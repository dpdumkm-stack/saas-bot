import logging
from app.extensions import db
from app.models import Subscription, Toko
from app.services.waha import stop_waha_session, delete_waha_session

def expire_subscription(phone_number: str, hard_delete_session=False) -> bool:
    """
    Handle logic for expiring a store's subscription.
    Policy: Soft Freeze.
    1. Stop WAHA Session (Resource saving).
    2. Set Subscription Status = EXPIRED.
    3. Set Toko Status = INACTIVE.
    4. Keep Data in DB.
    
    If hard_delete_session is True, the session is DELETED from WAHA instead of STOPPED.
    """
    try:
        logging.info(f"❄️ Freezing subscription for: {phone_number}")
        
        # 1. Get Records
        sub = Subscription.query.filter_by(phone_number=phone_number).first()
        toko = Toko.query.get(phone_number)
        
        if not sub:
            logging.warning(f"⚠️ Subscription not found for {phone_number}")
            return False
            
        session_name = toko.session_name if toko else f"session_{phone_number}"
        
        # 2. Manage WAHA Session
        if hard_delete_session:
            logging.info(f"🗑️ Deleting session {session_name} from WAHA...")
            delete_waha_session(session_name)
        else:
            logging.info(f"🛑 Stopping session {session_name} in WAHA...")
            stop_waha_session(session_name)
            
        # 3. Update Database (Soft Freeze)
        sub.status = "EXPIRED"
        if toko:
            toko.status_active = False
            
        db.session.commit()
        logging.info(f"✅ Subscription Frozen for {phone_number}. Data preserved.")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error expiring subscription: {e}")
        db.session.rollback()
        return False


def permanently_delete_subscription(phone_number: str) -> bool:
    """
    NUCLEAR OPTION: Permanently delete ALL data for a store.
    1. Delete WAHA Session.
    2. Delete Transaction, ChatLog, Menu, Customer.
    3. Delete Toko.
    4. Delete Subscription.
    """
    try:
        from app.config import Config
        # SECURITY GUARD: Protect Super Admin
        if phone_number == Config.SUPER_ADMIN_WA:
            logging.error(f"⛔ SECURITY ALERT: Attempted to NUCLEAR DELETE Super Admin ({phone_number}). Blocked.")
            return False

        logging.warning(f"☢️ INITIATING HARD DELETE FOR: {phone_number}")
        
        # 1. Get Records
        sub = Subscription.query.filter_by(phone_number=phone_number).first()
        toko = Toko.query.get(phone_number)
        
        if not sub and not toko:
            logging.warning(f"⚠️ No records found for {phone_number} to delete.")
            return False

        # 2. Delete WAHA Session
        if toko and toko.session_name:
            logging.info(f"🗑️ Deleting WAHA Session: {toko.session_name}")
            delete_waha_session(toko.session_name)
        else:
             # Fallback if only subscription exists
             delete_waha_session(f"session_{phone_number}")

        # 3. Delete Database Records (Manual Cascade)
        if toko:
            # Delete children
            from app.models import Menu, Customer, ChatLog, Transaction, BroadcastJob
            
            logging.info("🗑️ Deleting related data (ChatLog, Transaction, Menu, Customer, BroadcastJob)...")
            ChatLog.query.filter_by(toko_id=toko.id).delete()
            Transaction.query.filter_by(toko_id=toko.id).delete()
            Menu.query.filter_by(toko_id=toko.id).delete()
            Customer.query.filter_by(toko_id=toko.id).delete()
            BroadcastJob.query.filter_by(toko_id=toko.id).delete()
            
            logging.info(f"🗑️ Deleting Toko record: {toko.id}")
            db.session.delete(toko)
            
        if sub:
            logging.info(f"🗑️ Deleting Subscription record: {sub.phone_number}")
            db.session.delete(sub)
            
        db.session.commit()
        logging.info(f"✅ NUCLEAR DELETE COMPLETE for {phone_number}.")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error performing hard delete: {e}")
        db.session.rollback()
        return False
        
