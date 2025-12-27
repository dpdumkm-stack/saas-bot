from flask import Blueprint, request, jsonify
from app.config import Config
from app.extensions import db, limiter
from app.models import Toko, Menu, Customer, ChatLog, BroadcastJob, SystemConfig
from app.services.waha import kirim_waha, kirim_waha_raw, kirim_waha_image_raw, kirim_waha_image_url, kirim_waha_buttons, create_waha_session, get_waha_qr_retry, format_nomor
from app.services.gemini import tanya_gemini, analisa_bukti_transfer
from app.utils import download_file, extract_number
import threading
import uuid
import json
import logging
import time
from datetime import datetime, timedelta

webhook_bp = Blueprint('webhook', __name__)
WAHA_BASE_URL = Config.WAHA_BASE_URL
MASTER_SESSION = Config.MASTER_SESSION
SUPER_ADMIN_WA = Config.SUPER_ADMIN_WA
TARGET_LIMIT_USER = Config.TARGET_LIMIT_USER

def get_maintenance_mode():
    try:
        config = SystemConfig.query.get('maintenance_mode')
        return config and config.value.lower() == 'true'
    except: return False

def set_maintenance_mode(enabled):
    try:
        config = SystemConfig.query.get('maintenance_mode')
        if config: config.value = 'true' if enabled else 'false'
        else: db.session.add(SystemConfig(key='maintenance_mode', value='true' if enabled else 'false'))
        db.session.commit()
        return True
    except: return False

