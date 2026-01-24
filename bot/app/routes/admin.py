from flask import Blueprint, render_template, request, session, render_template_string, jsonify, redirect, url_for
import time
import uuid
import logging
from datetime import datetime, timedelta
from app.models import Toko, Subscription
from app.services.payment import create_payment_link
from app.extensions import db
from app.services.waha import create_waha_session, request_pairing_code, get_session_status

admin_bp = Blueprint('admin', __name__)

def ensure_store_exists(sub, pairing_method='qr'):
    toko = Toko.query.get(sub.phone_number)
    if not toko:
        new_sess = f"session_{sub.phone_number}"
        try:
            create_waha_session(new_sess, pairing_method=pairing_method)
        except: pass
        
        new_toko = Toko(
            id=sub.phone_number, 
            nama=sub.name, 
            kategori=sub.category, 
            session_name=new_sess, 
            remote_token=str(uuid.uuid4())[:8]
        )
        db.session.add(new_toko)
        db.session.commit()

@admin_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    phone = data.get('phone')
    name = data.get('name')
    category = data.get('category')
    tier = data.get('tier', 'STARTER')
    pairing_method = data.get('pairing_method', 'qr')  # NEW: qr or code

    if not phone or not name:
        return jsonify({"status": "error", "message": "Data tidak lengkap"}), 400

    # Clean Phone
    if phone.startswith('0'): phone = '62' + phone[1:]
    if phone.startswith('+'): phone = phone[1:]
    phone = phone.replace('-', '').replace(' ', '')

    # Check Existing or Create
    sub = Subscription.query.filter_by(phone_number=phone).first()
    if not sub:
        sub = Subscription(phone_number=phone)
        db.session.add(sub)

    sub.name = name
    sub.category = category
    sub.tier = tier
    
    # Generate Order ID
    order_id = f"SUBS-{int(time.time())}-{phone[-4:]}"
    sub.order_id = order_id

    # Handle TRIAL
    if tier == 'TRIAL':
        sub.status = 'ACTIVE'
        sub.payment_status = 'paid' 
        sub.expired_at = datetime.now() + timedelta(days=5)
        sub.active_at = datetime.now()  # Track when activated
        db.session.commit()
        
        # Audit Log
        try:
            from app.services.audit_service import log_audit
            log_audit('SYSTEM', phone, 'TRIAL_SIGNUP', 'SUBSCRIPTION', order_id, None, f"{name}|{tier}")
        except: pass
        
        ensure_store_exists(sub, pairing_method=pairing_method)
        
        # Send Welcome WhatsApp Message (Production Safe)
        try:
            from app.services.waha import kirim_waha_raw
            from app.config import Config
            
            # Format expiry date
            expiry_date = sub.expired_at.strftime('%d %b %Y, %H:%M')
            
            # Construct welcome message
            welcome_msg = f"""🎉 *Selamat! Trial 3 Hari Aktif*

Halo {name}!

Pendaftaran Anda berhasil. Bot Wali.ai siap digunakan hingga *{expiry_date}*.

📱 *Langkah Setup (2 menit):*
1. Klik link ini untuk scan QR:
   {Config.WAHA_WEBHOOK_URL.replace('/webhook', '')}/success?order_id={order_id}&method={pairing_method}

2. Connect WhatsApp bot Anda
3. Mulai terima order dari customer!

💡 Atau akses dashboard:
   {Config.WAHA_WEBHOOK_URL.replace('/webhook', '')}/dashboard

Butuh bantuan? Ketik /help"""
            
            # Send from master session to user's WhatsApp
            kirim_waha_raw(
                to=phone,
                message=welcome_msg,
                session=Config.MASTER_SESSION
            )
            logging.info(f"Trial welcome message sent to {phone}")
        except Exception as e:
            # Non-blocking: log error but don't fail registration
            logging.error(f"Failed to send trial welcome WA: {e}")
        
        # Auto-login
        session['toko_id'] = sub.phone_number
        session.permanent = True
        
        return jsonify({
            "status": "success", 
            "redirect_url": "/dashboard?new_reg=true"  # Redirect to Dashboard
        })

    # PAID Plans
    prices = {'STARTER': 99000, 'BUSINESS': 199000, 'PRO': 349000}
    amount = prices.get(tier, 99000)
    
    details = {
        'order_id': order_id,
        'amount': amount,
        'customer_details': {'first_name': name, 'phone': phone},
        'item_details': [{'id': tier, 'price': amount, 'quantity': 1, 'name': f"{tier} Plan"}]
    }
    
    pay_url = create_payment_link(details)
    if pay_url:
        sub.payment_url = pay_url
        sub.status = 'DRAFT'
        db.session.commit()
        return jsonify({"status": "success", "redirect_url": pay_url})
    else:
        return jsonify({"status": "error", "message": "Gagal membuat link pembayaran"}), 500