def cancel_subscription_with_grace(phone_number: str, reason: str = None) -> dict:
    """
    Cancel subscription with 30-day grace period.
    User can still reactivate during this time.
    
    Returns dict with:
    - success: bool
    - grace_period_ends: datetime
    - message: str
    """
    from datetime import datetime, timedelta
    from app.services.waha import kirim_waha
    
    try:
        logging.info(f"🚫 Initiating cancellation with grace for: {phone_number}")
        
        # 1. Get Records
        sub = Subscription.query.filter_by(phone_number=phone_number).first()
        toko = Toko.query.get(phone_number)
        
        if not sub:
            return {"success": False, "message": "Subscription not found"}
            
        if sub.status == 'CANCELLED':
            return {"success": False, "message": "Already cancelled"}
            
        session_name = toko.session_name if toko else f"session_{phone_number}"
        
        # 2. Set Grace Period Policy
        is_trial = (sub.tier or "").upper() == "TRIAL"
        
        if is_trial:
            # Policy: 7-day retention for Trial, immediate freeze
            grace_ends = datetime.now() + timedelta(days=7)
        else:
            # Policy: 30-day retention for Paid
            grace_ends = datetime.now() + timedelta(days=30)
        
        # 3. Stop WAHA Session (Resource saving)
        logging.info(f"🛑 Stopping session {session_name}...")
        stop_waha_session(session_name)
        
        # 4. Update Database
        sub.status = "CANCELLED"
        sub.cancelled_at = datetime.now()
        sub.cancellation_reason = reason
        sub.grace_period_ends = grace_ends
        
        if toko:
            toko.status_active = False
            
        db.session.commit()
        
        # 5. Send Confirmation Message
        re_days = 7 if is_trial else 30
        msg = (
            f"✅ **Subscription Dibatalkan**\n\n"
            f"Data Anda akan disimpan sampai *{grace_ends.strftime('%d %b %Y')}* ({re_days} hari).\n"
            f"Anda bisa reaktivasi kapan saja sebelum tanggal tersebut dengan klik tombol di dashboard.\n\n"
            f"Terima kasih sudah menggunakan layanan kami. 🙏"
        )
        
        try:
            from app.config import Config
            # Notification to User
            kirim_waha(phone_number, msg, session_name=Config.MASTER_SESSION)
            
            # Notification to Admin (SUPER_ADMIN_WA)
            if Config.SUPER_ADMIN_WA:
                admin_msg = (
                    f"🚫 **NOTIF CHURN: PEMBATALAN**\n\n"
                    f"Toko: *{sub.name}*\n"
                    f"Nomor: {phone_number}\n"
                    f"Alasan: {reason or 'Tidak disebutkan'}\n"
                    f"Grace Period S/D: *{grace_ends.strftime('%d %b %Y')}*"
                )
                admin_phone = Config.SUPER_ADMIN_WA
                if not admin_phone.endswith("@c.us"): admin_phone = f"{admin_phone}@c.us"
                kirim_waha(admin_phone, admin_msg, session_name=Config.MASTER_SESSION)
                
        except Exception as e:
            logging.warning(f"Failed to send cancellation notifications: {e}")
        
        logging.info(f"✅ Cancellation successful with grace period until {grace_ends}")
        return {
            "success": True,
            "grace_period_ends": grace_ends,
            "message": "Cancelled successfully. 30-day grace period active."
        }
        
    except Exception as e:
        logging.error(f"❌ Error cancelling subscription: {e}")
        db.session.rollback()
        return {"success": False, "message": str(e)}


