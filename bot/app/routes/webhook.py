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
@limiter.limit("30 per minute")
def webhook():
    try:
        data = request.json
        session_name = data.get('session', 'default')
        payload = data.get('payload', {})
        if not payload: return "No", 200

        # --- EVENT: Session Status Change (Auto Guide) ---
        event = data.get('event')
        if event == 'session.status':
            status = payload.get('status')
            if status == 'WORKING':
                toko = Toko.query.filter_by(session_name=session_name).first()
                if toko:
                    link_remote = f"http://localhost:5000/remote/{toko.remote_token}"
                    link_qr = "http://localhost:5000/admin/qr"
                    guide_msg = f"""🎉 *Selamat! Bot Toko Anda Sudah Aktif!* 🤖

Bot sekarang siap melayani pelanggan Anda 24/7.

📋 *PANDUAN PENGGUNAAN:*

1️⃣ *Isi Menu/Produk:*
   Ketik: `/menu [Nama Produk] [Harga]`
   Contoh: `/menu Nasi Goreng 15000`

2️⃣ *Kelola Stok & Harga:*
   Klik link ini untuk dashboard:
   {link_remote}

3️⃣ *Broadcast Promo:*
   Ketik pesan Anda, akhiri dengan `#all`
   Contoh: `Diskon 50% hari ini! #all`

🚀 *Tips:*
- Coba chat ke nomor ini dari HP lain untuk tes.
- Scan ulang kapan saja jika koneksi putus di: {link_qr}"""
                    def send_welcome():
                         time.sleep(3)
                         kirim_waha(toko.id, guide_msg, session_name)
                    threading.Thread(target=send_welcome).start()
                    logging.info(f"Welcome guide sent to {toko.id}")
            return "OK", 200

        chat_id = payload.get('from')
        body = payload.get('body', '')
        url_file = payload.get('mediaUrl')
        from_me = payload.get('fromMe', False)
        nomor_murni = format_nomor(chat_id)

        if "@g.us" in chat_id or "status@broadcast" in chat_id: return "Ignored", 200

        # --- A. ADMIN SAAS (MASTER) ---
        if session_name == MASTER_SESSION:
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
                lawan = format_nomor(payload.get('to'))
                cust = Customer.query.filter_by(toko_id=toko.id, nomor_hp=lawan).first()
                if not cust:
                    cust = Customer(toko_id=toko.id, nomor_hp=lawan); db.session.add(cust)
                cust.is_muted_until = datetime.now() + timedelta(minutes=30)
                db.session.commit()
                return "Me", 200

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
        return "Err", 500
