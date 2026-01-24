from google import genai
from datetime import datetime
import json
import logging
from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import Config
from app.extensions import db
from app.models import ChatLog, SystemConfig
import re

def sanitize_input(text):
    """
    Remove common prompt injection patterns and excessive special characters.
    """
    if not text: return ""
    # Remove markers that might be used to prematurely close blocks or start new commands
    # e.g., 'SYSTEM:', 'AI:', 'User:', '---', '==='
    text = re.sub(r'(?i)(system|ai|user|admin|assistant):', '', text)
    # Limit length for prompt injection sanity
    return text[:1000].strip()

def get_client(toko=None):
    """Dynamic client factory supporting per-store discovery"""
    api_key = Config.GEMINI_API_KEY
    if toko:
        cfg = SystemConfig.query.get(f"gemini_api_key_{toko.id}")
        if cfg and cfg.value:
            api_key = cfg.value
    
    if not api_key:
        return None
        
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        logging.error(f"Gemini Init Error: {e}")
        return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def _generate_with_retry(client, model, full_prompt):
    """Internal helper to handle retries for Gemini API calls"""
    res = client.models.generate_content(
        model=model,
        contents=full_prompt
    )
    return res

def get_gemini_response(user_input, toko, customer):
    """
    Get response from Gemini AI with hybrid resilience (Retry + Humanized fallback)
    """
    try:
        current_client = get_client(toko)
        if not current_client: return "Maaf, sistem AI belum dikonfigurasi."
        
        # Get dynamic model
        model_cfg = SystemConfig.query.get(f"gemini_model_{toko.id}")
        target_model = model_cfg.value if model_cfg else "gemini-2.0-flash"
        
        logging.info(f"Gemini Request: {toko.nama} | Model: {target_model}")
        
        # 1. Build context and history
        # 1. Build context and history
        config = SystemConfig.query.get('gemini_prompt')
        base_prompt = config.value if config else "Anda adalah asisten toko WhatsApp."
        
        # Context Aware Broadcast & Safety Fuse (v3.9.7)
        broadcast_context = ""
        if customer.last_broadcast_msg and customer.last_broadcast_at:
            # Only consider context if within 24 hours
            time_diff = datetime.utcnow() - customer.last_broadcast_at
            if time_diff.total_seconds() < 86400: # 24 hours
                # SAFETY FUSE: Prevent bot-loop (Ping-Pong)
                if customer.broadcast_reply_count >= 2:
                    logging.warning(f"🛡️ Safety Fuse triggered for {customer.nomor_hp}. AI response blocked to prevent loop.")
                    return None # Return None to skip sending
                
                broadcast_context = f"\n\n[KONTEKS BROADCAST]:\nAnda baru saja mengirim pesan ini ke pelanggan: \"{customer.last_broadcast_msg}\"\nJika balasan pelanggan ambigu, prioritaskan pembahasan tentang pesan broadcast di atas. Namun tetap layani jika mereka bertanya produk lain."
                
                # Increment counter (will be committed after response generation)
                customer.broadcast_reply_count += 1
        
        context = f"""
        Nama Toko: {toko.nama}
        Kategori: {toko.kategori}
        Link Toko: {toko.link_toko if hasattr(toko, 'link_toko') else '-'}
        Token Owner: {toko.remote_token}
        Nama Anda (Admin): {toko.admin_name}
        
        Sistem Prompt:
        Anda adalah {toko.admin_name}, seorang admin manusia yang ramah di toko WhatsApp {toko.nama}.
        {base_prompt}
        {broadcast_context}
        
        Gaya Bicara Admin WhatsApp (PENTING):
        1. Gunakan bahasa manusia yang luwes, santai, dan solutif. Hindari gaya bicara robot atau template kaku.
        2. Sesekali gunakan singkatan manusia (misal: sdh, blm, sy, ok, kak, ready) agar tidak terlihat seperti AI.
        3. Panggil diri Anda sebagai '{toko.admin_name}' sesekali untuk membangun kedekatan (Contoh: "Sebentar ya Kak, {toko.admin_name} cek stoknya dulu...").
        4. Berikan variasi jawaban, jangan pernah menjawab dengan kalimat yang sama persis jika ditanya berulang kali.
        5. Gunakan emoji secara natural (😊, 🙏, 👍).
        6. **AI Awareness**: Jika lawan bicara terlihat seperti bot atau AI (misal: terus mengulang sapaan basa-basi), berikan respon penutup yang sopan (Contoh: "Ok Kak, saya standby di sini ya jika butuh bantuan lagi!") dan BERHENTI bertanya balik.
        7. **Command Awareness**: Jika user bertanya tentang cara berhenti, menghapus data, aktivasi ulang, atau perintah teknis lainnya, sarankan mereka secara halus untuk mengetik */help* untuk melihat menu pengaturan teknis. (Contoh: "Untuk berhenti berlangganan atau hapus data, Kakak bisa ketik /help ya untuk bantuan teknis.").

        Daftar Menu/Produk:
        {toko.format_menu()}
        """
        
        # RAG / Knowledge Base Injection
        if hasattr(toko, 'knowledge_base_file_id') and toko.knowledge_base_file_id:
             import os
             # Assuming 'bot/knowledge_base' directory
             kb_path = os.path.join(current_app.root_path, '..', 'knowledge_base', toko.knowledge_base_file_id)
             if os.path.exists(kb_path):
                 try:
                     with open(kb_path, 'r', encoding='utf-8') as f:
                         kb_content = f.read()
                         # Truncate if too long (approx 2000 chars to save context window)
                         if len(kb_content) > 5000: kb_content = kb_content[:5000] + "...(truncated)"
                         
                         context += f"\n\n[Knowledge Base / Informasi Tambahan Toko]:\n{kb_content}\nNote: Gunakan informasi ini untuk menjawab pertanyaan pelanggan jika relevan."
                 except Exception as e:
                     logging.error(f"RAG Error: {e}")

        # Fetch last 10 messages (User & Bot mixed)
        history_obj = ChatLog.query.filter_by(customer_hp=customer.nomor_hp, toko_id=toko.id).order_by(ChatLog.created_at.desc()).limit(10).all()
        history_text = ""
        # Reversed so oldest first
        for h in reversed(history_obj):
            role_label = "AI" if (h.role == 'BOT' or h.role == 'AI') else "User"
            history_text += f"{role_label}: {h.message}\n"

        # 0. Sanitize input
        clean_input = sanitize_input(user_input)
        
        full_prompt = f"{context}\n\nHistory Chat:\n{history_text}\n\nUser: {clean_input}\nAI:"

        # 2. Generate with Smart Retry
        res = _generate_with_retry(current_client, target_model, full_prompt)
        
        jawaban = res.text.strip()
        
        # 3. Log and save (2 separate rows: User Input & AI Response)
        try:
            # Save User Input
            user_log = ChatLog(
                toko_id=toko.id,
                customer_hp=customer.nomor_hp,
                role='USER',
                message=clean_input
            )
            db.session.add(user_log)
            
            # Save AI Response
            ai_log = ChatLog(
                toko_id=toko.id,
                customer_hp=customer.nomor_hp,
                role='AI', 
                message=jawaban
            )
            db.session.add(ai_log)
            
            db.session.commit()
        except Exception as db_err:
            logging.error(f"DB Log Error (Gemini): {db_err}")
            db.session.rollback()

        return jawaban

    except Exception as e:
        import traceback
        import random
        logging.error(f"Gemini AI Final Exhausted Error: {str(e)}")
        logging.error(traceback.format_exc())
        
        try:
            from app.services.error_monitoring import ErrorMonitor
            ErrorMonitor.log_error("GEMINI_CRITICAL_FAILURE", str(e), severity="CRITICAL")
        except: pass
        
        # RANDOMIZED HUMAN FALLBACK (The 'Undercover Admin' Strategy)
        FALLBACK_MESSAGES = [
            "Waduh Kak, maaf banget ya, barusan HP admin sempat macet/hang sebentar pas mau balas karena lagi lumayan ramai chat masuk. 🙏 Boleh minta tolong dikirim ulang pertanyaannya Kak? Biar langsung saya bantu cek. Makasih! 😊",
            "Maaf banget Kak, barusan chatnya agak error di sini pas mau ketik balasannya tadi. Sepertinya HP admin lagi lelah karena lagi handle banyak banget pesanan sekaligus. 😅 Boleh dikirim ulang chat terakhirnya Kak? Saya langsung bantu prioritaskan ya. 🙏",
            "Aduh Kak, maaf barusan HP admin sempat 'ngadat' sebentar pas mau balas pesan Kakak. 🙏 Maklum admin lagi balas banyak chat masuk sekaligus nih. 😊 Boleh minta tolong kirim ulang pesannya? Admin bantu jawab sekarang kak! ✨",
            "Maaf ya Kak, barusan jaringan di toko sempat naik turun pas admin mau kirim balasan, soalnya lagi rame banget yang chat masuk. 🙏 Boleh dikirim lagi pertanyaannya Kak? Supaya nggak terlewat sama admin. Makasih banyak! 😊",
            "Waduh, maaf Kak, HP admin barusan tiba-tiba agak lemot pas mau balas pesan Kakak. Sepertinya kaget karena lagi rame pesanan masuk nih. 😅 Bisa minta tolong kirim ulang chatnya kak? Biar saya jawab langsung sekarang. 🙏"
        ]
        
        return random.choice(FALLBACK_MESSAGES)

