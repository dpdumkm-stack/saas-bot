from google import genai
from datetime import datetime
import json
import logging
from app.config import Config
from app.extensions import db
from app.models import ChatLog

client = None
if Config.GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=Config.GEMINI_API_KEY)
    except Exception as e:
        logging.error(f"Gemini Init Error: {e}")

def get_history_text(toko_id, customer_hp):
    logs = ChatLog.query.filter_by(toko_id=toko_id, customer_hp=customer_hp).order_by(ChatLog.created_at.desc()).limit(6).all()
    return "\n".join([f"{'User' if l.role=='USER' else 'Bot'}: {l.message}" for l in reversed(logs)])

def tanya_gemini(pesan_user, toko, customer):
    today = datetime.now().strftime("%Y-%m-%d")
    if toko.last_reset != today:
        toko.status_buka = True
        toko.last_reset = today
        db.session.commit()
    
    if not toko.status_buka: return "Maaf, Toko Sedang TUTUP. 🙏"

    history = get_history_text(toko.id, customer.nomor_hp)
    menu_list = "\n".join([f"- {m.item} Rp {m.harga:,} {'(Ada)' if m.stok != 0 else '(HABIS)'}" for m in toko.menus])

    system_prompt = f"""
    Role: Kasir '{toko.nama}' ({toko.kategori}). Menu: {menu_list}
    Tugas: Jawab ramah. 
    Jika deal/pesan -> Akhiri: [ORDER_MASUK:TotalAngka]. (Contoh: [ORDER_MASUK:50000])
    Jika customer marah -> Akhiri: [HANDOFF].
    """
    full_prompt = f"{system_prompt}\n\nHistory:\n{history}\nUser: {pesan_user}\nBot:"

    try:
        if not client: return "Maaf, sistem AI belum dikonfigurasi."
            
        res = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=full_prompt
        )
        jawaban = res.text.strip()
        try:
            db.session.add(ChatLog(toko_id=toko.id, customer_hp=customer.nomor_hp, role='USER', message=pesan_user))
            db.session.add(ChatLog(toko_id=toko.id, customer_hp=customer.nomor_hp, role='BOT', message=jawaban))
            db.session.commit()
        except Exception as db_err:
            logging.error(f"Database error saving chat log: {db_err}")
            db.session.rollback()
        return jawaban
    except Exception as e:
        logging.error(f"Gemini AI Error for customer {customer.nomor_hp}: {e}")
        return "Maaf, AI sedang sibuk."

def analisa_bukti_transfer(file_bytes, mime, expected):
    prompt = f"Analisa BUKTI TRANSFER. Tagihan: {expected}. JSON Output: {{'is_valid':bool, 'detected':int, 'fraud_score':int}}"
    try:
        if not client: return {'is_valid': False, 'fraud_score': 100}
            
        res = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[{"mime_type": mime, "data": file_bytes}, {"text": prompt}]
        )
        return json.loads(res.text.strip().replace("```json","").replace("```",""))
    except Exception as e:
        logging.error(f"Payment verification error: {e}")
        return {'is_valid': False, 'fraud_score': 50}
