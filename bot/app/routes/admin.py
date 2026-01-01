from flask import Blueprint, render_template, request, session, render_template_string, jsonify
import time
import uuid
from datetime import datetime, timedelta
from app.models import Toko, Subscription
from app.services.payment import create_payment_link
from app.extensions import db
from app.services.waha import create_waha_session

admin_bp = Blueprint('admin', __name__)

def ensure_store_exists(sub):
    toko = Toko.query.get(sub.phone_number)
    if not toko:
        new_sess = f"session_{sub.phone_number}"
        try:
            create_waha_session(new_sess)
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
        sub.expired_at = datetime.now() + timedelta(days=3)
        db.session.commit()
        
        ensure_store_exists(sub)
        
        return jsonify({
            "status": "success", 
            "redirect_url": f"/success?order_id={order_id}"
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


@admin_bp.route('/')
def landing_page():
    return render_template('landing.html')

@admin_bp.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

@admin_bp.route('/success')
def success_page():
    return render_template('success.html')



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
