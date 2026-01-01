from flask import Blueprint, jsonify, send_file, request, session
import threading
import requests
import io
import time
import logging
from app.config import Config
from app.models import Toko, Subscription
from app.extensions import db
from app.services.waha import get_waha_pairing_code

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
            # Lookup subscription by order_id to get the phone number
            sub = Subscription.query.filter_by(order_id=session_param).first()
            if not sub:
                # Try fallback lookup
                import re
                potential_phones = re.findall(r'\d+', session_param)
                for p in potential_phones:
                    if len(p) >= 10:
                        sub = Subscription.query.filter_by(phone_number=p).first()
                        if sub:
                            break
            
            if sub:
                target_session = f"session_{sub.phone_number}"
            else:
                return jsonify({"error": "Session not found"}), 404
        else:
            # Default to master session
            target_session = MASTER_SESSION
        
        api_key = Config.WAHA_API_KEY
        headers = {'X-Api-Key': api_key}
        
        # Check if session exists
        session_ready = False
        try:
            chk = requests.get(f"{WAHA_BASE_URL}/api/sessions/{target_session}", headers=headers, timeout=5)
            if chk.status_code == 200:
                session_ready = True
                if chk.json().get('status') == 'STOPPED':
                    threading.Thread(target=lambda: requests.post(
                        f"{WAHA_BASE_URL}/api/sessions/{target_session}/start", 
                        headers=headers, timeout=10
                    )).start()
        except: pass
            
        if not session_ready:
            # Trigger BG creation if not locked
            if not session_creation_lock.locked():
                threading.Thread(target=create_and_start_session_bg).start()
            return jsonify({"error": "Initializing... Please refresh in 5s"}), 503

        # Try to get QR
        qr_urls = [
            f"{WAHA_BASE_URL}/api/{target_session}/auth/qr?format=image",
            f"{WAHA_BASE_URL}/api/sessions/{target_session}/auth/qr?format=image",
            f"{WAHA_BASE_URL}/api/{target_session}/auth/qr"
        ]
        
        for url in qr_urls:
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    return send_file(
                        io.BytesIO(response.content),
                        mimetype='image/png'
                    )
            except: continue
        
        return jsonify({"error": "QR loading..."}), 503

    except Exception as e:
        logging.error(f"API QR Error: {e}")
        return jsonify({"error": "Internal Error"}), 500

@api_bp.route('/waha_status')
def waha_status():
    try:
        api_key = Config.WAHA_API_KEY
        headers = {'X-Api-Key': api_key}
        response = requests.get(f"{WAHA_BASE_URL}/api/sessions/{MASTER_SESSION}", headers=headers, timeout=3)
        if response.status_code == 200:
            status = response.json()
            return jsonify({"connected": status.get('status')=='WORKING', "status": status.get('status')})
        return jsonify({"connected": False, "status": "NOT_FOUND"})
    except:
        return jsonify({"connected": False, "status": "ERROR"})

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

@api_bp.route('/get-pairing-code')
def get_pairing_code():
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({"success": False, "error": "Missing order_id"}), 400
        
    # 1. Try Exact Match
    sub = Subscription.query.filter_by(order_id=order_id).first()
    
    # 2. Try Fallback (Extrapolate phone from order_id if not found)
    if not sub:
        logging.warning(f"Pairing: order_id '{order_id}' not found. Trying fallback...")
        import re
        potential_phones = re.findall(r'\d+', order_id)
        for p in potential_phones:
            if len(p) >= 10:
                sub = Subscription.query.filter_by(phone_number=p).first()
                if sub: 
                    logging.info(f"Fallback matched: phone {p}")
                    break

    if not sub:
        return jsonify({"success": False, "error": "Order not found"}), 404
        
    if sub.payment_status != 'paid' and sub.status != 'ACTIVE':
         return jsonify({"success": False, "error": "Payment not confirmed"}), 400

    session_name = f"session_{sub.phone_number}"
    code = get_waha_pairing_code(session_name, sub.phone_number)
    
    if code:
        return jsonify({"success": True, "code": code})
    else:
        return jsonify({"success": False, "error": "Code not available yet"}), 503




