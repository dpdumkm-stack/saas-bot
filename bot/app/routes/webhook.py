import json
import logging
import threading
import requests
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from app.models import Toko, Subscription, Customer, ChatLog
from app.extensions import db
from app.services.waha import kirim_waha, mark_seen
from app.services.gemini import get_gemini_response
from app.services.sales_engine import check_and_send_followups
from app.config import Config

from app.utils import should_ignore_message, get_parsed_number

webhook_bp = Blueprint('webhook', __name__)

def handle_global_opt_out(cmd, nomor_murni, chat_id, session_id):
    """
    Handle global opt-out/opt-in commands for ANY session.
    """
    from app.feature_flags import FeatureFlags
    if not FeatureFlags.is_opt_out_enabled():
        return False

    # OPT-OUT
    if cmd in ['stop', 'berhenti', 'unsubscribe', 'keluar', 'opt-out']:
        from app.services.opt_out_manager import OptOutManager
        success = OptOutManager.add_to_blacklist(nomor_murni, 'user_request')
        if success:
            response = (
                "✅ *Unsubscribe Berhasil*\n\n"
                "Anda telah di-unsubscribe dari broadcast marketing.\n\n"
                "Untuk subscribe kembali, ketik: *START*"
            )
        else:
            response = "❌ Gagal unsubscribe. Silakan hubungi admin."
        
        kirim_waha(chat_id, response, session_id)
        return True
    
    # OPT-IN
    if cmd in ['start', 'mulai', 'subscribe', 'masuk', 'opt-in']:
        from app.services.opt_out_manager import OptOutManager
        success = OptOutManager.remove_from_blacklist(nomor_murni)
        if success:
            response = (
                "✅ *Subscribe Berhasil*\n\n"
                "Anda telah subscribe kembali ke broadcast marketing.\n\n"
                "Untuk unsubscribe, ketik: *STOP*"
            )
        else:
            response = "❌ Anda tidak bisa subscribe kembali. Silakan hubungi admin."
        
        kirim_waha(chat_id, response, session_id)
        return True
        
    return False

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    # Force rebuild: v1.0.2 - Global unreg handler
    # 1. Security Check (Webhook Secret)
    if Config.WEBHOOK_SECRET:
        # Check multiple possible headers for compatibility
        received_secret = (
            request.headers.get('X-Webhook-Secret') or 
            request.headers.get('X-Header-2') or 
            request.headers.get('Authorization') or 
            request.headers.get('apikey')
        )
        
        # Security Note: If using Authorization header, some systems might prefix with 'Bearer '
        if received_secret and received_secret.startswith('Bearer '):
            received_secret = received_secret.replace('Bearer ', '')

        if received_secret != Config.WEBHOOK_SECRET:
            # Debug info (masked)
            rec_val = str(received_secret or "")
            logging.warning(
                f"Unauthorized Webhook Access from {request.remote_addr}. "
                f"Expected len: {len(Config.WEBHOOK_SECRET)}, Received len: {len(rec_val)}. "
                f"Starts with: '{rec_val[:2]}...', Ends with: '...{rec_val[-2:]}'"
            )
            return jsonify({"status": "error", "reason": "unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"status": "ignored", "reason": "empty"}), 200

    # Handle session.status webhook (for auto-configuration)
    event = data.get('event', '')
    if event == 'session.status':
        payload = data.get('payload', {})
        session_name = data.get('session', 'unknown')
        status = payload.get('status', '')
        
        logging.info(f"📊 Session status update: {session_name} = {status}")
        
        # If session just became WORKING, auto-configure webhook
        if status == 'WORKING':
            logging.info(f"🔄 New session WORKING detected: {session_name}. Triggering auto-configuration...")
            from app.services.waha import configure_session_webhook
            success = configure_session_webhook(session_name)
            if success:
                logging.info(f"✅ Auto-configuration completed for {session_name}")
            else:
                logging.warning(f"⚠️  Auto-configuration failed for {session_name}. Manual setup may be needed.")
        
        return jsonify({"status": "ok"}), 200

    # 1. Standard Filters
    ignore, reason = should_ignore_message(data)
    if ignore:
        return jsonify({"status": "ignored", "reason": reason}), 200


    # 2. Context Extraction
    nomor_murni, chat_id = get_parsed_number(data)
    session_id = data.get('session', Config.MASTER_SESSION)
    payload = data.get('payload', {})
    body = payload.get('body', '')
    toko_id = session_id.replace("session_", "")

    # Auto mark as read
    mark_seen(chat_id, session_id)

    # 3. Trigger Sales Engine (Background)
    try:
        app_ctx = current_app._get_current_object()
        threading.Thread(target=check_and_send_followups, args=(app_ctx,)).start()
    except Exception as e:
        logging.error(f"Scheduler Trigger Error: {e}")

    # 3.5 GLOBAL COMMAND HANDLER (All Sessions)
    cmd = (body or "").lower().strip()

    # 3.6 GLOBAL OPT-OUT (Priority High - All Sessions)
    if handle_global_opt_out(cmd, nomor_murni, chat_id, session_id):
        return "OK", 200
    
    # SECURITY HARDENING: Admin commands are only for Master Session (onboarding) 
    # or the actual Owner (Identity Guard)
    is_master = (session_id == Config.MASTER_SESSION)
    is_owner = (nomor_murni == toko_id)
    
    if is_master or is_owner:
        if cmd in ['/help', '/bantuan', '/menu']:
            # Get Context for Merchant
            sub = Subscription.query.filter_by(phone_number=toko_id).first()
            status_info = f"\n📊 *Status:* {sub.status if sub else 'Unknown'} | s/d: {sub.expired_at.strftime('%d %b %Y') if sub and sub.expired_at else '-'}"
            
            help_msg = (
                f"🤖 *WALI AI - MERCHANT HUB*{status_info}\n\n"
                "Gunakan perintah berikut untuk mengelola bot Anda:\n\n"
                "🛠️ *Manajemen Produk:*\n"
                "- `/list_menu` - Daftar semua produk\n"
                "- `/tambah_menu [Nama] [Harga] [Stok]`\n"
                "- `/hapus_menu [ID]`\n\n"
                "⚙️ *Akun & Koneksi:*\n"
                "- `/status` - Cek detail langganan\n"
                "- `/scan` - Hubungkan kembali WhatsApp\n"
                "- `/ping` - Cek status server bot\n\n"
                "🚮 *Data:* \n"
                "- `/unreg` - Berhenti & Hapus Data (Nuclear Reset)\n"
                "- `/reactivate` - Reaktivasi akun di masa tenggang\n\n"
                "💡 *Tip:* Kirim `/help` dari nomor owner toko untuk melihat menu ini."
            )
            kirim_waha(chat_id, help_msg, session_id)
            return "OK", 200

        if cmd == '/unreg':
            from app.services.registration import handle_registration
            from app.utils import normalize_phone_number
            
            # Normalize phone for DB lookup
            normalized_phone = normalize_phone_number(nomor_murni)
            
            # DEBUG LOGGING
            logging.info(f"🔍 UNREG DEBUG: raw nomor_murni='{nomor_murni}', normalized='{normalized_phone}', session='{session_id}', chat_id='{chat_id}'")
            
            # Call registration handler with normalized phone
            handle_registration(normalized_phone, body, chat_id, session_id)
            return "OK", 200

        if cmd == '/reactivate':
            from app.services.subscription_manager import reactivate_from_grace
            from app.utils import normalize_phone_number
            
            normalized_phone = normalize_phone_number(nomor_murni)
            logging.info(f"🔄 REACTIVATE DEBUG: raw='{nomor_murni}', normalized='{normalized_phone}'")
            
            res = reactivate_from_grace(normalized_phone)
            if not res['success']:
                kirim_waha(chat_id, f"❌ Reaktivasi Gagal: {res['message']}", session_id)
            return "OK", 200

    # 4. MASTER SESSION LOGIC (Registration & Admin)
    if session_id == Config.MASTER_SESSION:
        # A. Admin & Health Check Commands
        cmd = (body or "").lower()
        if cmd == '/ping':
            logging.info(f"DEBUG: /ping detected for {chat_id}")
            kirim_waha(chat_id, "🏓 Pong! (SaaS Bot Active)", session_id)
            return "OK", 200
        
        # B. Opt-Out/Opt-In Handlers (Phase 8A)
        if nomor_murni == Config.SUPER_ADMIN_WA:
            if cmd == '/pintu':
                from app.models import SystemConfig
                cfg = SystemConfig.query.get('maintenance_mode')
                status = "TERTUTUP (Aktif)" if cfg and cfg.value=='true' else "TERBUKA (Bebas)"
                kirim_waha(chat_id, f"Pintu Maintenance saat ini: {status}", session_id)
                return "OK", 200
            
            # BROADCAST COMMAND (Superadmin Only)
            if cmd == '/broadcast' or cmd.startswith('/broadcast '):
                from app.feature_flags import FeatureFlags
                
                # Check if feature is enabled
                if not FeatureFlags.is_broadcast_enabled():
                    kirim_waha(chat_id, "⚠️ Fitur broadcast sedang dalam maintenance", session_id)
                    return "OK", 200
                
                # If just "/broadcast" without args, show menu
                if cmd == '/broadcast':
                    from app.services.broadcast_manager import BroadcastManager
                    menu = BroadcastManager.format_segment_menu()
                    kirim_waha(chat_id, menu, session_id)
                    
                    # Store state: waiting for segment selection or CSV
# Customer already imported globally
                    customer = Customer.query.filter_by(toko_id='MASTER', nomor_hp=nomor_murni).first()
                    if not customer:
                        customer = Customer(toko_id='MASTER', nomor_hp=nomor_murni)
                        db.session.add(customer)
                    customer.flow_state = 'broadcast_awaiting_target'
                    db.session.commit()
                    
                    return "OK", 200
                
                # If "/broadcast <segment> <message>", parse and execute
                parts = body.split(maxsplit=2)
                if len(parts) >= 3:
                    segment = parts[1]
                    message = parts[2]
                    
                    from app.services.broadcast_manager import BroadcastManager
                    targets = BroadcastManager.get_segment_targets(segment)
                    
                    if not targets:
                        kirim_waha(chat_id, f"❌ Segment '{segment}' tidak ditemukan atau kosong", session_id)
                        return "OK", 200
                    
                    # Confirmation step
                    confirm_msg = (
                        f"📊 *KONFIRMASI BROADCAST*\n\n"
                        f"Target: {segment}\n"
                        f"Jumlah: {len(targets):,} nomor\n"
                        f"Estimasi waktu: ~{len(targets) * 12 // 60} menit\n\n"
                        f"Pesan:\n{message[:100]}{'...' if len(message) > 100 else ''}\n\n"
                        f"⚠️ Ketik *CONFIRM* untuk lanjut atau *CANCEL*"
                    )
                    kirim_waha(chat_id, confirm_msg, session_id)
                    
                    # Store pending broadcast
                    # Customer already imported globally
                    customer = Customer.query.filter_by(toko_id='MASTER', nomor_hp=nomor_murni).first()
                    if not customer:
                        customer = Customer(toko_id='MASTER', nomor_hp=nomor_murni)
                        db.session.add(customer)
                    
                    import json
                    customer.flow_state = 'broadcast_pending_confirm'
                    customer.flow_data = json.dumps({
                        'targets': targets,
                        'message': message,
                        'source': segment
                    })
                    db.session.commit()
                    
                    return "OK", 200
                else:
                    kirim_waha(chat_id, "Format: /broadcast <segment> <pesan>\nContoh: /broadcast active Promo 20% OFF!", session_id)
                    return "OK", 200
            
            # Handle broadcast confirmation
            if body and body.upper() in ['CONFIRM', 'CANCEL']:
                # Customer already imported globally
                customer = Customer.query.filter_by(toko_id='MASTER', nomor_hp=nomor_murni).first()
                
                if customer and customer.flow_state == 'broadcast_pending_confirm':
                    if body.upper() == 'CANCEL':
                        customer.flow_state = None
                        customer.flow_data = None
                        db.session.commit()
                        kirim_waha(chat_id, "❌ Broadcast dibatalkan", session_id)
                        return "OK", 200
                    
                    # Execute broadcast
                    import json
                    data = json.loads(customer.flow_data)
                    targets = data['targets']
                    message = data['message']
                    source = data.get('source', 'manual')
                    
                    from app.services.broadcast_manager import BroadcastManager
                    job_id = BroadcastManager.create_broadcast_job('SUPERADMIN', message, targets, source)
                    
                    if job_id:
                        kirim_waha(chat_id, f"✅ Broadcast dimulai! (Job #{job_id})\n🕐 Estimasi selesai dalam ~{len(targets) * 12 // 60} menit", session_id)
                    else:
                        kirim_waha(chat_id, "❌ Gagal membuat broadcast job. Cek logs untuk detail.", session_id)
                    
                    customer.flow_state = None
                    customer.flow_data = None
                    db.session.commit()
                    return "OK", 200
            
            # Handle segment selection (if waiting for target)
            # Customer already imported globally
            customer = Customer.query.filter_by(toko_id='MASTER', nomor_hp=nomor_murni).first()
            
            if customer and customer.flow_state == 'broadcast_awaiting_target':
                # Check if it's a number (segment selection)
                if body and body.strip().isdigit():
                    segment_map = {
                        '1': 'all_merchants',
                        '2': 'active',
                        '3': 'expired',
                        '4': 'trial',
                        '5': 'starter',
                        '6': 'business',
                        '7': 'pro',
                    }
                    
                    segment = segment_map.get(body.strip())
                    if segment:
                        from app.services.broadcast_manager import BroadcastManager
                        targets = BroadcastManager.get_segment_targets(segment)
                        
                        if targets:
                            kirim_waha(chat_id, f"✅ Segment dipilih: {segment} ({len(targets):,} nomor)\n\n💬 Sekarang ketik PESAN BROADCAST yang ingin dikirim:", session_id)
                            
                            customer.flow_state = 'broadcast_awaiting_message'
                            import json
                            customer.flow_data = json.dumps({'targets': targets, 'source': segment})
                            db.session.commit()
                        else:
                            kirim_waha(chat_id, "❌ Segment kosong, silakan pilih yang lain", session_id)
                    else:
                        kirim_waha(chat_id, "❌ Pilihan tidak valid. Ketik angka 1-7 atau kirim file CSV", session_id)
                    
                    return "OK", 200
            
            # Handle message input (after segment selected)
            if customer and customer.flow_state == 'broadcast_awaiting_message':
                if body:
                    import json
                    data = json.loads(customer.flow_data)
                    targets = data['targets']
                    source = data['source']
                    
                    # Show confirmation
                    confirm_msg = (
                        f"📊 *KONFIRMASI BROADCAST*\n\n"
                        f"Target: {source}\n"
                        f"Jumlah: {len(targets):,} nomor\n"
                        f"Estimasi waktu: ~{len(targets) * 12 // 60} menit\n\n"
                        f"Pesan:\n{body[:200]}{'...' if len(body) > 200 else ''}\n\n"
                        f"⚠️ Ketik *CONFIRM* untuk lanjut atau *CANCEL*"
                    )
                    kirim_waha(chat_id, confirm_msg, session_id)
                    
                    customer.flow_state = 'broadcast_pending_confirm'
                    data['message'] = body
                    customer.flow_data = json.dumps(data)
                    db.session.commit()
                    
                return "OK", 200

        # B. Registration Flow
        body_text = (body or "").upper()
        is_submitting_reg = any(x in body_text for x in ["/DAFTAR", "REG_AUTO", "/UNREG", "/PINTU", "UPGRADE", "BELI", "PERPANJANG"])
        is_registered_owner = Subscription.query.filter_by(phone_number=nomor_murni).first() is not None
        
        if is_registered_owner or is_submitting_reg:
            # Upgrade / Payment Flow
            if body_text.startswith("UPGRADE") or body_text.startswith("BELI") or body_text == "PERPANJANG":
                parts = body_text.split()
                if len(parts) < 2:
                    # Show Menu
                    menu = (
                        "📦 *PILIHAN PAKET WALI.AI*\n\n"
                        "1️⃣ *STARTER* - Rp 99.000/bln\n"
                        "   (200 Chat, 1 No WA)\n\n"
                        "2️⃣ *PRO* - Rp 199.000/bln\n"
                        "   (Unlimited Chat, 2 No WA)\n\n"
                        "3️⃣ *BUSINESS* - Rp 499.000/3bln\n"
                        "   (VIP Support, 5 No WA)\n\n"
                        "💡 *Cara Beli:*\n"
                        "Ketik *BELI [NAMA_PAKET]*\n"
                        "Contoh: *BELI PRO*"
                    )
                    kirim_waha(chat_id, menu, session_id)
                    return "OK", 200
                else:
                    # Process Purchase
                    package_key = parts[1] # e.g. PRO
                    
                    # Call Service
                    from app.services.transaction_service import create_subscription_transaction
                    
                    # We need name from Subscription if possible, or use "Pelanggan"
                    sub = Subscription.query.filter_by(phone_number=nomor_murni).first()
                    name = sub.name if sub else "Pelanggan"
                    
                    kirim_waha(chat_id, "⏳ Mohon tunggu, sedang membuat link pembayaran...", session_id)
                    
                    res = create_subscription_transaction(nomor_murni, name, package_key)
                    
                    if res['status'] == 'success':
                        msg = (
                            f"✅ *Link Pembayaran Siap!*\n\n"
                            f"Paket: {res['package_name']}\n"
                            f"Harga: Rp {res['amount']:,}\n\n"
                            f"👉 *Klik Link Ini:* \n{res['payment_url']}\n\n"
                            f"_(Link berlaku 24 jam)_"
                        )
                        kirim_waha(chat_id, msg, session_id)
                    else:
                        kirim_waha(chat_id, f"❌ Gagal: {res['message']}", session_id)
                    
                    return "OK", 200

            from app.services.registration import handle_registration
            handle_registration(nomor_murni, body, chat_id, session_id)
            return "OK", 200
            
        return "Ignored: Unknown on Master", 200

    # 5. AI RESPONDER LOGIC (Store Sessions)
    with current_app.app_context():
        # Cleaned up imports
        toko = Toko.query.get(toko_id)
        if not toko:
            return "Toko Not Found", 200
            
        # --- IDENTITY GUARD ---
        # Bot should not be a customer of itself.
        is_self = (nomor_murni == toko_id)
        
        if is_self:
            # Skip customer registration and most logic
            customer = None
            logging.info(f"🚫 Identity Guard: Bot {toko_id} chatting with itself. Skipping customer logic.")
        else:
            customer = Customer.query.filter_by(toko_id=toko_id, nomor_hp=nomor_murni).first()
            if not customer:
                customer = Customer(toko_id=toko_id, nomor_hp=nomor_murni)
                db.session.add(customer)
                
            customer.last_interaction = db.func.now()
            db.session.commit()
        
        # 3. Security (Fixed Identity Guard)
        is_owner = (nomor_murni == toko_id or nomor_murni == Config.SUPER_ADMIN_WA)
        
        # Health Check Command
        if (body or "").lower() == '/ping':
            kirim_waha(chat_id, f"🏓 Pong! (Bot {toko.nama} Aktif)", session_id)
            return "OK", 200

        # Help & Command Trigger
        if (body or "").lower() in ['/help', '/menu', '/bantuan']:
            if is_owner:
                # Get Sub for context
                sub = Subscription.query.filter_by(phone_number=toko_id).first()
                status_str = f"| Exp: {sub.expired_at.strftime('%d/%m/%y') if sub and sub.expired_at else '-'}"
                
                msg = (
                    f"🤖 *WALI AI - MERCHANT HUB*\n"
                    f"🏪 Toko: *{toko.nama}* {status_str}\n\n"
                    "🛠️ *Atur Menu & Produk:*\n"
                    "- `/list_menu` - Daftar semua produk\n"
                    "- `/tambah_menu [Nama] [Harga] [Stok]`\n"
                    "- `/hapus_menu [ID]`\n\n"
                    "⚙️ *System & Akun:*\n"
                    "- `/status` - Detail masa aktif\n"
                    "- `/scan` - Scan ulang WA\n"
                    "- `/ping` - Cek status bot\n"
                    "- `/help` - Menu ini"
                )
            else:
                msg = (
                    f"👋 *Halo! Saya Asisten AI {toko.nama}.*\n\n"
                    "Silakan tanya apa saja tentang produk kami, contoh:\n"
                    "👉 _\"Lihat menu dong\"_\n"
                    "👉 _\"Ada promo apa hari ini?\"_\n"
                    "👉 _\"Alamat tokonya dimana?\"_\n\n"
                    "_Saya siap membantu Kakak 24 jam!_ 😊"
                )
            kirim_waha(chat_id, msg, session_id)
            return "OK", 200
        
        # Smart Filter (Spam prevention)
        body_lower = (body or "").lower()
        INTENT_KEYWORDS = [
            # Greeting & conversational keywords
            'halo', 'hai', 'hi', 'hello', 'hallo', 'helo', 'hy', 'test', 'apa', 'dong', 'min', 'kak', 'gan', 'sis', 'bro', 'om',
            # Transaction keywords
            'beli', 'harga', 'stok', 'pesan', 'bayar', 'produk', 'menu', 'katalog', 
            'ongkir', 'alamat', 'lokasi', 'buka', 'tutup', 'jam', 'kirim', 'ready',
            'order', 'price'
        ]
        
        has_intent = any(k in body_lower for k in INTENT_KEYWORDS)
        
        # --- PING-PONG PROTECTION (BURST LIMIT) ---
        if not is_self and not is_owner:
            # Check burst limit: count BOT/AI messages to this customer in the last 1 minute
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            recent_bot_msgs = ChatLog.query.filter(
                ChatLog.toko_id == toko_id,
                ChatLog.customer_hp == nomor_murni,
                ChatLog.role.in_(['AI', 'BOT']),
                ChatLog.created_at >= one_minute_ago
            ).count()
            
            if recent_bot_msgs >= 3:
                logging.warning(f"⚠️ Ping-Pong Protection: Burst limit (3 msgs/min) for {nomor_murni}. Silencing bot.")
                return "OK (Silenced)", 200

        # is_owner defined above
        
        # --- IDENTITY GUARD BYPASS ---
        # If it's the bot itself, ONLY allow admin commands starting with /
        if is_self and not (body or "").startswith('/'):
            return "OK (Self-Ignored)", 200
        
        # --- OWNER COMMANDS (Product Management) ---
        if is_owner:
            from app.models import Menu
            message_body = (body or "").strip()
            
            # 1. LIST MENU (with IDs)
            if message_body.lower() == '/list_menu':
                menus = Menu.query.filter_by(toko_id=toko.id).all()
                if not menus:
                    reply = "Belum ada menu. Gunakan format:\n/tambah_menu [Nama] [Harga] [Stok]"
                else:
                    reply = "*Daftar Menu (ID untuk Hapus/Edit):*\n"
                    reply += "\n".join([f"🆔 {m.id} | {m.item} | Rp{m.harga:,} | Stok: {m.stok}" for m in menus])
                kirim_waha(chat_id, reply, session_id)
                return "OK", 200

            # 2. TAMBAH MENU
            # Format: /tambah_menu Nasi Goreng 15000 100
            if message_body.lower().startswith('/tambah_menu'):
                try:
                    parts = message_body.split()
                    if len(parts) < 3:
                        raise ValueError("Format salah")
                    
                    # Logic to handle Name with spaces:
                    # Last element is Stok? Check if 2 last are digits
                    stok = -1
                    price = 0
                    
                    if parts[-1].isdigit() and parts[-2].isdigit():
                        stok = int(parts.pop())
                        price = int(parts.pop())
                    elif parts[-1].isdigit():
                        price = int(parts.pop())
                    else:
                         raise ValueError("Harga harus angka")
                        
                    name = " ".join(parts[1:]) 
                    
                    new_menu = Menu(toko_id=toko.id, item=name, harga=price, stok=stok)
                    db.session.add(new_menu)
                    db.session.commit()
                    
                    # Audit Log
                    try:
                        from app.services.audit_service import log_audit
                        log_audit(toko.id, nomor_murni, 'ADD_MENU', 'MENU', new_menu.id, None, f"{name}|{price}|{stok}")
                    except: pass
                    
                    kirim_waha(chat_id, f"✅ Sukses tambah menu: {name} (Rp {price:,})", session_id)
                except:
                    kirim_waha(chat_id, "❌ Gagal. Format: `/tambah_menu [Nama] [Harga] [Stok]`", session_id)
                return "OK", 200

            # 3. HAPUS MENU
            if message_body.lower().startswith('/hapus_menu'):
                try:
                    parts = message_body.split()
                    if len(parts) < 2: raise ValueError("Missing ID")
                    
                    menu_id = int(parts[1]) # Force int
                    logging.info(f"Deleting Menu ID: {menu_id} for Toko {toko.id}")
                    
                    menu = Menu.query.filter_by(id=menu_id, toko_id=toko.id).first()
                    if menu:
                        old_meta = f"{menu.item}|{menu.harga}|{menu.stok}"
                        db.session.delete(menu)
                        db.session.commit()
                        
                        # Audit Log
                        try:
                            from app.services.audit_service import log_audit
                            log_audit(toko.id, nomor_murni, 'DELETE_MENU', 'MENU', menu_id, old_meta, None)
                        except: pass
                        
                        kirim_waha(chat_id, f"✅ Menu ID {menu_id} berhasil dihapus.", session_id)
                    else:
                        logging.warning(f"Menu ID {menu_id} not found.")
                        kirim_waha(chat_id, "❌ Menu ID tidak ditemukan.", session_id)
                except Exception as e:
                    logging.error(f"Hapus Menu Error: {e}")
                    kirim_waha(chat_id, "❌ Format salah. Contoh: `/hapus_menu 5`", session_id)
                return "OK", 200
        # --- END OWNER COMMANDS ---

        if not (has_intent or is_owner):
            logging.info(f"Filtered (No Intent): '{body}' from {nomor_murni}")

        # Call AI
        from app.services.broadcast import get_panic_mode
        if get_panic_mode():
            logging.info("Panic Mode Active: Silencing AI response")
            return "Panic Mode Active", 200

        logging.info(f"Calling Gemini for: '{body}'")
        try:
            ai_response = get_gemini_response(body, toko, customer)
            logging.info(f"Gemini Response: '{ai_response[:50] if ai_response else 'None'}...'")
        except Exception as e:
            logging.error(f"Gemini Execution Error: {e}", exc_info=True)
            
            # Track error for monitoring & alerts
            try:
                from app.services.error_monitoring import ErrorMonitor
                ErrorMonitor.log_error(
                    "GEMINI_FAILURE",
                    f"Failed for toko {toko.id}: {str(e)}",
                    severity="CRITICAL"
                )
            except:
                pass  # Don't let monitoring break the app
            
            # Enhanced fallback messages based on error type
            error_msg = str(e).lower()
            
            if "quota" in error_msg or "rate limit" in error_msg:
                ai_response = (
                    "Maaf kak, saat ini sistem sedang ramai sekali 😅\n"
                    "Bisa dicoba lagi sebentar lagi ya! 🙏"
                )
            elif "api key" in error_msg or "authentication" in error_msg:
                ai_response = (
                    "Mohon maaf ada gangguan teknis sebentar.\n"
                    "Tim kami sudah diberitahu. Terima kasih ya! 🙏"
                )
            else:
                ai_response = "Maaf, ada gangguan teknis sebentar ya kak 🙏"

        if ai_response:
            logging.info(f"Sending AI response to WAHA: {chat_id}")
            kirim_waha(chat_id, ai_response, session_id)
        else:
            logging.warning("Gemini returned empty response, skipping send.")

    # 6. MEDIA HANDLING (Bukti Transfer & CSV Upload)
    has_media = payload.get('hasMedia', False) or (data.get('media') is not None)
    if has_media:
        media = payload.get('media') or data.get('media')
        caption = (payload.get('body') or "").lower()
        mime_type = media.get('mimetype', '')
        
        # CSV Upload for Broadcast (Superadmin Only)
        if nomor_murni == Config.SUPER_ADMIN_WA and session_id == Config.MASTER_SESSION:
            # Customer already imported globally
            customer = Customer.query.filter_by(toko_id='MASTER', nomor_hp=nomor_murni).first()
            
            if customer and customer.flow_state == 'broadcast_awaiting_target':
                # Check if it's a CSV/text file
                if 'csv' in mime_type or 'text' in mime_type or media.get('filename', '').endswith('.csv'):
                    from app.feature_flags import FeatureFlags
                    
                    if not FeatureFlags.BROADCAST_CSV_UPLOAD:
                        kirim_waha(chat_id, "⚠️ Fitur CSV upload sedang dalam maintenance", session_id)
                        return "OK", 200
                    
                    kirim_waha(chat_id, "🔄 Memproses file CSV...", session_id)
                    
                    try:
                        from app.services.csv_handler import validate_csv_file
                        from app.services.waha import get_headers
                        
                        media_url = media.get('url')
                        if not media_url:
                            kirim_waha(chat_id, "❌ Gagal mendapatkan URL file", session_id)
                            return "OK", 200
                        
                        result = validate_csv_file(media_url, get_headers())
                        
                        if result['status'] == 'success':
                            targets = result['targets']
                            count = result['count']
                            
                            if count > FeatureFlags.BROADCAST_MAX_TARGETS:
                                kirim_waha(chat_id, f"❌ Terlalu banyak nomor: {count:,} (max {FeatureFlags.BROADCAST_MAX_TARGETS:,})", session_id)
                                return "OK", 200
                            
                            kirim_waha(chat_id, f"✅ CSV berhasil diproses!\n📊 {count:,} nomor valid ditemukan\n\n💬 Sekarang ketik PESAN BROADCAST:", session_id)
                            
                            customer.flow_state = 'broadcast_awaiting_message'
                            import json
                            customer.flow_data = json.dumps({'targets': targets, 'source': 'csv'})
                            db.session.commit()
                        else:
                            error_msg = result.get('message', 'Unknown error')
                            kirim_waha(chat_id, f"❌ Error parsing CSV: {error_msg}", session_id)
                        
                        return "OK", 200
                        
                    except Exception as e:
                        logging.error(f"CSV upload error: {e}")
                        kirim_waha(chat_id, f"❌ Gagal memproses CSV: {str(e)[:100]}", session_id)
                        return "OK", 200
        
        # Payment Proof Verification (Enhanced with Confidence Scoring)
        payment_keywords = ['bayar', 'transfer', 'lunas', 'struk', 'bukti', 'tf']
        is_payment = any(abc in caption for abc in payment_keywords)
        
        if is_payment:
            logging.info(f"📸 Payment proof detected from {nomor_murni}: {caption}")
            kirim_waha(chat_id, "🔍 Sedang memverifikasi bukti transfer...", session_id)
            
            try:
                # Download Media
                media_url = media.get('url')
                if not media_url:
                    kirim_waha(chat_id, "❌ Gagal mengunduh gambar. Mohon kirim ulang.", session_id)
                    return "OK", 200
                
                from app.services.waha import get_headers
                m_res = requests.get(media_url, headers=get_headers(), timeout=30)
                
                if m_res.status_code != 200:
                    logging.error(f"Failed to download media: {m_res.status_code}")
                    kirim_waha(chat_id, "❌ Gagal mengunduh gambar. Coba lagi.", session_id)
                    return "OK", 200
                
                mime = m_res.headers.get('Content-Type', 'image/jpeg')
                
                # Look up pending orders/transactions for this customer (contextual matching)
                expected_amount = None
                order_context = None
                pending_order = None
                
                # Order Matching: Find pending transaction for this customer
                try:
                    from app.services.order_service import find_pending_order
                    pending_order = find_pending_order(
                        toko_id=toko.id,
                        customer_hp=nomor_murni,
                        amount=None  # Will match any pending order first
                    )
                    
                    if pending_order:
                        expected_amount = pending_order.nominal
                        order_context = {
                            'order_id': pending_order.order_id,
                            'customer_phone': nomor_murni,
                            'created_at': pending_order.tanggal
                        }
                        logging.info(f"Found pending order {pending_order.order_id} for {nomor_murni}: Rp{expected_amount:,}")
                except Exception as order_err:
                    logging.warning(f"Order lookup error (non-fatal): {order_err}")
                
                from app.services.gemini import analisa_bukti_transfer
                
                logging.info(f"Calling enhanced payment verification for {nomor_murni}")
                analysis = analisa_bukti_transfer(
                    m_res.content, 
                    mime, 
                    expected_amount=expected_amount,
                    order_context=order_context,
                    toko=toko
                )
                
                # Log analysis result for debugging
                logging.info(f"Payment verification result: {json.dumps(analysis)}")
                
                # Extract results
                is_valid = analysis.get('is_valid', False)
                confidence = analysis.get('confidence_score', 0)
                detected_amount = analysis.get('detected_amount', 0)
                bank_name = analysis.get('bank_name', 'Unknown')
                match_status = analysis.get('match_status', 'NO_EXPECTED_AMOUNT')
                fraud_hints = analysis.get('fraud_hints', [])
                
                # Store verification result in ChatLog for audit trail
                try:
                    # ChatLog and db already imported globally
                    verification_log = ChatLog(
                        toko_id=toko.id,
                        customer_hp=customer.nomor_hp,
                        role='SYSTEM',
                        message=f"Payment Verification: {json.dumps(analysis)}"
                    )
                    db.session.add(verification_log)
                    db.session.commit()
                except Exception as log_err:
                    logging.error(f"Failed to log verification: {log_err}")
                
                # Confidence-based response flow
                if confidence >= 95 and is_valid:
                    # HIGH CONFIDENCE - Auto-approve
                    order_info = ""
                    if pending_order:
                        order_info = f"Order: #{pending_order.order_id}\n"
                    
                    reply = (
                        f"✅ *Pembayaran Terverifikasi!*\n\n"
                        f"{order_info}"
                        f"Bank: {bank_name}\n"
                        f"Nominal: Rp {detected_amount:,}\n"
                        f"Kepercayaan: {confidence}%\n\n"
                        f"Terima kasih! Pesanan Anda segera diproses. 🙏"
                    )
                    
                    # Auto-update order status to PAID
                    if pending_order and pending_order.order_id:
                        try:
                            from app.services.order_service import verify_order
                            verify_order(
                                order_id=pending_order.order_id,
                                verification_status='VERIFIED',
                                confidence_score=confidence,
                                detected_amount=detected_amount,
                                detected_bank=bank_name,
                                verified_by='AI',
                                fraud_hints=fraud_hints
                            )
                            logging.info(f"Order {pending_order.order_id} auto-verified by AI")
                        except Exception as verify_err:
                            logging.error(f"Failed to auto-verify order: {verify_err}")
                    
                elif confidence >= 70 and is_valid:
                    # MEDIUM CONFIDENCE - Notify both parties, flag for manual review
                    order_info = ""
                    if pending_order:
                        order_info = f"Order: #{pending_order.order_id}\n"
                    
                    reply = (
                        f"⚠️ *Bukti Transfer Diterima*\n\n"
                        f"{order_info}"
                        f"Bank: {bank_name}\n"
                        f"Nominal: Rp {detected_amount:,}\n"
                        f"Kepercayaan: {confidence}%\n\n"
                        f"Admin kami akan verifikasi manual segera. "
                        f"Mohon tunggu konfirmasi ya Kak! 🙏"
                    )
                    
                    # Flag order for manual review
                    if pending_order and pending_order.order_id:
                        try:
                            from app.services.order_service import verify_order
                            verify_order(
                                order_id=pending_order.order_id,
                                verification_status='MANUAL_REVIEW',
                                confidence_score=confidence,
                                detected_amount=detected_amount,
                                detected_bank=bank_name,
                                verified_by='AI',
                                fraud_hints=fraud_hints,
                                notes=f"Medium confidence ({confidence}%), needs manual review"
                            )
                            logging.info(f"Order {pending_order.order_id} flagged for manual review")
                        except Exception as verify_err:
                            logging.error(f"Failed to flag order for review: {verify_err}")
                    
                    # Notify merchant/owner
                    if toko.remote_token:
                        order_ref = f"\nOrder: #{pending_order.order_id}" if pending_order else ""
                        merchant_notif = (
                            f"🔔 *Bukti Transfer Perlu Review*\n\n"
                            f"Dari: {nomor_murni}{order_ref}\n"
                            f"Bank: {bank_name}\n"
                            f"Nominal: Rp {detected_amount:,}\n"
                            f"Confidence: {confidence}%\n"
                            f"Match Status: {match_status}\n\n"
                            f"⚠️ Mohon verifikasi manual via dashboard."
                        )
                        
                        try:
                            # Send to store owner's WhatsApp
                            owner_chat_id = f"{toko.remote_token}@c.us"
                            kirim_waha(owner_chat_id, merchant_notif, session_id)
                        except Exception as e:
                            logging.warning(f"Could not notify merchant {toko.remote_token}: {e}")
                    
                else:
                    # LOW CONFIDENCE - Request clearer photo
                    issues = ", ".join(fraud_hints[:3]) if fraud_hints else "unclear image"
                    
                    reply = (
                        f"⚠️ *Bukti Transfer Kurang Jelas*\n\n"
                        f"Kepercayaan: {confidence}%\n"
                        f"Masalah: {issues}\n\n"
                        f"Mohon kirim foto yang lebih jelas ya Kak:\n"
                        f"✓ Pastikan status transfer 'BERHASIL'\n"
                        f"✓ Nominal terlihat dengan jelas\n"
                        f"✓ Tidak blur/buram\n\n"
                        f"Terima kasih! 🙏"
                    )
                
                kirim_waha(chat_id, reply, session_id)
                
            except Exception as e:
                logging.error(f"Media analysis error: {e}")
                import traceback
                logging.error(traceback.format_exc())
                
                # Track error for monitoring
                try:
                    from app.services.error_monitoring import ErrorMonitor
                    ErrorMonitor.log_error(
                        "PAYMENT_VERIFICATION_FAILURE",
                        f"Failed for toko {toko.id}: {str(e)}",
                        severity="ERROR"
                    )
                except:
                    pass
                
                kirim_waha(
                    chat_id, 
                    "❌ Maaf, ada gangguan saat memverifikasi bukti transfer. "
                    "Mohon kirim ulang atau hubungi admin. 🙏", 
                    session_id
                )

    return "OK", 200
