import requests
import time
import base64
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import Config

WAHA_BASE_URL = Config.WAHA_BASE_URL
WAHA_API_KEY = Config.WAHA_API_KEY

def get_headers():
    h = {'Content-Type': 'application/json'}
    if WAHA_API_KEY:
        h['X-Api-Key'] = WAHA_API_KEY
    return h

def format_nomor(chat_id): 
    # WAHA Standard usually expects 12345@c.us or 12345@s.whatsapp.net
    if '@' not in str(chat_id):
        return f"{chat_id}@c.us"
    return chat_id

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def kirim_waha_raw(chat_id, message, session_name="default"):
    """
    Send text message via WAHA Plus
    Endpoint: /api/sendText
    """
    try:
        url = f"{WAHA_BASE_URL}/api/sendText"
        payload = {
            "session": session_name,
            "chatId": format_nomor(chat_id),
            "text": message
        }
        
        logging.info(f"Sending to WAHA: {chat_id}")
        response = requests.post(url, json=payload, headers=get_headers(), timeout=60)
        logging.info(f"WAHA Response: {response.status_code} {response.text}")
        return response
        
    except Exception as e:
        logging.error(f"Error sending WAHA: {e}")
        return None

def create_waha_session(session_name):
    # WAHA Plus NOWEB: Start session with Webhook Config
    try:
        # 1. Define Webhook Config
        webhook_url = Config.WAHA_WEBHOOK_URL
        # WAHA Plus Webhook Structure
        webhook_config = [
            {
                "url": webhook_url,
                "events": ["message", "session.status"] 
            }
        ]

        # 2. Check if exists
        url_all = f"{WAHA_BASE_URL}/api/sessions?all=true"
        res = requests.get(url_all, headers=get_headers())
        
        if res.status_code == 200:
            sessions = res.json()
            for s in sessions:
                if s.get('name') == session_name:
                    # Optional: Update Webhook if session exists (PATCH not always available/standard, so we assume OK or user must restart session)
                    # Ideally we would log "Session exists, ensuring webhook..." but for now we rely on initial creation or manual clean.
                    return True 
        
        # 3. Start Session with Webhook
        url_start = f"{WAHA_BASE_URL}/api/sessions"
        payload = {
            "name": session_name, 
            "config": {
                "webhooks": webhook_config
            }
        }
        
        logging.info(f"Starting WAHA Session '{session_name}' with webhook: {webhook_url}")
        res = requests.post(url_start, json=payload, headers=get_headers())
        if res.status_code in [200, 201]:
             logging.info("Session created successfully.")
             return True
        else:
             logging.error(f"Failed to create session: {res.text}")
             return False
             
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        return False

def get_waha_qr_retry(session_name, retries=5):
    # Get QR image
    url = f"{WAHA_BASE_URL}/api/{session_name}/auth/qr?format=image"
    for _ in range(retries):
        try:
            res = requests.get(url, headers=get_headers(), timeout=10)
            if res.status_code == 200 and 'image' in res.headers.get('content-type', ''):
                return res.content
            time.sleep(2)
        except Exception as e:
            logging.error(f"Error getting QR: {e}")
            time.sleep(2)
    return None

def get_waha_pairing_code(session_name, phone_number):
    try:
        import re
        phone = re.sub(r'\D', '', phone_number) 
        
        # SUMOPOD/WAHA variants to try
        urls = [
            f"{WAHA_BASE_URL}/api/sessions/{session_name}/auth/pairing-code",
            f"{WAHA_BASE_URL}/api/{session_name}/auth/pairing-code" # Variant 2
        ]
        
        for url in urls:
            try:
                logging.info(f"WAHA: Trying QR/Pairing Link: {url}")
                res = requests.get(url, params={"phoneNumber": phone}, headers=get_headers(), timeout=10)
                logging.info(f"WAHA: Res [{res.status_code}] for {url}")
                if res.status_code == 200:
                    return res.json().get('code')
            except: continue
            
    except Exception as e:
        logging.error(f"WAHA: Global Pairing Code Error: {e}")
    return None




def kirim_waha(chat_id, pesan, session_name="default"):
    return kirim_waha_raw(chat_id, pesan, session_name)

def kirim_waha_image_raw(chat_id, image_binary, caption, session_name="default"):
    """
    Send Image via WAHA Plus
    Endpoint: /api/sendImage
    """
    try:
        url = f"{WAHA_BASE_URL}/api/sendImage"
        # Base64 encode
        b64_img = "data:image/jpeg;base64," + base64.b64encode(image_binary).decode('utf-8')
        
        payload = {
            "session": session_name,
            "chatId": format_nomor(chat_id),
            "file": {
                "mimetype": "image/jpeg",
                "data": b64_img,
                "filename": "image.jpg"
            },
            "caption": caption
        }
        requests.post(url, json=payload, headers=get_headers(), timeout=20)
    except Exception as e:
        logging.error(f"Error sending image: {e}")

def kirim_waha_image_url(chat_id, url, caption, session_name="default"):
    try:
        # WAHA often supports URL in 'file'->'url'
        endpoint = f"{WAHA_BASE_URL}/api/sendImage"
        payload = {
            "session": session_name,
            "chatId": format_nomor(chat_id),
            "file": {
                "url": url,
                "mimetype": "image/jpeg",
                "filename": "image.jpg"
            },
            "caption": caption
        }
        requests.post(endpoint, json=payload, headers=get_headers(), timeout=20)
    except Exception as e:
        logging.error(f"Error sending image url: {e}")

def kirim_waha_buttons(chat_id, title, footer, buttons, session_name="default"):
    # Fallback to text for safety or use formatting
    msg = f"*{title}*\n{footer}\n\n"
    for b in buttons:
        msg += f"- {b[1]} (Ketik: {b[0]})\n"
    kirim_waha_raw(chat_id, msg, session_name)
