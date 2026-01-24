from flask import Blueprint, jsonify, send_file, request, session
import threading
import requests
import io
import time
import logging
from app.config import Config
from app.models import Toko, Subscription
from app.extensions import db


api_bp = Blueprint('api', __name__)
WAHA_BASE_URL = Config.WAHA_BASE_URL
MASTER_SESSION = Config.MASTER_SESSION

# Global lock for session creation
session_creation_lock = threading.Lock()

def create_and_start_session_bg():
    """Background task to create and start session"""
    with session_creation_lock:
        try:
            api_key = Config.WAHA_API_KEY
            headers = {'X-Api-Key': api_key}
            logging.info(f"BG: Force Recreating session '{MASTER_SESSION}'...")
            
            # 1. Delete existing (if any)
            try:
                requests.delete(f"{WAHA_BASE_URL}/api/sessions/{MASTER_SESSION}", headers=headers, timeout=10)
                time.sleep(1)
            except: pass

            # 2. Create (Minimal payload, relies on global config)
            res = requests.post(
                f"{WAHA_BASE_URL}/api/sessions",
                json={"name": MASTER_SESSION},
                headers=headers,
                timeout=30
            )
            logging.info(f"BG: Create Res: {res.status_code} {res.text}")
            res.raise_for_status()
            
            time.sleep(2)
            
            # 3. Start
            logging.info("BG: Starting session...")
            res2 = requests.post(f"{WAHA_BASE_URL}/api/sessions/{MASTER_SESSION}/start", headers=headers, timeout=30)
            logging.info(f"BG: Start Res: {res2.status_code}")
            res2.raise_for_status()
        except Exception as e:
            logging.error(f"BG Session Error: {e}")

@api_bp.route('/qr')
def api_qr():
    """Get QR code image from WAHA with async recovery"""
    try:
        # Check if a specific session (order_id) is requested
        session_param = request.args.get('session')
        
        if session_param:
            # Handle if session already has "session_" prefix
            sub_id = session_param.replace('session_', '')
            
            # Lookup subscription by order_id or phone_number
            sub = Subscription.query.filter(
                (Subscription.order_id == sub_id) | 
                (Subscription.phone_number == sub_id)
            ).first()
            
            if not sub:
                # Try fallback lookup for digits (phone number)
                import re
                potential_phones = re.findall(r'\d+', sub_id)
                for p in potential_phones:
                    if len(p) >= 10:
                        sub = Subscription.query.filter_by(phone_number=p).first()
                        if sub: break
            
            if sub:
                target_session = f"session_{sub.phone_number}"
            else:
                return jsonify({"error": "Session not found"}), 404
        else:
            # Default to master session
            target_session = MASTER_SESSION
        
        api_key = Config.WAHA_API_KEY
        headers = {'X-Api-Key': api_key}
        
        # Check if session exists and its status
        try:
            chk = requests.get(f"{WAHA_BASE_URL}/api/sessions/{target_session}", headers=headers, timeout=5)
            if chk.status_code == 200:
                status = chk.json().get('status')
                if status in ['STOPPED', 'FAILED']:
                    logging.info(f"Session {target_session} is {status}. Restarting...")
                    requests.post(f"{WAHA_BASE_URL}/api/sessions/{target_session}/start", headers=headers, timeout=10)
                    return jsonify({"error": "Restarting session... Wait 5s"}), 503
            else:
                # Session doesn't exist at all, create it
                logging.info(f"Session {target_session} not found. Creating...")
                requests.post(f"{WAHA_BASE_URL}/api/sessions", json={"name": target_session}, headers=headers, timeout=10)
                requests.post(f"{WAHA_BASE_URL}/api/sessions/{target_session}/start", headers=headers, timeout=10)
                return jsonify({"error": "Creating session... Wait 10s"}), 503
        except Exception as sess_err:
            logging.error(f"Sess check error: {sess_err}")

        # Try to get QR
        qr_urls = [
            f"{WAHA_BASE_URL}/api/{target_session}/auth/qr?format=image",
            f"{WAHA_BASE_URL}/api/sessions/{target_session}/auth/qr?format=image"
        ]
        
        for url in qr_urls:
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                    return send_file(io.BytesIO(response.content), mimetype='image/png')
            except: continue
        
        return jsonify({"error": "QR loading..."}), 503

    except Exception as e:
        logging.error(f"API QR Error: {e}")
        return jsonify({"error": "Internal Error"}), 500

@api_bp.route('/status')
def api_status():
    """Check connection status for a specific session or master session"""
    try:
        session_param = request.args.get('session')
        target_session = MASTER_SESSION
        
        if session_param:
            sub = Subscription.query.filter_by(order_id=session_param).first()
            if not sub:
                # Try search by phone
                import re
                p = re.findall(r'\d+', session_param)
                if p:
                    sub = Subscription.query.filter_by(phone_number=p[0]).first()
            
            if sub:
                target_session = f"session_{sub.phone_number}"

        api_key = Config.WAHA_API_KEY
        headers = {'X-Api-Key': api_key}
        
        response = requests.get(f"{WAHA_BASE_URL}/api/sessions/{target_session}", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'UNKNOWN')
            # WAHA Statuses: SCAN_QR, WORKING, STOPPED, FAILED, etc.
            return jsonify({
                "status": status,
                "connected": status == 'WORKING',
                "session": target_session
            })
        
        return jsonify({"status": "NOT_FOUND", "connected": False})
    except Exception as e:
        logging.error(f"Status API Error: {e}")
        return jsonify({"status": "ERROR", "connected": False})