@admin_bp.route('/daftar')
def register_page():
    """Universal registration page with dynamic content based on tier"""
    return render_template('register_trial.html')

@admin_bp.route('/')
def landing_page():
    return render_template('landing.html')

@admin_bp.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

@admin_bp.route('/success')
def success_page():
    order_id = request.args.get('order_id')
    sub = Subscription.query.filter_by(order_id=order_id).first()
    
    if not sub:
        # Fallback to general success page or 404 with better UI
        return render_template('subscribe.html', error="Order ID tidak ditemukan. Silakan hubungi admin.")

    # SELF-HEALING: Ensure WAHA session exists
    session_name = f"session_{sub.phone_number}"
    
    # Check if session creation was skipped (e.g. TRX flow)
    # We trigger creation here just in case. It's idempotent-ish (handled inside).
    try:
        # We need a quick check or just call create_waha_session blindly?
        # create_waha_session checks API internally.
        # But to be safe and avoid delay, maybe check status first?
        # Actually `create_waha_session` in waha.py does a check first.
        # START SELF-HEAL
        from app.services.waha import get_session_status
        status_data = get_session_status(session_name)
        
        # Check for missing (error) OR broken/stopped state
        if status_data.get('status') == 'error' or status_data.get('session_status') in ['FAILED', 'STOPPED']:
             logging.info(f"🚑 Self-Healing: Repairing session {session_name} (Status: {status_data.get('session_status')})")
             # Default to QR method for self-healing unless specified
             method = request.args.get('method', 'qr') 
             create_waha_session(session_name, pairing_method=method)
        # END SELF-HEAL
    except Exception as e:
        logging.error(f"Self-healing failed: {e}")

    return render_template('success_pairing.html', 
                           session_name=session_name, 
                           phone_number=sub.phone_number,
                           order_id=order_id,
                           active_method=request.args.get('method', 'qr'))

@admin_bp.route('/success_pairing')
def success_pairing_legacy():
    # Support legacy links in WA notifications
    return redirect(url_for('admin.success_page', **request.args))

# Subscription Management API Endpoints
@admin_bp.route('/api/subscription/cancel', methods=['POST'])
def api_cancel_subscription():
    """Cancel subscription with 30-day grace period"""
    from app.services.subscription_manager import cancel_subscription_with_grace
    
    data = request.json
    phone = data.get('phone_number')
    reason = data.get('reason', 'No reason provided')
    confirm = data.get('confirm', False)
    
    if not phone or not confirm:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    result = cancel_subscription_with_grace(phone, reason)
    
    if result['success']:
        # Audit Log
        try:
            from app.services.audit_service import log_audit
            log_audit('SYSTEM', phone, 'CANCEL_SUBSCRIPTION', 'SUBSCRIPTION', phone, None, reason)
        except: pass
        
        return jsonify({
            "status": "success",
            "message": result['message'],
            "grace_period_ends": result['grace_period_ends'].isoformat() if result.get('grace_period_ends') else None
        })
    else:
        return jsonify({"status": "error", "message": result['message']}), 400