def reactivate_from_grace(phone_number: str) -> dict:
    """
    Reactivate a cancelled subscription during grace period.
    
    Returns dict with:
    - success: bool
    - message: str
    - new_expiry: datetime (if success)
    """
    from datetime import datetime, timedelta
    from app.services.waha import kirim_waha, create_waha_session
    
    try:
        logging.info(f"🔄 Attempting reactivation for: {phone_number}")
        
        # 1. Get Subscription
        sub = Subscription.query.filter_by(phone_number=phone_number).first()
        toko = Toko.query.get(phone_number)
        
        if not sub:
            return {"success": False, "message": "Subscription not found"}
            
        if sub.status != 'CANCELLED':
            return {"success": False, "message": "Subscription not cancelled"}
            
        # 2. Check Grace Period
        if not sub.grace_period_ends:
            return {"success": False, "message": "No grace period set"}
            
        if datetime.now() > sub.grace_period_ends:
            return {"success": False, "message": "Grace period expired. Please resubscribe."}
        
        # 3. Calculate New Expiry (extend from now based on tier)
        tier_days = {"TRIAL": 5, "STARTER": 30, "BUSINESS": 30, "PRO": 30}
        extension_days = tier_days.get(sub.tier, 30)
        new_expiry = datetime.now() + timedelta(days=extension_days)
        
        # 4. Restart WAHA Session
        session_name = toko.session_name if toko else f"session_{phone_number}"
        logging.info(f"🔄 Restarting session {session_name}...")
        
        # Session might already exist (stopped), so we don't create new
        # Just update status and let user reconnect
        
        # 5. Update Database
        sub.status = "ACTIVE"
        sub.expired_at = new_expiry
        sub.cancelled_at = None
        sub.cancellation_reason = None
        sub.grace_period_ends = None
        
        if toko:
            toko.status_active = True
            
        db.session.commit()
        
        # 6. Send Confirmation
        msg = (
            f"🎉 **SELAMAT DATANG KEMBALI!**\n\n"
            f"Subscription Anda berhasil direaktivasi.\n"
            f"Masa aktif baru sampai: *{new_expiry.strftime('%d %b %Y')}*.\n\n"
            f"Silakan hubungkan kembali WhatsApp Anda untuk aktivasi bot.\n"
            f"Ketik /scan untuk mendapat QR Code."
        )
        
        try:
            from app.config import Config
            kirim_waha(phone_number, msg, session_name=Config.MASTER_SESSION)
        except Exception as e:
            logging.warning(f"Failed to send reactivation msg: {e}")
        
        logging.info(f"✅ Reactivation successful. New expiry: {new_expiry}")
        return {
            "success": True,
            "new_expiry": new_expiry,
            "message": "Reactivated successfully!"
        }
        
    except Exception as e:
        logging.error(f"❌ Error reactivating subscription: {e}")
        db.session.rollback()
        return {"success": False, "message": str(e)}

def activate_subscription(order_id: str, duration_days=30) -> bool:
    """
    Activate a subscription after payment success.
    1. Update Subscription Status -> ACTIVE, Payment -> PAID.
    2. Update Toko Status -> ACTIVE.
    3. Update Expiry Date.
    4. Send Confirmation Message.
    """
    from datetime import datetime, timedelta
    from app.services.waha import kirim_waha
    from app.config import Config
    import uuid
    
    try:
        logging.info(f"💰 Processing Activation for Order: {order_id}")
        
        sub = Subscription.query.filter_by(order_id=order_id).first()
        if not sub:
            logging.error(f"Subscription not found for Order ID: {order_id}")
            return False
            
        # Prevent double activation
        if sub.payment_status == 'paid' and sub.status == 'ACTIVE':
            logging.info(f"Subscription {sub.phone_number} already active.")
            return True
            
        # 1. Update Subscription
        sub.payment_status = 'paid'
        sub.status = 'ACTIVE'
        sub.active_at = datetime.now()
        
        # Smart Expiry: If not expired, extend from existing expiry date
        if sub.expired_at and sub.expired_at > datetime.now():
            sub.expired_at = sub.expired_at + timedelta(days=duration_days)
        else:
            sub.expired_at = datetime.now() + timedelta(days=duration_days)
        sub.step = 0 # Reset registration step
        
        # 2. Update/Create Toko
        session_name = f"session_{sub.phone_number}"
        toko = Toko.query.get(sub.phone_number)
        
        if not toko:
            toko = Toko(
                id=sub.phone_number,
                nama=sub.name,
                admin_name=sub.admin_name,
                kategori=sub.category,
                session_name=session_name,
                remote_token=str(uuid.uuid4())[:8],
                status_active=True
            )
            db.session.add(toko)
        else:
            toko.session_name = session_name
            toko.status_active = True
            toko.nama = sub.name 
            # toko.admin_name = sub.admin_name # Optional sync
            
        db.session.commit()
        
        # Ensure session exists (Critical for TRX flow)
        from app.services.waha import create_waha_session
        try:
            create_waha_session(session_name, pairing_method='qr')
        except Exception as e:
            logging.error(f"Failed to create session on activation: {e}")
            
        # 3. Send Notification
        # Ensure we have the user's phone number formatted correctly
        target_phone = sub.phone_number
        if not target_phone.endswith("@c.us"):
             target_phone = f"{target_phone}@c.us"
             
        success_url = f"https://saas-bot-643221888510.asia-southeast2.run.app/success?order_id={order_id}"
        dashboard_url = "https://saas-bot-643221888510.asia-southeast2.run.app/dashboard/login"
        msg_success = (
            f"🎉 *PEMBAYARAN DITERIMA!*\n\n"
            f"Terima kasih Kak *{sub.name}*, akun {sub.tier} kakak sudah aktif!\n"
            f"Masa aktif berlaku sampai: *{sub.expired_at.strftime('%d %b %Y')}*.\n\n"
            f"📊 *Dashboard: SUDAH BISA DIAKSES*\n"
            f"Login sekarang untuk atur produk & settings:\n"
            f"👉 {dashboard_url}\n"
            f"PIN: *1234*\n\n"
            f"🤖 *Bot: BELUM AKTIF (Perlu 1 Langkah Lagi)*\n"
            f"Agar bot bisa balas pesan pelanggan otomatis, *SCAN QR* dulu:\n"
            f"👉 {success_url}\n\n"
            f"💡 *Tip:* Ketik */help* kapan saja untuk melihat daftar perintah bantuan (Status, Unreg, dll).\n"
            f"_Pastikan scan pakai HP yang mau dijadikan Bot WhatsApp ya!_"
        )
        
        # Send from MASTER_SESSION
        kirim_waha(target_phone, msg_success, session_name=Config.MASTER_SESSION)
        
        logging.info(f"✅ Auto-Activation Success for {sub.phone_number}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error activating subscription: {e}")
        db.session.rollback()
        return False

