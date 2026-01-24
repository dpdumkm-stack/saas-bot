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
        from app.services.subscription_manager import activate_subscription
        
        success = activate_subscription(order_id)
        if success:
             return jsonify({"status": "ok", "message": "activated"}), 200
        else:
             return jsonify({"status": "error", "message": "activation_failed"}), 500
            
    elif status in ['expire', 'cancel', 'deny']:
        sub.payment_status = 'failed'
        db.session.commit()
        
    return jsonify({"status": "ok"}), 200

