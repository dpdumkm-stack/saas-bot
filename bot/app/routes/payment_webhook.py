from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Subscription, Toko
from app.services.waha import kirim_waha, create_waha_session
from app.config import Config
import hashlib
import logging
from datetime import datetime, timedelta
import uuid

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payment/notification', methods=['POST'])
def midtrans_notification():
    """
    Handle Midtrans HTTP Notification
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error"}), 400
        
    logging.info(f"PAYMENT NOTIF: {data}")
    
    order_id = data.get('order_id')
    status_code = data.get('status_code')
    gross_amount = data.get('gross_amount')
    signature_key = data.get('signature_key')
    transaction_status = data.get('transaction_status')
    
    # 1. Start Verification (Simple Signature Check)
    # Midtrans Signature: SHA512(order_id+status_code+gross_amount+ServerKey)
    raw_str = f"{order_id}{status_code}{gross_amount}{Config.MIDTRANS_SERVER_KEY}"
    my_signature = hashlib.sha512(raw_str.encode('utf-8')).hexdigest()
    
    if my_signature != signature_key:
        logging.warning("Invalid Signature Payment")
        return jsonify({"status": "error", "message": "Invalid Signature"}), 403
        
    # 2. Update Database
    sub = Subscription.query.filter_by(order_id=order_id).first()
    if not sub:
        logging.warning(f"Order ID Not Found: {order_id}")
        return jsonify({"status": "error", "message": "Order not found"}), 404
        
    if transaction_status in ['capture', 'settlement']:
        if sub.status != 'ACTIVE':
            sub.status = 'ACTIVE'
            sub.payment_status = 'paid'
            sub.expired_at = datetime.now() + timedelta(days=30)
            
            # Create Toko Resource if not exists
            toko = Toko.query.get(sub.phone_number)
            if not toko:
                new_sess = f"session_{sub.phone_number}"
                if create_waha_session(new_sess):
                    new_toko = Toko(
                        id=sub.phone_number, 
                        nama=sub.name, 
                        kategori=sub.category, 
                        session_name=new_sess, 
                        remote_token=str(uuid.uuid4())[:8]
                    )
                    db.session.add(new_toko)
            
            db.session.commit()
            
            # Notify User
            msg = f"✅ **Pembayaran Diterima!**\n\nPaket {sub.tier} telah aktif.\nBerlaku sampai: {sub.expired_at.strftime('%d-%m-%Y')}\n\nKetik **/kode** untuk menyambungkan WhatsApp Anda."
            kirim_waha(sub.phone_number, msg, Config.MASTER_SESSION)
            
    elif transaction_status in ['deny', 'cancel', 'expire']:
        sub.payment_status = 'failed'
        db.session.commit()
        kirim_waha(sub.phone_number, "❌ Pembayaran Gagal/Expired. Silakan daftar ulang.", Config.MASTER_SESSION)
        
    return jsonify({"status": "ok"}), 200