def cleanup_expired_grace_periods(dry_run=False) -> dict:
    """
    Permanently delete subscriptions whose grace period has ended.
    Should run daily via cron.
    """
    from datetime import datetime
    
    results = {"deleted_count": 0, "details": []}
    
    try:
        today = datetime.now()
        
        # Find all CANCELLED subscriptions with expired grace periods
        expired_grace = Subscription.query.filter(
            Subscription.status == 'CANCELLED',
            Subscription.grace_period_ends != None,
            Subscription.grace_period_ends < today
        ).all()
        
        logging.info(f"🗑️ Found {len(expired_grace)} expired grace periods to cleanup")
        
        for sub in expired_grace:
            if not dry_run:
                success = permanently_delete_subscription(sub.phone_number)
                if success:
                    results["deleted_count"] += 1
                    results["details"].append(f"DELETED: {sub.phone_number}")
            else:
                results["deleted_count"] += 1
                results["details"].append(f"[Dry Run] WOULD DELETE: {sub.phone_number}")
        
        return results
        
    except Exception as e:
        logging.error(f"❌ Error cleaning up grace periods: {e}")
        return {"deleted_count": 0, "details": [f"ERROR: {str(e)}"]}


def check_daily_expirations(dry_run=False) -> dict:
    """
    Daily Cron Job Logic:
    1. Check for Active subscriptions expiring in 7, 3, 1 days -> Send Reminder.
    2. Check for Active subscriptions that EXPIRED yesterday (or today) -> Freeze.
    
    Returns a summary dict or list of actions taken.
    """
    from datetime import datetime
    from app.services.waha import kirim_waha
    
    # Use system local time or UTC? Usually servers use UTC. 
    # But for "Daily" checks aligned with user time, ideally we use local.
    # We'll assume server time is reasonable proxy for now.
    today = datetime.now().date()
    
    results = {
        "reminders_sent": 0,
        "frozen_count": 0,
        "details": []
    }
    
    # 1. Get all ACTIVE subscriptions
    # We filter by status='ACTIVE' to ensure we don't spam expired users.
    active_subs = Subscription.query.filter_by(status='ACTIVE').all()
    
    logging.info(f"📅 Daily Cron: Checking {len(active_subs)} active subscriptions.")
    
    for sub in active_subs:
        if not sub.expired_at:
            continue
            
        expiry_date = sub.expired_at.date()
        days_left = (expiry_date - today).days
        is_trial = (sub.tier or "").upper() == "TRIAL"
        
        # Action Logic
        msg = None
        payment_link = None
        
        # Performance Highlight (Count handled messages)
        chat_count = 0
        try:
            from app.models import ChatLog
            chat_count = ChatLog.query.filter_by(toko_id=sub.phone_number).count()
        except: pass
        
        # Generate Payment Link for ANY active subscription nearing expiry
        if days_left <= 7:
            try:
                from app.services.payment import create_payment_link
                from app.config import Config
                
                # Determine tier and package info
                current_tier = (sub.tier or "STARTER").upper()
                if current_tier == "TRIAL": current_tier = "STARTER" # Suggest Starter for trial users
                
                package = Config.PRICING_PACKAGES.get(current_tier, Config.PRICING_PACKAGES["STARTER"])
                amount = package["price"]
                
                prefix = "UPGRADE" if is_trial else "RENEW"
                pay_order_id = f"{prefix}-{sub.phone_number}-{int(datetime.now().timestamp())}"
                
                details = {
                    'order_id': pay_order_id,
                    'amount': amount,
                    'customer_details': {'first_name': sub.name, 'phone': sub.phone_number},
                    'item_details': [{'id': current_tier, 'price': amount, 'quantity': 1, 'name': f"{'Upgrade ke' if is_trial else 'Perpanjang'} Paket {current_tier}"}]
                }
                payment_link = create_payment_link(details)
            except Exception as e:
                logging.warning(f"Failed to generate renewal link for {sub.phone_number}: {e}")
        
        if days_left <= 0:
            # EXPIRED!
            if not dry_run:
                # 1. Send final goodbye message BEFORE freezing (so it can still go out)
                if is_trial:
                    final_msg = (
                        "😢 *MASA TRIAL BERAKHIR*\n\n"
                        f"Halo Kak, masa percobaan gratis bot sudah selesai hari ini. Bot kakak sudah membantu melayani *{chat_count} chat* selama trial! 🚀\n\n"
                        "Yuk *UPGRADE* ke Full Version sekarang agar bot tetap aktif dan data tidak hilang.\n\n"
                        f"Klik link di bawah untuk bayar instan (QRIS/Bank):\n{payment_link if payment_link else 'Hubungi Admin'}\n\n"
                        "Bot akan langsung aktif otomatis setelah pembayaran sukses! 😊"
                    )
                else:
                    final_msg = (
                        "⚠️ *LAYANAN DIBEKUKAN*\n\n"
                        f"Masa aktif langganan Toko *{sub.name}* telah berakhir hari ini.\n"
                        f"Bulan lalu bot kami sudah melayani *{chat_count} pesan* untuk Kakak. 🤝\n\n"
                        "Segera perpanjang agar bot tetap aktif melayani pelanggan 24 jam:\n"
                        f"👉 {payment_link if payment_link else 'Hubungi Admin'}\n\n"
                        "_Bot akan langsung aktif otomatis setelah pembayaran sukses._"
                    )
                
                # Try to send message
                try:
                    # Use the sub's own session to send to itself
                    toko = Toko.query.get(sub.phone_number)
                    session_name = toko.session_name if toko else f"session_{sub.phone_number}"
                    kirim_waha(sub.phone_number, final_msg, session_name=session_name)
                except Exception as e:
                    logging.error(f"Failed to send expiration msg to {sub.phone_number}: {e}")

                # 2. Execute FREEZE
                expire_sub_success = expire_subscription(sub.phone_number)
                
                if expire_sub_success:
                    results["frozen_count"] += 1
                    results["details"].append(f"FROZEN: {sub.phone_number}")
            else:
                results["frozen_count"] += 1
                results["details"].append(f"[Dry Run] WOULD FREEZE: {sub.phone_number} (Days Left: {days_left})")
                
        elif days_left == 1:
            if is_trial:
                msg = (
                    "⏳ *BESOK TRIAL HABIS*\n\n"
                    f"Halo Kak, masa percobaan bot tinggal 1 hari lagi. Bot sudah menangani *{chat_count} pesan* untuk kakak! 😉\n\n"
                    "Jangan sampai layanan terputus ya. Yuk amankan slot kakak dengan upgrade sekarang:\n\n"
                    f"👉 {payment_link}\n\n"
                    "_Pilih paket favorit Kakak dan asisten akan tetap siaga 24 jam!_"
                )
                
                # Admin Alert for Churn Risk
                try:
                    from app.config import Config
                    if Config.SUPER_ADMIN_WA:
                        admin_alert = (
                            f"🔔 **RISIKO CHURN (TRIAL H-1)**\n\n"
                            f"Toko: *{sub.name}*\n"
                            f"Nomor: {sub.phone_number}\n"
                            f"Performa: *{chat_count} chat handled*\n"
                            f"Status: Belum upgrade."
                        )
                        admin_phone = Config.SUPER_ADMIN_WA
                        if not admin_phone.endswith("@c.us"): admin_phone = f"{admin_phone}@c.us"
                        kirim_waha(admin_phone, admin_alert, session_name=Config.MASTER_SESSION)
                except: pass
            else:
                msg = (
                    "⚠️ *PERINGATAN TERAKHIR*\n\n"
                    f"Layanan Bot Toko *{sub.name}* akan *NON-AKTIF BESOK*.\n"
                    f"Bulan ini asisten AI sudah membantu *{chat_count} chat* Kakak. Jangan sampai terputus ya!\n\n"
                    f"👉 Link Perpanjangan Instan:\n{payment_link}\n\n"
                    "_Tenang, sisa masa aktif Kakak tidak akan hangus (akumulatif)._"
                )
                
                # Admin Alert for High-Tier Risk
                if sub.tier in ['BUSINESS', 'PRO']:
                    try:
                        from app.config import Config
                        if Config.SUPER_ADMIN_WA:
                            admin_alert = (
                                f"💎 **VIP ALERT: RISIKO CHURN**\n\n"
                                f"Toko: *{sub.name}* ({sub.tier})\n"
                                f"Nomor: {sub.phone_number}\n"
                                f"Penggunaan: *{chat_count} chat handled*\n"
                                f"Status: Sisa 1 hari, belum bayar."
                            )
                            admin_phone = Config.SUPER_ADMIN_WA
                            if not admin_phone.endswith("@c.us"): admin_phone = f"{admin_phone}@c.us"
                            kirim_waha(admin_phone, admin_alert, session_name=Config.MASTER_SESSION)
                    except: pass
        elif days_left == 3:
            # Trial usually doesn't hit H-3 logic unless created manually with >3 days, but safe to handle.
            if is_trial:
                 msg = (
                    "👋 *Halo Kak!*\n\n"
                    "Gimana performa bot-nya? Semoga membantu jualan ya.\n"
                    "Sekedar info, masa trial sisa 3 hari lagi. Siapkan budget buat upgrade yuk! 😉"
                )
            else:
                msg = (
                    "🔔 *REMINDER PERPANJANGAN*\n\n"
                    f"Masa aktif Toko *{sub.name}* tersisa *3 hari* lagi.\n"
                    f"Bulan ini Wali AI sudah melayani *{chat_count} pelanggan* Kakak. 🚀\n\n"
                    f"Yuk perpanjang sekarang agar asisten tetap siaga:\n{payment_link}"
                )
        elif days_left == 7:
            if not is_trial:
                msg = (
                    "👋 *Halo Kak!*\n\n"
                    f"Sekedar mengingatkan, paket langganan Bot Toko *{sub.name}* tersisa *7 hari* lagi.\n"
                    f"Sejauh ini bulan ini Anda sudah dibantu *{chat_count} chat*. 😉\n\n"
                    "Yuk amankan slot untuk bulan depan sekarang:\n"
                    f"👉 {payment_link}\n\n"
                    "_P.S. Bayar sekarang tidak mengurangi sisa hari ya, otomatis nambah di akhir!_"
                )
            
        if msg:
            if not dry_run:
                try:
                    toko = Toko.query.get(sub.phone_number)
                    session_name = toko.session_name if toko else f"session_{sub.phone_number}"
                    
                    kirim_waha(sub.phone_number, msg, session_name=session_name)
                    results["reminders_sent"] += 1
                    results["details"].append(f"Reminder H-{days_left}: {sub.phone_number}")
                except Exception as e:
                    logging.error(f"Failed to send reminder to {sub.phone_number}: {e}")

            else:
                 results["reminders_sent"] += 1
                 results["details"].append(f"[Dry Run] WOULD SEND H-{days_left}: {sub.phone_number}")

    return results
