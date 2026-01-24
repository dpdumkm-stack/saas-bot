import logging
from app.models import Subscription, Toko
from app.extensions import db
from app.services.waha import kirim_waha, create_waha_session
from app.services.payment import create_payment_link
from app.services.subscription_manager import permanently_delete_subscription, cancel_subscription_with_grace
from datetime import datetime, timedelta
import time
import uuid
from app.config import Config

def handle_registration(phone, body, chat_id, session_id):
    """Handle the multi-step registration flow via WhatsApp"""
    
    # NORMALIZE PHONE NUMBER (08... -> 62...)
    original_phone = phone
    if phone.startswith('0'):
        phone = '62' + phone[1:]
    if phone.startswith('+'):
        phone = phone[1:]
    phone = phone.replace('-', '').replace(' ', '')
    
    # DEBUG LOGGING
    logging.info(f"🔍 REGISTRATION DEBUG: original='{original_phone}', normalized='{phone}', body='{body}'")
    
    # 1. Check existing subscription
    sub = Subscription.query.filter_by(phone_number=phone).first()
    
    # DEBUG LOGGING
    logging.info(f"🔍 DB QUERY RESULT: phone='{phone}', found={sub is not None}, sub_id={sub.id if sub else 'N/A'}")
    
    # 2. Command: /unreg or /scan
    cmd = body.lower().strip()
    if cmd == '/unreg':
        if sub:
            # SAFETY CHECK: Paid Users get Grace Period
            is_paid = (sub.payment_status == 'paid')
            is_trial = (sub.tier and sub.tier.upper() == 'TRIAL')
            
            if is_paid and not is_trial:
                # GRACEFUL CANCEL (30 Days Retention)
                # Note: cancel_subscription_with_grace sends its own confirmation via Master Session
                res = cancel_subscription_with_grace(phone)
                
                if not res['success']:
                    kirim_waha(chat_id, f"❌ Gagal memproses permintaan: {res['message']}", session_id)
            else:
                # HARD DELETE (Draft / Trial / Unpaid) - Nuclear Reset
                success = permanently_delete_subscription(phone)
                if success:
                    kirim_waha(chat_id, "Data pendaftaran & toko Anda telah dihapus permanen (Nuclear Reset). Ketik /daftar untuk mulai baru.", Config.MASTER_SESSION)
                else:
                    kirim_waha(chat_id, "❌ Terjadi kegagalan saat membersihkan data. Silakan hubungi admin.", session_id)
        else:
            kirim_waha(chat_id, "Anda belum terdaftar.", session_id)
        return
        
    if cmd == '/scan':
        if sub and sub.payment_status == 'paid':
            success_url = f"https://saas-bot-643221888510.asia-southeast2.run.app/success?order_id={sub.order_id}"
            msg = (
                f"Ini link **Scan QR Aktivasi** Kakak: 😊\n\n"
                f"👉 {success_url}\n\n"
                f"Buka link di atas melalui HP lain/laptop, lalu scan QR-nya pakai WhatsApp ini ya!"
            )
            kirim_waha(chat_id, msg, session_id)
        else:
            kirim_waha(chat_id, "Maaf, fitur ini hanya untuk akun yang sudah bayar dan butuh aktivasi. Ketik /daftar jika ingin mulai baru.", session_id)
        return

    # 3. Initiation: /daftar or REG_AUTO
    if not sub:
        new_sub = Subscription(
            phone_number=phone,
            status='DRAFT',
            step=1
        )
        db.session.add(new_sub)
        db.session.commit()
        kirim_waha(chat_id, "Halo! 😊 Selamat datang di Asisten UMKM.\n\nSiapa nama Toko/Bisnis Anda?", session_id)
        return

    # 4. Step 1: Capture Name
    if sub.step == 1:
        sub.name = body
        sub.step = 2
        db.session.commit()
        msg = (
            f"Salam kenal, {body}! 🤝\n\n"
            f"Kategori bisnisnya apa?\n"
            f"A. Makanan & Minuman 🍔\n"
            f"B. Jasa / Service 🛠️\n"
            f"C. Retail / Toko 🛍️\n\n"
            f"(Ketik A, B, atau C)"
        )
        kirim_waha(chat_id, msg, session_id)
        return

    # 5. Step 2: Capture Category
    if sub.step == 2:
        cats = {'A': 'Kuliner', 'B': 'Jasa', 'C': 'Retail'}
        cat = cats.get(body.upper())
        if not cat:
            kirim_waha(chat_id, "Mohon pilih A, B, atau C saja.", session_id)
            return
            
        sub.category = cat
        sub.step = 25 # Step 2.5: Ask Admin Name
        db.session.commit()
        
        msg = (
            f"Kategori {cat} terpilih. 👍\n\n"
            f"Sekarang, siapa **Nama Panggilan Admin** yang Kakak inginkan?\n"
            f"(Contoh: Sari, Mita, Aldi, atau nama Kakak sendiri).\n\n"
            f"Nama ini yang akan menyapa pelanggan Kakak nanti agar terasa lebih akrab. 😊"
        )
        kirim_waha(chat_id, msg, session_id)
        return

    # 5.5 Step 2.5: Capture Admin Name
    if sub.step == 25:
        sub.admin_name = body.strip()
        sub.step = 3
        db.session.commit()
        
        msg = (
            f"Siap! Nanti **{body}** yang akan bantu balas chat pelanggan Kakak. 😉\n\n"
            f"Terakhir, pilih Paket Langganan:\n"
            f"1. STARTER (Rp 99rb/bln)\n"
            f"2. BUSINESS (Rp 199rb/bln)\n"
            f"3. PRO (Rp 349rb/bln)\n\n"
            f"(Ketik 1, 2, atau 3)"
        )
        kirim_waha(chat_id, msg, session_id)
        return

    # 6. Step 3: Capture Tier & Generate Payment Link
    if sub.step == 3:
        tiers = {'1': 'STARTER', '2': 'BUSINESS', '3': 'PRO'}
        prices = {'STARTER': 99000, 'BUSINESS': 199000, 'PRO': 349000}
        
        selected_tier = tiers.get(body)
        if not selected_tier:
            kirim_waha(chat_id, "Mohon pilih 1, 2, atau 3.", session_id)
            return
            
        amount = prices[selected_tier]
        order_id = f"SUB-{phone}-{int(time.time())}"
        
        sub.tier = selected_tier
        sub.order_id = order_id
        sub.step = 4 # Waiting Payment
        
        # Create Midtrans Link
        details = {
            'order_id': order_id,
            'amount': amount,
            'customer_details': {'first_name': sub.name, 'phone': phone},
            'item_details': [{'id': selected_tier, 'price': amount, 'quantity': 1, 'name': f"Paket {selected_tier}"}]
        }
        
        pay_url = create_payment_link(details)
        if pay_url:
            sub.payment_url = pay_url
            db.session.commit()
            msg = (
                f"Terima kasih Kak! 🙏\n\n"
                f"Pesanan: Paket {selected_tier}\n"
                f"Total: Rp {amount:,}\n\n"
                f"Silakan bayar melalui link aman ini ya:\n{pay_url}\n\n"
                f"**Langkah Terakhir Setelah Bayar:**\n"
                f"Kakak akan diarahkan ke halaman **Aktivasi (Scan QR)**. Cukup scan sekali saja agar asisten otomatisnya langsung aktif dan siap bantu jualan. Gampang banget kok! 😊✨"
            )
            kirim_waha(chat_id, msg, session_id)
        else:
            kirim_waha(chat_id, "Gagal membuat link pembayaran. Hubungi Admin.", session_id)
        return

    # 7. Step 4: Reminder if they chat again
    if sub.step == 4 and sub.payment_status != 'paid':
        kirim_waha(chat_id, f"Menunggu pembayaran Anda.\nLink: {sub.payment_url}", session_id)
        return
