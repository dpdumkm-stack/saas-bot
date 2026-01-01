from flask import Blueprint, request, jsonify, current_app
from app.config import Config
from app.extensions import db, limiter
from app.models import Toko, Menu, Customer, ChatLog, BroadcastJob, SystemConfig, Subscription
from app.services.waha import kirim_waha, kirim_waha_raw, kirim_waha_image_raw, kirim_waha_image_url, kirim_waha_buttons, create_waha_session, get_waha_qr_retry, format_nomor, get_waha_pairing_code
from app.services.payment import create_payment_link
from app.services.sales_engine import check_and_send_followups
from app.services.gemini import tanya_gemini, analisa_bukti_transfer, upload_knowledge_base
from app.services.shipping import search_city, get_shipping_cost, get_city_name
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

@webhook_bp.route('/api/cron', methods=['GET'])
def api_cron():
    """Manual Trigger for Sales Engine"""
    check_and_send_followups(current_app._get_current_object())
    return jsonify({"status": "executed"}), 200

@webhook_bp.route('/webhook', methods=['POST'])
@limiter.limit("200 per minute")
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

    # 1.5 TRIGGER SALES ENGINE (Lazy Scheduler)
    try:
        app_ctx = current_app._get_current_object()
        threading.Thread(target=check_and_send_followups, args=(app_ctx,)).start()
    except Exception as e:
        logging.error(f"Scheduler Trigger Error: {e}")


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
        
        # Ignore Broadcasts / Groups / Newsletters already handled at top
        if "@g.us" in chat_id or "status@broadcast" in chat_id or "@newsletter" in chat_id: 
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

            # 0.5 HANDLE TURBO REGISTRATION (REG_AUTO)
            if body.startswith("REG_AUTO"):
                try:
                    # Format: REG_AUTO | Nama: [Name] | Kat: [Cat] | Paket: [Tier]
                    parts = body.split('|')
                    name = parts[1].split(':')[1].strip()
                    cat = parts[2].split(':')[1].strip()
                    tier = parts[3].split(':')[1].strip()
                    
                    # Create/Update Sub
                    sub = Subscription.query.filter_by(phone_number=nomor_murni).first()
                    if not sub:
                        sub = Subscription(phone_number=nomor_murni)
                        db.session.add(sub)
                    
                    sub.name = name
                    sub.category = cat
                    sub.tier = tier
                    sub.status = 'DRAFT'
                    sub.payment_status = 'unpaid'
                    sub.step = 3
                    db.session.commit()
                    
                    # Generate Link
                    price_map = {'STARTER': 99000, 'BUSINESS': 199000, 'PRO': 349000}
                    amount = price_map.get(tier, 99000)
                    order_id = f"SUB-{nomor_murni}-{int(time.time())}"
                    sub.order_id = order_id
                    
                    # Call Snap
                    cust_details = {'first_name': name, 'phone': nomor_murni}
                    item_details = [{'id': tier, 'price': amount, 'quantity': 1, 'name': f"Paket {tier}"}]
                    pay_link = create_payment_link({'order_id': order_id, 'amount': amount, 'customer_details': cust_details, 'item_details': item_details})
                    
                    sub.payment_url = pay_link
                    db.session.commit()
                    
                    msg = (
                        f"👋 Halo {name}!\n"
                        f"Terima kasih telah memilih Paket {tier} ({cat}).\n\n"
                        f"🔔 *INVOICE PEMBAYARAN*\n"
                        f"Total: Rp {amount:,.0f}\n"
                        f"Link: {pay_link}\n\n"
                        f"_Setelah bayar, Kode Aktivasi akan muncul otomatis di layar._\n\n"
                        f"📝 *Salah tulis nama? Balas:*\n"
                        f"`/gantinama {name}`\n\n"
                        f"🔁 *Salah pilih paket? Ketik:*\n"
                        f"`/batal`"
                    )
                    kirim_waha(chat_id, msg, MASTER_SESSION)
                    return "TurboPaid", 200     
                except Exception as e:
                    logging.error(f"Turbo Error: {e}")
                    kirim_waha(chat_id, "⚠️ Gagal proses otomatis. Silakan ketik **/daftar**.", MASTER_SESSION)
                    return "Error", 500

            # 0.6 HANDLE NAME CORRECTION (/gantinama)
            if body.lower().startswith("/gantinama"):
                 sub = Subscription.query.filter_by(phone_number=nomor_murni).first()
                 if sub:
                     new_name = body.replace("/gantinama", "").replace("/Gantinama", "").strip()
                     if new_name:
                         sub.name = new_name
                         db.session.commit()
                         kirim_waha(chat_id, f"✅ Nama toko diubah jadi: *{new_name}*\nLink pembayaran lama masih valid.", MASTER_SESSION)
                         return "Renamed", 200

            # --- Conversational Registration Flow ---
            
            # 1. TRIGGER / GREETING
            greeting_triggers = ["/daftar", "halo", "hi", "mau daftar"]
            # Check for Link Triggers
            tier_selected = None
            if "mau daftar paket starter" in body.lower(): tier_selected = "STARTER"
            elif "mau daftar paket business" in body.lower(): tier_selected = "BUSINESS"
            elif "mau daftar paket pro" in body.lower(): tier_selected = "PRO"
            elif "mau coba gratis" in body.lower(): tier_selected = "TRIAL_BUSINESS"

            if any(t in body.lower() for t in greeting_triggers) or tier_selected:
                sub = Subscription.query.filter_by(phone_number=nomor_murni).first()
                
                # If already Active
                if sub and sub.status == 'ACTIVE':
                    # Check Expiry
                    if sub.expired_at and sub.expired_at < datetime.now():
                        sub.status = 'EXPIRED'; db.session.commit()
                        kirim_waha(chat_id, "❌ Masa berlangganan Anda telah habis.", MASTER_SESSION)
                        return "Exp", 200
                    kirim_waha(chat_id, "✅ Anda sudah terdaftar! Ketik /kode untuk sambungkan HP.", MASTER_SESSION)
                    return "Active", 200

                # Create New Draft
                if not sub:
                    sub = Subscription(phone_number=nomor_murni)
                    db.session.add(sub)
                
                # Set Initial State
                sub.status = 'DRAFT'
                sub.step = 1
                if tier_selected:
                     # Map Trial Business
                     if tier_selected == "TRIAL_BUSINESS":
                         sub.tier = "BUSINESS" # Grants business features
                         sub.payment_status = "trial"
                     else:
                         sub.tier = tier_selected
                         sub.payment_status = "unpaid"
                # If just /daftar, default to Starter or Ask? Let's default to Starter for now or just proceed.
                
                db.session.commit()
                kirim_waha(chat_id, "Halo! 👋 Selamat datang di Asisten UMKM.\n\nSiapa nama Toko/Bisnis Anda?", MASTER_SESSION)
                return "Step1", 200

            # 0. HANDLE CANCELLATION
            if body.lower() in ["/batal", "batal", "cancel", "tidak jadi"]:
                sub = Subscription.query.filter_by(phone_number=nomor_murni, status='DRAFT').first()
                if sub:
                    db.session.delete(sub)
                    db.session.commit()
                    kirim_waha(chat_id, "❌ Pendaftaran dibatalkan.\n\nKetik **/daftar** jika ingin mulai lagi.", MASTER_SESSION)
                    return "Cancelled", 200

            # 1. HANDLE NEW REGISTRATION FLOW
            # Check if user has ongoing registration
            sub = Subscription.query.filter_by(phone_number=nomor_murni, status='DRAFT').first()
            if sub:
                # STEP 1: ASK NAME -> ASK CATEGORY
                if sub.step == 1:
                    sub.name = body.strip()
                    sub.step = 2
                    db.session.commit()
                    kirim_waha(chat_id, f"Salam kenal, {sub.name}! 🔥\n\nKategori bisnisnya apa?\nA. Makanan & Minuman 🍔\nB. Jasa / Service 🛠️\nC. Retail / Toko 🛍️\n\n(Ketik A, B, atau C)", MASTER_SESSION)
                    return "Step2", 200
                
                # STEP 2: SAVE CATEGORY -> FINALIZE
                elif sub.step == 2:
                    cat_input = body.lower().strip()
                    cat_map = {'a': 'F&B', 'b': 'Service', 'c': 'Retail'}
                    
                    # VALIDATION: Check if input is A/B/C
                    if cat_input not in cat_map:
                        # SMART EDIT: Assume user wants to simple correct Name
                        sub.name = body.strip()
                        db.session.commit()
                        kirim_waha(chat_id, f"📝 Nama Toko diupdate: *{sub.name}*\n\nOke, sekarang pilih kategorinya:\nA. Makanan & Minuman 🍔\nB. Jasa / Service 🛠️\nC. Retail / Toko 🛍️\n\n(Ketik A, B, atau C)", MASTER_SESSION)
                        return "NameCorrected", 200

                    cat = cat_map[cat_input]
                    sub.category = cat
                    
                    # Logic: If Trial -> Activate 3 Days. If Paid -> Send Link.
                    
                    # Case A: Free Trial (from "Coba Gratis" or generic /daftar)
                    if sub.payment_status == 'trial' or not sub.tier:
                         sub.status = 'TRIAL' # or ACTIVE
                         sub.tier = 'BUSINESS' # Default trial tier
                         sub.expired_at = datetime.now() + timedelta(days=3)
                         sub.step = 0
                         
                         # Create System Resources
                         new_sess = f"session_{nomor_murni}"
                         if create_waha_session(new_sess):
                             new_toko = Toko(id=nomor_murni, nama=sub.name, kategori=cat, session_name=new_sess, remote_token=str(uuid.uuid4())[:8])
                             db.session.add(new_toko)
                             db.session.commit()
                             msg = (
                                 f"✅ **Pendaftaran Berhasil!**\n\n"
                                 f"Toko: {sub.name}\n"
                                 f"Paket: {sub.tier} (Trial 3 Hari)\n\n"
                                 f"Ketik **/kode** untuk menyambungkan WhatsApp.\n\n"
                                 f"📚 *Bingung? Lihat Panduan:*\n"
                                 f"{request.url_root}tutorial"
                             )
                             kirim_waha(chat_id, msg, MASTER_SESSION)
                         else:
                             kirim_waha(chat_id, "Gagal setup server. Coba lagi nanti.", MASTER_SESSION)
                             
                    # Case B: Paid Tier Selected
                    else:
                        sub.step = 3 # Payment Pending
                        db.session.commit()
                        
                        # Generate Payment Link
                        price_map = {'STARTER': 99000, 'BUSINESS': 199000, 'PRO': 349000}
                        amount = price_map.get(sub.tier, 99000)
                        order_id = f"SUB-{nomor_murni}-{int(time.time())}"
                        sub.order_id = order_id
                        
                        link = create_payment_link({
                            'order_id': order_id,
                            'amount': amount,
                            'customer_details': {'first_name': sub.name, 'phone': format_nomor(nomor_murni)},
                            'item_details': [{'id': sub.tier, 'price': amount, 'quantity': 1, 'name': f"Paket {sub.tier}"}]
                        })
                        
                        if link:
                            sub.payment_url = link
                            db.session.commit()
                            kirim_waha(chat_id, f"Sip! Paket {sub.tier} dipilih.\n\nSilakan selesaikan pembayaran Rp {amount:,} di link ini:\n👉 {link}\n\n(Akun otomatis aktif setelah bayar)", MASTER_SESSION)
                        else:
                            kirim_waha(chat_id, "Gagal membuat link pembayaran. Hubungi Admin.", MASTER_SESSION)
                            
                    return "DoneReg", 200

            # 3. EXISTING ACTIVE USER COMMANDS
            if body.lower().startswith("/kode"):
                # Check Subscription
                sub = Subscription.query.filter_by(phone_number=nomor_murni).first()
                if not sub or sub.status not in ['ACTIVE', 'TRIAL']:
                    kirim_waha(chat_id, "❌ Akses Ditolak. Anda belum berlangganan/Trial habis.", MASTER_SESSION)
                    return "SubErr", 200
                
                toko = Toko.query.get(nomor_murni)
                if not toko:
                    kirim_waha(chat_id, "❌ Toko belum siap. Ketik /daftar dulu.", MASTER_SESSION)
                    return "NoToko", 200
                
                kirim_waha(chat_id, "⏳ Sedang meminta Kode Tautan...", MASTER_SESSION)
                code = get_waha_pairing_code(toko.session_name, nomor_murni)
                if code:
                    msg_code = (
                        f"Kode Tautan Anda:\n*{code}*\n\n"
                        "Cara Masukkan Kode:\n"
                        "1. Buka WhatsApp di HP Toko.\n"
                        "2. Klik Titik Tiga (⋮) atau Pengaturan ⚙️.\n"
                        "3. Pilih menu *Perangkat tertaut* (Linked devices).\n"
                        "4. Klik tombol *Tautkan perangkat* (Link a device).\n"
                        "5. Saat muncul kamera scan, klik tulisan kecil di paling bawah: *Tautkan dengan nomor telepon saja*.\n"
                        "6. Masukkan Kode di atas."
                    )
                    kirim_waha(chat_id, msg_code, MASTER_SESSION)
                else:
                    kirim_waha(chat_id, "❌ Gagal mengambil kode. Pastikan sesi belum terhubung/timeout.", MASTER_SESSION)
                return "Kode", 200
            
            elif body == "/scan":
                toko = Toko.query.get(nomor_murni)
                if toko:
                    qr = get_waha_qr_retry(toko.session_name)
                    if qr: kirim_waha_image_raw(chat_id, qr, "📲 Scan ini.", MASTER_SESSION)
                return "Scan", 200

            elif body.lower() == "/ping":
                kirim_waha(chat_id, "🏓 Pong! (SaaS Bot Active)", MASTER_SESSION)
                return "Ping", 200

            elif body.lower() == "/unreg":
                # RESET DATA USER
                toko = Toko.query.get(nomor_murni)
                sub = Subscription.query.filter_by(phone_number=nomor_murni).first()
                
                deleted = []
                if toko:
                    db.session.delete(toko)
                    deleted.append("Data Toko")
                if sub:
                    db.session.delete(sub)
                    deleted.append("Data Langganan")
                
                if deleted:
                    db.session.commit()
                    kirim_waha(chat_id, f"♻️ Reset Berhasil: {', '.join(deleted)} dihapus.\nSilakan ketik **/daftar** untuk mulai ulang.", MASTER_SESSION)
                else:
                    kirim_waha(chat_id, "⚠️ Data tidak ditemukan. Ketik **/daftar** untuk mulai baru.", MASTER_SESSION)
                return "Unreg", 200
                return "Ping", 200

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
                
                elif body.startswith("/setlokasi"):
                    query = body.replace("/setlokasi", "").strip()
                    if len(query) < 3:
                        kirim_waha(chat_id, "ℹ️ Ketik nama kota minimal 3 huruf. Contoh: /setlokasi bandung", session_name)
                        return "Loc", 200
                    
                    matches = search_city(query)
                    if not matches:
                        kirim_waha(chat_id, "❌ Kota tidak ditemukan.", session_name)
                    else:
                        msg = "📍 Pilih Lokasi (Balas Angkanya):\n"
                        for i, m in enumerate(matches):
                             msg += f"{i+1}. {m['name']}, {m['province']}\n"
                        msg += "\n(Ketik 1, 2, dst)"
                        
                        # Store state
                        # Simple state hack: use 'setup_step' + saving candidate list in last_reset temporarily or just re-search?
                        # Better: Use 'setup_step'='LOC_SEARCH' and store list in memory/json?
                        # Since memory is cheap here: reuse 'last_reset' (hacky) or add 'temp_data' column.
                        # For MVP, let's persist result in a simple way or just handle generic number response.
                        # We will use 'setup_step' and store matches in 'knowledge_base_name' temporarily? No, dangerous.
                        # Let's just create a quick robust check.
                        # We can store matches in 'admins' field? (Since it's text json).
                        # Let's use 'admins' for now as temp storage for setup flow since admins is unused list.
                        toko.setup_step = "LOC_SEARCH"
                        toko.admins = json.dumps(matches) 
                        db.session.commit()
                        kirim_waha(chat_id, msg, session_name)
                    return "LocSearch", 200

                # HANDLE LOCATION SELECTION (OWNER)
                if toko.setup_step == "LOC_SEARCH" and body.isdigit():
                    try:
                        idx = int(body) - 1
                        matches = json.loads(toko.admins)
                        if 0 <= idx < len(matches):
                            sel = matches[idx]
                            toko.shipping_origin_id = sel['id']
                            toko.setup_step = "NONE"
                            toko.admins = "[]" # Reset
                            db.session.commit()
                            kirim_waha(chat_id, f"✅ Lokasi Toko diset: {sel['name']}", session_name)
                            return "LocSet", 200
                    except: pass

                if body.startswith("/broadcast"):
                    msg = body.replace("/broadcast","").strip()
                    custs = [c.nomor_hp for c in toko.customers]
                    if custs:
                        job = BroadcastJob(toko_id=toko.id, pesan=msg, target_list=json.dumps(custs))
                        db.session.add(job); db.session.commit()
                        kirim_waha(chat_id, "🚀 Broadcast antri.", session_name)
                    return "Bc", 200
                
                # KB UPLOAD (DOCUMENT)
                # Check for media payload in WAHA
                # Usually: msg_obj['media'] or msg_obj['body'] is url if setup
                # For Waha Plus, check 'hasMedia' or 'media' object inside payload
                media_url = None
                mime_type = "text/plain" 
                filename = "doc"
                
                # Try extract media
                if msg_obj.get('hasMedia') or msg_obj.get('media'):
                     # WAHA logic: File might be in body (url) or separate
                     # Assuming url_file logic applies if we have it
                     # Let's verify 'url_file' variable usage (need to ensure it's extracted earlier)
                     pass

                # Re-extract url_file cleanly if not done globally
                url_file = None
                if msg_obj.get('hasMedia'):
                     # WAHA Plus often puts the binary or url.
                     # If using 'downloadMedia' endpoint or contained in body.
                     # Let's assume standard 'media' dict or 'body' is url
                     m = msg_obj.get('media', {})
                     url_file = m.get('url') or msg_obj.get('body') # simplified
                     mime_type = m.get('mimetype') or "application/pdf"
                     filename = m.get('filename') or "document"
                
                if url_file and ("pdf" in mime_type or "text" in mime_type or "word" in mime_type):
                     kirim_waha(chat_id, "🧠 Sedang membaca dokumen...", session_name)
                     fb, mime = download_file(url_file)
                     if fb:
                         # Upload to Gemini
                         kb_id = upload_knowledge_base(fb, mime, filename)
                         if kb_id:
                             toko.knowledge_base_file_id = kb_id
                             toko.knowledge_base_name = filename
                             db.session.commit()
                             kirim_waha(chat_id, f"✅ Otak Bot diupdate!\nFile: {filename}\nSekarang saya bisa menjawab pertanyaan dari dokumen ini.", session_name)
                         else:
                             kirim_waha(chat_id, "❌ Gagal memproses ke AI.", session_name)
                     return "Doc", 200

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
                    db.session.add(cust)
                
                # SALES ENGINE: Update Interaction
                cust.last_interaction = datetime.now()
                cust.followup_status = 'NONE' # Reset follow-up status because they replied
                db.session.commit()

                if cust.is_muted_until and cust.is_muted_until > datetime.now(): return "Muted", 200

                # --- IMAGE / VISION HANDLER ---
                image_data = None
                if url_file:
                    # ⚠️ RESTRICTION: BLOCK VIDEO
                    if "video" in mime_type:
                        kirim_waha(chat_id, "❌ Maaf, saya tidak bisa melihat video. Kirim foto saja ya! 📷", session_name)
                        return "VideoBlocked", 200

                    kirim_waha(chat_id, "👀 Melihat gambar...", session_name)
                    fb, mime = download_file(url_file)
                    
                    if fb:
                        # CASE A: Payment Verification (High Priority)
                        if cust.order_status == 'WAIT_TRANSFER':
                            res = analisa_bukti_transfer(fb, mime, cust.current_bill)
                            if res['is_valid'] and res['fraud_score'] < 30:
                                kirim_waha(chat_id, "✅ Lunas!", session_name)
                                kirim_waha_image_url(toko.id, url_file, f"💰 MASUK Rp {cust.current_bill:,}", session_name)
                                cust.order_status = 'NONE'; db.session.commit()
                            else:
                                kirim_waha(chat_id, "Dicek manual.", session_name)
                                kirim_waha_image_url(toko.id, url_file, "⚠️ BUKTI MENCURIGAKAN!", session_name)
                            return "ImgPaid", 200
                        
                        # CASE B: General Vision (Visual Q&A)
                        else:
                            # Pass to tanya_gemini as context
                            image_data = {'mime_type': mime, 'data': fb}
                
                # --- CHAT & VISION RESPONSE ---
                jawaban = tanya_gemini(body, toko, cust, image_data=image_data)
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
                
                elif "[CEK_ONGKIR" in jawaban:
                    # Format: [CEK_ONGKIR:NamaKota]
                    try:
                        dest_query = jawaban.split("[CEK_ONGKIR:")[1].split("]")[0]
                        kirim_waha(chat_id, f"🚚 Cek ongkir ke {dest_query}...", session_name)
                        
                        # Find destination ID
                        matches = search_city(dest_query)
                        if matches and toko.shipping_origin_id:
                            # Use first match
                            dest_id = matches[0]['id']
                            costs = get_shipping_cost(toko.shipping_origin_id, dest_id)
                            kirim_waha(chat_id, f"📦 Ongkir ke {matches[0]['name']}:\n\n{costs}", session_name)
                        elif not toko.shipping_origin_id:
                            kirim_waha(chat_id, "Maaf, Toko belum set lokasi pengiriman.", session_name)
                        else:
                            kirim_waha(chat_id, "Maaf, lokasi tujuan tidak ditemukan.", session_name)
                    except Exception as e:
                        logging.error(f"Ongkir Error: {e}")
                        kirim_waha(chat_id, "Gagal cek ongkir.", session_name)
                
                else: kirim_waha(chat_id, jawaban, session_name)
        return "OK", 200

    except Exception as e:
        logging.error(f"Webhook Fatal: {e}")
        # Return 200 to stop WhatsApp from retrying endlessly on buggy logic
        return "ErrHandled", 200