def analisa_bukti_transfer(file_bytes, mime, expected_amount=None, order_context=None, toko=None):
    """
    Advanced payment proof verification with multi-bank support.
    
    Args:
        file_bytes: Image bytes
        mime: MIME type
        expected_amount: Expected payment amount (int or None)
        order_context: Additional context like order_id, customer_name (dict or None)
        toko: Toko object for per-store API key
        
    Returns:
        dict with keys: is_valid, detected_amount, confidence_score, bank_name, 
                       transfer_date, sender_name, fraud_hints, match_status
    """
    try:
        current_client = get_client(toko)
        if not current_client: 
            return {
                'is_valid': False, 
                'confidence_score': 0,
                'detected_amount': 0,
                'fraud_hints': ['API client not configured']
            }
        
        # Build context-aware prompt with Indonesian banking knowledge
        prompt_parts = [
            "🏦 **INDONESIAN PAYMENT PROOF VERIFICATION**",
            "",
            "Analyze this payment screenshot/receipt. Extract ALL available information.",
            "",
            "**RECOGNIZED BANKS & E-WALLETS:**",
            "- Mobile Banking: BCA Mobile, Livin by Mandiri, BRImo, BNI Mobile, CIMB Niaga",
            "- E-Wallets: GoPay, OVO, Dana, ShopeePay, LinkAja, **QRIS (All Platforms)**",
            "- ATM Receipts: All major banks",
            "",
            "**REQUIRED FIELDS TO EXTRACT:**",
            "1. **Bank/Platform Name** (e.g., 'BCA', 'GoPay')",
            "2. **Transfer Amount** (in IDR, numerical only)",
            "3. **Transfer Status** (Must say 'BERHASIL', 'SUKSES', 'SUCCESS', or equivalent)",
            "4. **Transfer Date & Time** (if visible)",
            "5. **Sender Name** (if visible)",
            "6. **Recipient Name/Account** (if visible)",
            "",
        ]
        
        # Add expected amount context if provided
        if expected_amount:
            prompt_parts.extend([
                f"**EXPECTED AMOUNT**: Rp {expected_amount:,}",
                f"**VALIDATION**: Check if detected amount matches expected amount.",
                "",
            ])
        
        # Add order context if provided
        if order_context:
            prompt_parts.append(f"**ORDER CONTEXT**: {json.dumps(order_context)}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "**FRAUD DETECTION - CHECK FOR RED FLAGS:**",
            "- Screenshot looks edited/photoshopped",
            "- Status is 'GAGAL', 'PENDING', or 'DITOLAK'",
            "- Amount suspiciously low or high",
            "- Date is very old (>7 days)",
            "- Image is too blurry to read clearly",
            "",
            "**OUTPUT FORMAT (STRICT JSON ONLY, NO MARKDOWN):**",
            "{",
            '  "is_valid": boolean,',
            '  "confidence_score": 0-100,',
            '  "detected_amount": number,',
            '  "bank_name": "string",',
            '  "transfer_status": "string",',
            '  "transfer_date": "string or null",',
            '  "sender_name": "string or null",',
            '  "fraud_hints": ["list", "of", "concerns"],',
            '  "match_status": "EXACT_MATCH" | "MISMATCH" | "NO_EXPECTED_AMOUNT"',
            "}",
            "",
            "**CONFIDENCE SCORING GUIDE:**",
            "- 95-100: Perfect clarity, exact match, no red flags",
            "- 85-94: Clear image, amount matches, minor issues (old date)",
            "- 70-84: Readable but some uncertainty or small mismatch",
            "- 50-69: Blurry image or significant concerns",
            "- 0-49: Unreadable, fraudulent, or failed transfer",
        ])
        
        full_prompt = "\n".join(prompt_parts)
        
        # Call Gemini Vision API
        res = current_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                {"mime_type": mime, "data": file_bytes}, 
                {"text": full_prompt}
            ]
        )
        
        # Parse response
        response_text = res.text.strip()
        
        # Clean JSON markers
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(response_text)
        
        # Validate schema and add defaults
        validated_result = {
            'is_valid': result.get('is_valid', False),
            'confidence_score': result.get('confidence_score', 0),
            'detected_amount': result.get('detected_amount', 0),
            'bank_name': result.get('bank_name', 'Unknown'),
            'transfer_status': result.get('transfer_status', 'Unknown'),
            'transfer_date': result.get('transfer_date'),
            'sender_name': result.get('sender_name'),
            'fraud_hints': result.get('fraud_hints', []),
            'match_status': result.get('match_status', 'NO_EXPECTED_AMOUNT')
        }
        
        # Additional validation: if expected_amount was provided, verify match_status
        if expected_amount and validated_result['detected_amount'] > 0:
            if abs(validated_result['detected_amount'] - expected_amount) <= 100:
                validated_result['match_status'] = 'EXACT_MATCH'
            else:
                validated_result['match_status'] = 'MISMATCH'
                validated_result['fraud_hints'].append(
                    f"Amount mismatch: Expected Rp{expected_amount:,}, Got Rp{validated_result['detected_amount']:,}"
                )
        
        logging.info(f"Payment verification result: {validated_result}")
        return validated_result
        
    except json.JSONDecodeError as e:
        logging.error(f"Payment verification JSON parse error: {e}")
        logging.error(f"Raw response: {response_text[:500]}")
        return {
            'is_valid': False,
            'confidence_score': 0,
            'detected_amount': 0,
            'fraud_hints': ['Failed to parse AI response'],
            'match_status': 'ERROR'
        }
    except Exception as e:
        logging.error(f"Payment verification error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return {
            'is_valid': False,
            'confidence_score': 0,
            'detected_amount': 0,
            'fraud_hints': [str(e)[:100]],
            'match_status': 'ERROR'
        }
