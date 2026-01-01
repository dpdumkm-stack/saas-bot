import json
import logging
import threading
from flask import Blueprint, request, jsonify, current_app
from app.models import Toko, Subscription, Customer, ChatLog
from app.extensions import db
from app.services.waha import kirim_waha
from app.services.gemini import get_gemini_response
from app.services.sales_engine import check_and_send_followups
from app.config import Config

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    # 1. Validate payload
    data = request.get_json()
    if not data:
        return jsonify({"status": "ignored", "reason": "empty"}), 200

    # --- FILTER GROUP/BROADCAST/NEWSLETTER EARLY ---
    msg_obj = data.get('payload', data.get('data', data))
    chat_id = msg_obj.get('from') or msg_obj.get('chatId') or ""
    
    if "@g.us" in chat_id or "status@broadcast" in chat_id or "@newsletter" in chat_id:
        return jsonify({"status": "ignored", "reason": "non_personal_chat"}), 200

    logging.info(f"WEBHOOK RAW: {json.dumps(data)}")

    # 1.5 TRIGGER SALES ENGINE
    try:
        app_ctx = current_app._get_current_object()
        threading.Thread(target=check_and_send_followups, args=(app_ctx,)).start()
    except Exception as e:
        logging.error(f"Scheduler Trigger Error: {e}")

    # 2. Extract Basic Info
    session_id = data.get('session', Config.MASTER_SESSION)
    payload = data.get('payload', {})
    
    # Handle different WAHA payload structures
    body = payload.get('body', '')
    chat_id = payload.get('from', '')
    from_me = payload.get('fromMe', False)
    
    # Stop if no chat_id or from me
    if not chat_id or from_me:
        return "Ignored", 200

    # Derive Toko ID from Session Name
    # Example: 'session_62812...' -> '62812...'
    toko_id = session_id.replace("session_", "")
    nomor_murni = chat_id.split('@')[0] if '@' in chat_id else chat_id

    # --- FILTER NOMOR TERDAFTAR (MASTER SESSION ONLY) ---
    if session_id == Config.MASTER_SESSION:
        is_admin = (nomor_murni == Config.SUPER_ADMIN_WA)
        is_submitting_reg = any(x in body.upper() for x in ["/DAFTAR", "REG_AUTO", "/UNREG", "/PING", "/PINTU"])
        
        # Cek apakah nomor ada di tabel Subscription atau Toko
        is_registered_owner = Subscription.query.filter_by(phone_number=nomor_murni).first() is not None
        
        if not (is_admin or is_registered_owner or is_submitting_reg):
            # Jika orang asing chat ke nomor Master dan bukan mau daftar -> ABAIKAN
            return "Ignored: Unknown number on Master Session", 200

    with current_app.app_context():
        # --- BUSINESS LOGIC START ---
        
        # A. ADMIN & REGISTRATION (MASTER)
        if session_id == Config.MASTER_SESSION:
            # 1. Admin Commands
            if nomor_murni == Config.SUPER_ADMIN_WA:
                if body.lower() == '/ping':
                    kirim_waha(chat_id, "🏓 Pong! (SaaS Bot Active)", session_id)
                    return "OK", 200
                elif body.lower() == '/pintu':
                    from app.models import SystemConfig
                    cfg = SystemConfig.query.get('maintenance_mode')
                    msg = "Pintu Maintenance saat ini: " + ("TERTUTUP (Aktif)" if cfg and cfg.value=='true' else "TERBUKA (Bebas)")
                    kirim_waha(chat_id, msg, session_id)
                    return "OK", 200

            # 2. Registration Flow
            sub = Subscription.query.filter_by(phone_number=nomor_murni).first()
            if sub or is_submitting_reg:
                from app.services.registration import handle_registration
                handle_registration(nomor_murni, body, chat_id, session_id)
                return "OK", 200

        # B. CUSTOMER SERVICE (AI RESPONDER)
        toko = Toko.query.get(toko_id)
        if not toko:
            return "Toko Not Found", 200
            
        # AI Response Logic
        customer = Customer.query.filter_by(toko_id=toko_id, nomor_hp=nomor_murni).first()
        if not customer:
            customer = Customer(toko_id=toko_id, nomor_hp=nomor_murni)
            db.session.add(customer)
        
        customer.last_interaction = db.func.now()
        ai_response = get_gemini_response(body, toko, customer)
        
        if ai_response:
            kirim_waha(chat_id, ai_response, session_id)
            chat_log = ChatLog(toko_id=toko_id, customer_id=customer.id, message=body, response=ai_response)
            db.session.add(chat_log)
            db.session.commit()

    return "OK", 200
