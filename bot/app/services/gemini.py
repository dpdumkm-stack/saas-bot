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

def upload_knowledge_base(file_bytes, mime_type, file_name):
    """Uploads a file to Gemini for RAG"""
    try:
        if not client: return None
        
        logging.info(f"Uploading KB: {file_name} ({mime_type})")
        # Direct upload using files.upload
        # Note: google-genai client assumes file path usually, but let's check input.
        # If file_bytes is bytes, we might need a workaround or save to tmp.
        # For simplicity in this env, we assume we save it to tmp first or use a supported stream method if available.
        # The 'client.models.generate_content' supports inline data for images, but for large PDF docs we might need
        # to use the 'files' API.
        
        # NOTE: For 'google-genai' SDK (v1.0+), it supports uploading bytes directly? 
        # Actually standard practice for 'genai' is valid path.
        # Let's write to tmp.
        import os
        tmp_path = f"tmp_{file_name}"
        with open(tmp_path, 'wb') as f:
            f.write(file_bytes)
            
        # Upload
        # Using the specific client method for file upload if available, 
        # or fall back to standard 'google.generativeai' if 'genai.Client' is different.
        # Assuming 'genai.Client' from 'google-genai' package:
        
        # Check if we can use client.files.upload
        if hasattr(client, 'files'):
             up_file = client.files.upload(path=tmp_path)
             return up_file.name # returns 'files/xxxxx'
        
        # If that fails, maybe this client version is different. 
        # But let's assume standard google-genai structure.
        
        # Clean up
        if os.path.exists(tmp_path): os.remove(tmp_path)
        
        return None 
    except Exception as e:
        logging.error(f"Upload KB Error: {e}")
        return None


def get_history_text(toko_id, customer_hp):
    logs = ChatLog.query.filter_by(toko_id=toko_id, customer_hp=customer_hp).order_by(ChatLog.created_at.desc()).limit(6).all()
    return "\n".join([f"{'User' if l.role=='USER' else 'Bot'}: {l.message}" for l in reversed(logs)])

def tanya_gemini(pesan_user, toko, customer, image_data=None):
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
    if image_data:
        system_prompt += "\n[VISUAL] User mengirim gambar. Analisa gambar tersebut dan jawab pertanyaan user."
        
    full_prompt = f"{system_prompt}\n\nHistory:\n{history}\nUser: {pesan_user}\nBot:"

    try:
        if not client: return "Maaf, sistem AI belum dikonfigurasi."
            
        contents = []
        
        # 0. Add Image if available (General Vision)
        if image_data:
             # image_data = {'mime_type': '...', 'data': bytes}
             contents.append(image_data)
        
        # 1. Add Knowledge Base if exists
        if toko.knowledge_base_file_id:
             contents.append({"file": toko.knowledge_base_file_id})
             system_prompt += "\n[PENTING] Jawab berdasarkan dokumen di atas jika relevan."
             
        # 2. Add System Prompt & Text
        # Note: If mixing image and text, order matters in some versions, but list usually works.
        # But 'full_prompt' contains history.
        contents.append(full_prompt)

        res = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=contents
        )
        jawaban = res.text.strip()
        try:
            # Mark image message in logs check
            msg_log = f"[IMAGE] {pesan_user}" if image_data else pesan_user
            db.session.add(ChatLog(toko_id=toko.id, customer_hp=customer.nomor_hp, role='USER', message=msg_log))
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
