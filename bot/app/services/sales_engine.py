from app.extensions import db
from app.models import Customer, Toko, ChatLog
from app.services.waha import kirim_waha
from app.services.gemini import client
from datetime import datetime, timedelta
import logging

def check_and_send_followups(app):
    """
    Checks for idle customers and sends follow-up messages.
    Designed to run in a background thread with app context.
    """
    with app.app_context():
        try:
            # 1. Configuration
            # "Deep Sleep" logic from brief says >6 hours for Auto Follow-up
            # For testing/demo, we can set this lower, but let's stick to 6 hours for prod logic
            threshold = datetime.now() - timedelta(hours=6)
            
            # Batch size to prevent timeouts
            BATCH_SIZE = 5

            # 2. Query Candidates
            # - Has chatted before (last_interaction not None)
            # - Last chat was OLDER than threshold
            # - Has NOT been followed up yet for this session (status == 'NONE')
            # - Optional: Ignore if blocked or completed (assuming order_status resets on complete)
            
            candidates = Customer.query.filter(
                Customer.last_interaction < threshold,
                Customer.followup_status == 'NONE',
                Customer.last_interaction != None
            ).limit(BATCH_SIZE).all()

            if not candidates:
                return

            logging.info(f"SalesEngine: Found {len(candidates)} candidates for follow-up.")

            for cust in candidates:
                try:
                    toko = cust.toko
                    if not toko: continue

                    # 3. Generate Nudge
                    msg = generate_nudge(toko, cust)
                    
                    if msg:
                        # 4. Send Message
                        kirim_waha(cust.nomor_hp, msg, toko.session_name)
                        
                        # 5. Update State
                        cust.followup_status = 'SENT'
                        # Reset interaction time? No, keep it to measure gap.
                        # Status SENT prevents loop.
                        
                        # Log conversation
                        db.session.add(ChatLog(toko_id=toko.id, customer_hp=cust.nomor_hp, role='BOT', message=msg))
                        db.session.commit()
                        logging.info(f"SalesEngine: Sent nudge to {cust.nomor_hp}")
                    
                except Exception as e:
                    logging.error(f"SalesEngine Error {cust.nomor_hp}: {e}")
                    # Prevent infinite retry on error
                    cust.followup_status = 'ERROR'
                    db.session.commit()
                    
        except Exception as e:
            logging.error(f"SalesEngine Fatal: {e}")

def generate_nudge(toko, cust):
    # Priority 1: Pending Payment
    if cust.order_status == 'WAIT_TRANSFER':
        return f"Halo Kak! 👋 Tagihan Rp {cust.current_bill:,} belum dibayar nih. Stok menipis lho, mau diamankan sekarang?"
    
    # Priority 2: AI Contextual Nudge
    try:
        if not client: 
            return f"Halo Kak! Apa kabar? Ada yang bisa kami bantu lagi di {toko.nama}?"
        
        # Get context
        logs = ChatLog.query.filter_by(toko_id=toko.id, customer_hp=cust.nomor_hp)\
            .order_by(ChatLog.created_at.desc()).limit(3).all()
        history = "\n".join([f"{l.role}: {l.message}" for l in reversed(logs)])
        
        prompt = f"""
        Role: Sales Toko '{toko.nama}' (Kategori: {toko.kategori}).
        Context: Customer ini berhenti membalas chat sejak 6 jam lalu.
        History Chat Terakhir:
        {history}
        
        Tugas: Buat 1 kalimat sapaan ramah, pendek (MAX 15 kata), dan tidak terlihat putus asa.
        Tujuannya hanya untuk memancing mereka membalas.
        Output langsung kalimatnya.
        """
        
        res = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return res.text.strip().replace('"', '')
    except Exception as e:
        logging.error(f"Gemini Nudge Error: {e}")
        return f"Halo Kak! Masih berminat dengan menu kami?"
