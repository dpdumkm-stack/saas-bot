import requests
import time
import base64
import random
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import Config

WAHA_BASE_URL = Config.WAHA_BASE_URL

def format_nomor(chat_id): return chat_id.split('@')[0]
def format_chat_id(nomor): return f"{nomor}@c.us" if "@" not in str(nomor) else nomor

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def kirim_waha_raw(chat_id, pesan, session="default"):
    """Send WhatsApp message with retry logic"""
    target = f"{chat_id}@c.us" if "@" not in str(chat_id) else chat_id
    headers = {'X-Api-Key': Config.WAHA_API_KEY}
    try:
        response = requests.post(f"{WAHA_BASE_URL}/api/sendText", json={
            "session": session, "chatId": target, "text": pesan
        }, headers=headers, timeout=5)
        response.raise_for_status()
        return response
    except Exception as e:
        # logging.error(f"Failed to send WA message: {e}") # Optional log
        raise e

def create_waha_session(session_name):
    """
    Creates a new WAHA session using the minimal payload strategy.
    Relies on global environment variables (WAHA_WEBHOOK_URL) defined in docker-compose.yml.
    """
    try:
        url = f"{WAHA_BASE_URL}/api/sessions"
        headers = {'X-Api-Key': Config.WAHA_API_KEY}
        # Explicitly use minimal payload to force global config inheritance
        res = requests.post(url, json={"name": session_name}, headers=headers, timeout=10)
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"Error creating session: {e}")
        return False

def get_waha_qr_retry(session_name, retries=5):
    headers = {'X-Api-Key': Config.WAHA_API_KEY}
    try: requests.post(f"{WAHA_BASE_URL}/api/sessions/{session_name}/start", headers=headers, timeout=5)
    except: pass
    url = f"{WAHA_BASE_URL}/api/sessions/{session_name}/auth/qr?format=image"
    for _ in range(retries):
        try:
            time.sleep(3); res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200: return res.content
        except: pass
    return None

def kirim_waha(chat_id, pesan, session_name):
    import threading
    def task():
        target = format_chat_id(chat_id)
        headers = {'X-Api-Key': Config.WAHA_API_KEY}
        time.sleep(random.uniform(1.0, 2.5))
        try:
            requests.post(f"{WAHA_BASE_URL}/api/sendSeen", json={"session": session_name, "chatId": target}, headers=headers)
            requests.post(f"{WAHA_BASE_URL}/api/startTyping", json={"session": session_name, "chatId": target}, headers=headers)
            time.sleep(min(len(pesan)/25, 5))
            requests.post(f"{WAHA_BASE_URL}/api/stopTyping", json={"session": session_name, "chatId": target}, headers=headers)
            requests.post(f"{WAHA_BASE_URL}/api/sendText", json={"session": session_name, "chatId": target, "text": pesan}, headers=headers)
        except: pass
    threading.Thread(target=task).start()

def kirim_waha_image_raw(chat_id, image_binary, caption, session_name):
    try:
        b64 = base64.b64encode(image_binary).decode('utf-8')
        payload = {"session": session_name, "chatId": format_chat_id(chat_id), "file": {"url": f"data:image/png;base64,{b64}", "filename": "qr.png"}, "caption": caption}
        headers = {'X-Api-Key': Config.WAHA_API_KEY}
        requests.post(f"{WAHA_BASE_URL}/api/sendImage", json=payload, headers=headers)
    except: pass

def kirim_waha_image_url(chat_id, url, caption, session_name):
    try: 
        headers = {'X-Api-Key': Config.WAHA_API_KEY}
        requests.post(f"{WAHA_BASE_URL}/api/sendImage", json={"session": session_name, "chatId": format_chat_id(chat_id), "file": {"url": url}, "caption": caption}, headers=headers)
    except: pass

def kirim_waha_buttons(chat_id, title, footer, buttons, session_name):
    formatted = [{"reply": {"id": b[0], "title": b[1]}} for b in buttons]
    try: 
        headers = {'X-Api-Key': Config.WAHA_API_KEY}
        requests.post(f"{WAHA_BASE_URL}/api/sendButton", json={"session": session_name, "chatId": format_chat_id(chat_id), "reply_to": None, "title": title, "footer": footer, "buttons": formatted}, headers=headers)
    except: pass