@api_bp.route('/reset_session', methods=['POST'])
def reset_session():
    try:
        api_key = Config.WAHA_API_KEY
        headers = {'X-Api-Key': api_key}
        try: requests.post(f"{WAHA_BASE_URL}/api/sessions/{MASTER_SESSION}/logout", headers=headers, timeout=5)
        except: pass
        requests.delete(f"{WAHA_BASE_URL}/api/sessions/{MASTER_SESSION}", headers=headers, timeout=5)
        time.sleep(2)
        requests.post(f"{WAHA_BASE_URL}/api/sessions", json={"name": MASTER_SESSION}, headers=headers, timeout=30)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/update_counter', methods=['POST'])
def api_update_counter():
    try:
        data = request.json
        if not data: return jsonify({"error": "invalid request"}), 400
        token = data.get('hp')
        if not token: return jsonify({"error": "missing token"}), 400
        if session.get(f'auth_{token}') != True: return jsonify({"error": "unauthorized"}), 401
        toko = Toko.query.filter_by(remote_token=token).first()
        if not toko: return jsonify({"error": "toko not found"}), 404
        idx = int(data.get('index', -1))
        if idx < 0 or idx >= len(toko.menus): return jsonify({"error": "invalid index"}), 400
        m = toko.menus[idx]
        chg = int(data.get('change', 0))
        if m.stok == -1: m.stok = 10 if chg < 0 else -1
        else: m.stok = max(0, m.stok + chg)
        db.session.commit()
        return jsonify({"status": "success", "new_stok": m.stok})
    except Exception as e:
        return jsonify({"error": "server error"}), 500

@api_bp.route('/register_trx', methods=['POST'])
def register_trx():
    """
    Unified Payment Registration Endpoint.
    Used by: Landing Page (New User) & Chatbot (Upgrade/Renewal).
    """
    import uuid
    from datetime import datetime
    from app.services.midtrans_service import get_snap_redirect_url
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    phone = data.get('phone_number')
    name = data.get('name', 'Unknown Token')
    category = data.get('category', 'General')
    package_key = data.get('package', 'STARTER').upper()
    
    if not phone:
        return jsonify({"error": "Phone number is required"}), 400
        
    # Call Service
    from app.services.transaction_service import create_subscription_transaction
    
    result = create_subscription_transaction(phone, name, package_key, category)
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify({"status": "failed", "message": result['message'], "error": result['message']}), 400

@api_bp.route('/broadcast/send', methods=['POST'])
def send_broadcast():
    """Admin Endpoint to Trigger Broadcast"""
    import json
    from app.models import BroadcastJob
    
    # Security: Use WAHA_API_KEY as Admin Secret
    if request.headers.get('X-Api-Key') != Config.WAHA_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    toko_id = data.get('toko_id')
    message = data.get('message')
    targets = data.get('targets', [])
    
    if not toko_id or not message or not targets:
        return jsonify({"error": "Missing toko_id, message, or targets"}), 400
        
    try:
        job = BroadcastJob(
            toko_id=toko_id,
            pesan=message,
            target_list=json.dumps(targets),
            status='PENDING'
        )
        db.session.add(job)
        db.session.commit()
        return jsonify({"status": "queued", "job_id": job.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/subscription/cancel', methods=['POST'])
def api_cancel_subscription():
    """Cancel subscription from dashboard with feedback."""
    try:
        data = request.json
        phone = data.get('phone_number')
        reason = data.get('reason')
        confirm = data.get('confirm')

        if not phone or not confirm:
            return jsonify({"status": "error", "message": "Missing phone or confirmation"}), 400

        from app.services.subscription_manager import cancel_subscription_with_grace
        result = cancel_subscription_with_grace(phone, reason=reason)

        if result['success']:
            return jsonify({"status": "success", "message": result['message'], "grace_period_ends": result.get('grace_period_ends')})
        else:
            return jsonify({"status": "error", "message": result['message']}), 400

    except Exception as e:
        logging.error(f"API Cancel Subscription Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/subscription/reactivate', methods=['POST'])
def api_reactivate_subscription():
    """Reactivate cancelled subscription from dashboard."""
    try:
        data = request.json
        phone = data.get('phone_number')

        if not phone:
            return jsonify({"status": "error", "message": "Phone number is required"}), 400

        from app.services.subscription_manager import reactivate_from_grace
        result = reactivate_from_grace(phone)

        if result['success']:
            return jsonify({"status": "success", "message": result['message'], "new_expiry": result.get('new_expiry')})
        else:
            return jsonify({"status": "error", "message": result['message']}), 400

    except Exception as e:
        logging.error(f"API Reactivate Subscription Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



