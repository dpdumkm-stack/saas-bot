from flask import Blueprint, request, jsonify, current_app
from app.models import Subscription, Toko
from app.extensions import db
from app.services.waha import create_waha_session, kirim_waha
from app.config import Config
import logging
from datetime import datetime, timedelta
import uuid

payment_bp = Blueprint('payment', __name__)
MASTER_SESSION = Config.MASTER_SESSION

@payment_bp.route('/api/payment/notification', methods=['POST'])
def midtrans_notification():
    """Handle Midtrans Webhook Notification"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "ignored", "reason": "no data"}), 200
        
    logging.info(f"MIDTRANS NOTIF RAW: {data}")
    
    order_id = data.get('order_id')
    status = data.get('transaction_status')
    
    if not order_id:
        # Some test notifications might not have order_id in expected field
        return jsonify({"status": "ok", "message": "test received"}), 200
        
    sub = Subscription.query.filter_by(order_id=order_id).first()
    if not sub:
        logging.warning(f"Midtrans Notif: Subscription not found for order_id: {order_id}. This is normal for Midtrans Test.")
        return jsonify({"status": "ok", "message": "order_not_found_handled"}), 200

        
    if status in ['settlement', 'capture']:
        # Double check status to prevent multiple activations
        if sub.payment_status != 'paid':
            sub.payment_status = 'paid'
            sub.status = 'ACTIVE'
            sub.active_at = datetime.now()
            sub.expired_at = datetime.now() + timedelta(days=31)
            sub.step = 0
            
            session_name = f"session_{sub.phone_number}"
            toko = Toko.query.get(sub.phone_number)
            if not toko:
                toko = Toko(
                    id=sub.phone_number,
                    nama=sub.name,
                    kategori=sub.category,
                    session_name=session_name,
                    remote_token=str(uuid.uuid4())[:8],
                    status_active=True
                )
                db.session.add(toko)
            else:
                toko.session_name = session_name
                toko.status_active = True
                toko.nama = sub.name # Sync name
                
            db.session.commit()
            
            # Start WAHA Session in background
            from threading import Thread
            Thread(target=create_waha_session, args=(session_name,)).start()
            
            # Notify master bot
            success_url = f"https://saas-bot-643221888510.asia-southeast2.run.app/success?order_id={order_id}"
            msg_success = (
                f"✅ **PEMBAYARAN DITERIMA!**\n\n"
                f"Terima kasih {sub.name}, akun Anda kini telah aktif! 🚀\n\n"
                f"Silakan klik link di bawah ini untuk mengaktifkan bot dengan **SCAN QR CODE**:\n\n"
                f"👉 {success_url}\n\n"
                f"_(Buka link di atas, lalu scan QR code dengan WhatsApp Anda)_"
            )


            kirim_waha(f"{sub.phone_number}@c.us", msg_success, MASTER_SESSION)
            
            logging.info(f"Bot Activated successfully for {sub.phone_number}")
            
    elif status in ['expire', 'cancel', 'deny']:
        sub.payment_status = 'failed'
        db.session.commit()
        
    return jsonify({"status": "ok"}), 200