@webhook_bp.route('/webhook', methods=['POST'])
@limiter.limit("200 per minute")
def webhook():
    # 1. Validate payload
    data = request.get_json()
    if not data:
        return jsonify({"status": "ignored", "reason": "empty"}), 200

    logging.info(f"WEBHOOK RAW: {json.dumps(data)}")

    # 2. Parse Go-Whatsapp Format
    # Format: { "messages": [ { "key": { "remoteJid": "..." }, "message": { "conversation": "..." } } ] }
    # Or simplified depending on version. Aldino usually sends simpler structure or standard Baileys.
    
    try:
        # --- PARSING STRATEGY FOR WAHA PLUS (STANDARD) ---
        # Structure: { "event": "message", "payload": { "from": "...", "body": "...", "fromMe": false, ... } }
        
        # 1. Extract Inner Payload
        msg_obj = {}
        if 'payload' in data: 
            msg_obj = data['payload']
        elif 'data' in data:
            msg_obj = data['data']
        else:
            msg_obj = data # Fallback
            
        # 2. Get Chat ID (WAHA uses 'from' or 'chatId')
        chat_id = msg_obj.get('from') or msg_obj.get('chatId')
        
        # 3. Check From Me
        from_me = msg_obj.get('fromMe', False)
        if from_me:
             return jsonify({"status": "ignored", "reason": "from_me"}), 200
             
        # 4. Get Body (handle null for media messages)
        body = msg_obj.get('body')
        if body is None:
            body = msg_obj.get('text') or ""
        
        # 5. Push Name
        push_name = msg_obj.get('pushName') or msg_obj.get('notifyName') or "User"
        
        # 6. Fallback/Safety
        if not chat_id:
             logging.warning(f"No chat_id found in webhook. msg_obj keys: {list(msg_obj.keys())}")
             return jsonify({"status": "ignored", "reason": "no_chat_id"}), 200
             
        payload_info = {
            "chat_id": chat_id,
            "body": body,
            "push_name": push_name
        }
        
        logging.info(f"PARSED WEBHOOK (WAHA): {payload_info}")
        
        # --- PREPARE VARIABLES FOR LOGIC ---
        session_name = MASTER_SESSION
        
        # Check if internal format (already has @c.us or @s.whatsapp.net)
        nomor_murni = chat_id.split('@')[0] if '@' in chat_id else chat_id
        
        # Ignore Broadcasts / Groups if not needed
        if "@g.us" in chat_id or "status@broadcast" in chat_id: 
            logging.info(f"Ignoring group/broadcast message from {chat_id}")
            return "Ignored", 200

        # --- BUSINESS LOGIC START ---
        
        # --- A. ADMIN SAAS (MASTER) ---
        if session_name == MASTER_SESSION:
            # SUPER ADMIN CHECK
            if nomor_murni == SUPER_ADMIN_WA:
                if body == "/mt on":
                    if set_maintenance_mode(True): kirim_waha(chat_id, "🛑 MAINTENANCE ON", MASTER_SESSION)
                    return "OK", 200
                elif body == "/mt off":
                    if set_maintenance_mode(False): kirim_waha(chat_id, "✅ MAINTENANCE OFF", MASTER_SESSION)
                    return "OK", 200

            if get_maintenance_mode():
                kirim_waha(chat_id, "⚠️ Sedang Maintenance.", MASTER_SESSION)
                return "MT", 200

            if body.startswith("/daftar"):
                toko = Toko.query.get(nomor_murni)
                if toko:
                    kirim_waha(chat_id, "Sudah terdaftar! /scan untuk ulang.", MASTER_SESSION)
                else:
                    if Toko.query.count() >= TARGET_LIMIT_USER:
                        kirim_waha(chat_id, "Kuota Penuh.", MASTER_SESSION)
                        return "Full", 200
                    try:
                        parts = body.split("#")
                        nama = parts[0].replace("/daftar","").strip()
                        kat = parts[1].strip().lower() if len(parts)>1 else "umum"
                        new_sess = f"session_{nomor_murni}"
                        if create_waha_session(new_sess):
                            new_toko = Toko(id=nomor_murni, nama=nama, kategori=kat, session_name=new_sess, remote_token=str(uuid.uuid4())[:8])
                            db.session.add(new_toko); db.session.commit()
                            kirim_waha(chat_id, "✅ Terdaftar! Tunggu QR...", MASTER_SESSION)
                            qr = get_waha_qr_retry(new_sess)
                            if qr: kirim_waha_image_raw(chat_id, qr, "📲 SCAN!", MASTER_SESSION)
                            else: kirim_waha(chat_id, "Gagal QR. Ketik /scan.", MASTER_SESSION)
                        else: kirim_waha(chat_id, "Server Penuh.", MASTER_SESSION)
                    except: kirim_waha(chat_id, "Format: /daftar Nama #kategori", MASTER_SESSION)
                return "Reg", 200
            
            elif body == "/scan":
                toko = Toko.query.get(nomor_murni)
                if toko:
                    qr = get_waha_qr_retry(toko.session_name)
                    if qr: kirim_waha_image_raw(chat_id, qr, "📲 Scan ini.", MASTER_SESSION)
                return "Scan", 200

        # --- B. CLIENT UMKM ---
        else:
            toko = Toko.query.filter_by(session_name=session_name).first()
            if not toko: return "Unknown", 200
            if get_maintenance_mode() and nomor_murni != toko.id:
                kirim_waha(chat_id, "⚠️ Maintenance sebentar...", session_name)
                return "MT", 200

            # 1. OWNER COMMANDS
            if nomor_murni == toko.id:
                if body.startswith("/menu"):
                    try:
                        p = body.split()
                        if len(p) < 3:
                            kirim_waha(chat_id, "❌ Format: /menu [Nama Item] [Harga]", session_name)
                            return "Cmd", 200
                        hrg = int(p[-1])
                        itm = " ".join(p[1:-1])
                        if hrg <= 0 or hrg > 100000000:
                            kirim_waha(chat_id, "❌ Harga tidak valid", session_name); return "Cmd", 200
                        db.session.add(Menu(toko_id=toko.id, item=itm, harga=hrg))
                        db.session.commit()
                        kirim_waha(chat_id, f"✅ Menu '{itm}' ditambahkan (Rp {hrg:,})", session_name)
                    except: kirim_waha(chat_id, "❌ Gagal menambah menu.", session_name)
                    return "Cmd", 200
                elif body == "/remote":
                    link = f"{request.host_url}remote/{toko.remote_token}"
                    kirim_waha(chat_id, f"🎛️ Remote: {link}", session_name)
                    return "Cmd", 200
                elif body.startswith("/broadcast"):
                    msg = body.replace("/broadcast","").strip()
                    custs = [c.nomor_hp for c in toko.customers]
                    if custs:
                        job = BroadcastJob(toko_id=toko.id, pesan=msg, target_list=json.dumps(custs))
                        db.session.add(job); db.session.commit()
                        kirim_waha(chat_id, "🚀 Broadcast antri.", session_name)
                    return "Bc", 200

            # 2. AUTO-MUTE
            if from_me:
                # Need to parse 'to' if from_me is true, but we returned early for from_me above
                # So this block is effectively unreachable unless we change the from_me check
                pass 

            # 3. CUSTOMER CHAT
            if nomor_murni == toko.id and not from_me: pass
            else:
                cust = Customer.query.filter_by(toko_id=toko.id, nomor_hp=nomor_murni).first()
                if not cust:
                    cust = Customer(toko_id=toko.id, nomor_hp=nomor_murni)
                    db.session.add(cust); db.session.commit()
                if cust.is_muted_until and cust.is_muted_until > datetime.now(): return "Muted", 200

                if url_file and cust.order_status == 'WAIT_TRANSFER':
                    kirim_waha(chat_id, "⏳ Cek bukti...", session_name)
                    fb, mime = download_file(url_file)
                    if fb:
                        res = analisa_bukti_transfer(fb, mime, cust.current_bill)
                        if res['is_valid'] and res['fraud_score'] < 30:
                            kirim_waha(chat_id, "✅ Lunas!", session_name)
                            kirim_waha_image_url(toko.id, url_file, f"💰 MASUK Rp {cust.current_bill:,}", session_name)
                            cust.order_status = 'NONE'; db.session.commit()
                        else:
                            kirim_waha(chat_id, "Dicek manual.", session_name)
                            kirim_waha_image_url(toko.id, url_file, "⚠️ BUKTI MENCURIGAKAN!", session_name)
                    return "Img", 200

                jawaban = tanya_gemini(body, toko, cust)
                if "[HANDOFF]" in jawaban:
                    kirim_waha(chat_id, "Maaf, Owner akan bantu.", session_name)
                    kirim_waha(toko.id, f"⚠️ SOS: {body}", session_name)
                    cust.is_muted_until = datetime.now() + timedelta(minutes=30); db.session.commit()
                elif "[ORDER_MASUK" in jawaban:
                    try: total = extract_number(jawaban.split("[ORDER_MASUK:")[1].split("]")[0])
                    except: total = 0
                    kirim_waha(chat_id, jawaban.split("[")[0], session_name)
                    cust.order_status = 'WAIT_TRANSFER'; cust.current_bill = total; db.session.commit()
                    btns = [("qris", "QRIS"), ("bank", "Transfer"), ("cod", "COD")]
                    kirim_waha_buttons(chat_id, f"Total Rp {total:,}", "Bayar:", btns, session_name)
                    if nomor_murni != toko.id: kirim_waha(toko.id, f"🔔 ORDER Rp {total:,}", session_name)
                else: kirim_waha(chat_id, jawaban, session_name)
        return "OK", 200

    except Exception as e:
        logging.error(f"Webhook Fatal: {e}")
        # Return 200 to stop WhatsApp from retrying endlessly on buggy logic
        return "ErrHandled", 200
