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
        return jsonify({"status": "no data"}), 400
        
    logging.info(f"MIDTRANS NOTIF RAW: {data}")
    
    order_id = data.get('order_id')
    status = data.get('transaction_status')
    
    if not order_id:
        return jsonify({"status": "no order_id"}), 400
        
    sub = Subscription.query.filter_by(order_id=order_id).first()
    if not sub:
        logging.error(f"Subscription not found for order_id: {order_id}")
        return jsonify({"status": "not found"}), 404
        
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
            msg_success = (
                f"✅ **AKTIVASI BERHASIL!**\n\n"
                f"Halo *{sub.name}*, paket Anda telah aktif.\n"
                f"Sesi sedang disiapkan di server...\n\n"
                f"Langkah terakhir:\n"
                f"Silakan buka link berikut untuk mengambil **Kode Pairing** (Tautan HP):\n"
                f"{request.url_root}success?order_id={order_id}"
            )
            kirim_waha(f"{sub.phone_number}@c.us", msg_success, MASTER_SESSION)
            
            logging.info(f"Bot Activated successfully for {sub.phone_number}")
            
    elif status in ['expire', 'cancel', 'deny']:
        sub.payment_status = 'failed'
        db.session.commit()
        
    return jsonify({"status": "ok"}), 200