@admin_bp.route('/api/subscription/reactivate', methods=['POST'])
def api_reactivate_subscription():
    """Reactivate cancelled subscription during grace period"""
    from app.services.subscription_manager import reactivate_from_grace
    
    data = request.json
    phone = data.get('phone_number')
    
    if not phone:
        return jsonify({"status": "error", "message": "Phone number required"}), 400
    
    result = reactivate_from_grace(phone)
    
    if result['success']:
        # Audit Log
        try:
            from app.services.audit_service import log_audit
            log_audit('SYSTEM', phone, 'REACTIVATE_SUBSCRIPTION', 'SUBSCRIPTION', phone, None, 'SUCCESS')
        except: pass
        
        return jsonify({
            "status": "success",
            "message": result['message'],
            "new_expiry": result.get('new_expiry').isoformat() if result.get('new_expiry') else None
        })
    else:
        return jsonify({"status": "error", "message": result['message']}), 400

# NEW: Pairing Code API Endpoints
@admin_bp.route('/api/pairing/request-code', methods=['POST'])
def api_request_pairing_code():
    """Request pairing code for a session"""
    data = request.json
    session_name = data.get('session_name')
    
    if not session_name:
        return jsonify({"status": "error", "message": "Session name required"}), 400
    
    result = request_pairing_code(session_name)
    return jsonify(result)

@admin_bp.route('/api/pairing/check-status', methods=['POST'])
def api_check_session_status():
    """Check session connection status"""
    data = request.json
    session_name = data.get('session_name')
    
    if not session_name:
        return jsonify({"status": "error", "message": "Session name required"}), 400
    
    result = get_session_status(session_name)
    return jsonify(result)



@admin_bp.route('/health')
def health_check():
    """System health check endpoint for monitoring"""
    from app.extensions import db
    from app.config import Config
    import requests
    
    checks = {}
    all_healthy = True
    
    # 1. Database Check
    from sqlalchemy import text
    try:
        db.session.execute(text('SELECT 1'))
        checks['database'] = 'healthy'
    except Exception as e:
        checks['database'] = f'error: {str(e)[:50]}'
        all_healthy = False
    
    # 2. WAHA API Check
    try:
        headers = {'X-Api-Key': Config.WAHA_API_KEY}
        res = requests.get(f"{Config.WAHA_BASE_URL}/api/sessions", headers=headers, timeout=5)
        checks['waha_api'] = 'healthy' if res.status_code == 200 else f'status_{res.status_code}'
        if res.status_code != 200:
            all_healthy = False
    except Exception as e:
        checks['waha_api'] = f'error: {str(e)[:50]}'
        all_healthy = False
    
    # 3. Broadcast Worker Check (basic check - see if BroadcastJob table accessible)
    try:
        from app.models import BroadcastJob
        pending = BroadcastJob.query.filter_by(status='PENDING').count()
        checks['broadcast_worker'] = f'healthy (pending: {pending})'
    except Exception as e:
        checks['broadcast_worker'] = f'error: {str(e)[:50]}'
        all_healthy = False
    
    
    # ALWAYS return 200 for Cloud Run liveness/readiness
    # We inform status in body ('healthy' or 'degraded') but don't kill the container
    status_code = 200
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'checks': checks,
        'timestamp': datetime.now().isoformat()
    }), status_code

@admin_bp.route('/subscribe')
def subscribe_page():
    return render_template('subscribe.html')

@admin_bp.route('/admin/qr')
def qr_page():
    return render_template('qr_scan.html', timestamp=int(time.time()))

@admin_bp.route('/remote/<token>', methods=['GET', 'POST'])
def remote_view(token):
    toko = Toko.query.filter_by(remote_token=token).first()
    if not toko:
        return "403 Forbidden", 403
    
    if session.get(f'auth_{token}') != True:
        if request.method == 'POST':
            pin = request.form.get('pin', '')
            if pin == toko.remote_pin:
                session[f'auth_{token}'] = True
                session.permanent = True
                return render_template('remote.html', toko=toko, user_token=token)
            return "PIN Salah", 401
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Login</title></head>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <form method=post style="padding:2rem;border:1px solid #ddd;border-radius:8px;">
                    <h2>Masukkan PIN</h2>
                    <input type=password name=pin placeholder="PIN" required style="padding:0.5rem;font-size:1rem;">
                    <button style="padding:0.5rem 1rem;margin-left:0.5rem;">Masuk</button>
                </form>
            </body>
            </html>
        """)

    return render_template('remote.html', toko=toko, user_token=token)
