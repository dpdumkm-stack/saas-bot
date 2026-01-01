import logging
from app.models import Subscription, Toko
from app.extensions import db
from app.services.waha import kirim_waha, create_waha_session
from app.services.payment import create_payment_link
from datetime import datetime, timedelta
import time
import uuid

def handle_registration(phone, body, chat_id, session_id):
    """Handle the multi-step registration flow via WhatsApp"""
    
    # 1. Check existing subscription
    sub = Subscription.query.filter_by(phone_number=phone).first()
    
    # 2. Command: /unreg
    if body.lower() == '/unreg':
        if sub:
            db.session.delete(sub)
            db.session.commit()
            kirim_waha(chat_id, "Data pendaftaran Anda telah dihapus. Ketik /daftar untuk mulai baru.", session_id)
        else:
            kirim_waha(chat_id, "Anda belum terdaftar.", session_id)
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
        sub.step = 3
        db.session.commit()
        
        msg = (
            f"Kategori {cat} terpilih.\n\n"
            f"Pilih Paket Langganan:\n"
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
                f"Terima kasih! 🙏\n\n"
                f"Pesanan: Paket {selected_tier}\n"
                f"Total: Rp {amount:,}\n\n"
                f"Silakan lakukan pembayaran melalui link ini:\n{pay_url}\n\n"
                f"Bot akan aktif otomatis setelah pembayaran lunas."
            )
            kirim_waha(chat_id, msg, session_id)
        else:
            kirim_waha(chat_id, "Gagal membuat link pembayaran. Hubungi Admin.", session_id)
        return

    # 7. Step 4: Reminder if they chat again
    if sub.step == 4 and sub.payment_status != 'paid':
        kirim_waha(chat_id, f"Menunggu pembayaran Anda.\nLink: {sub.payment_url}", session_id)
        return
