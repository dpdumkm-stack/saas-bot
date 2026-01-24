import requests
import time
import base64
import logging
import random
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
        from app.utils import normalize_phone_number
        clean = normalize_phone_number(chat_id)
        return f"{clean}@c.us"
    return chat_id

def mark_seen(chat_id, session_name="default"):
    """Mark chat as read (Double blue ticks)"""
    try:
        # Try different variations based on WAHA 2025 docs
        chat_id_formatted = format_nomor(chat_id)
        url = f"{WAHA_BASE_URL}/api/{session_name}/chats/{chat_id_formatted}/messages/read"
        res = requests.post(url, headers=get_headers(), timeout=10)
        # logging.info(f"Mark Seen: {res.status_code}")
    except Exception as e:
        logging.error(f"Error mark_seen: {e}")

def set_presence(chat_id, presence="composing", session_name="default"):
    """
    Set presence status (e.g., typing)
    """
    try:
        # Status typing in 2025 is 'typing' or 'composing'
        # To stop typing use 'paused'
        chat_id_formatted = format_nomor(chat_id)
        url = f"{WAHA_BASE_URL}/api/{session_name}/presence"
        
        val = presence
        if presence == "composing": val = "composing"
        if presence == "available": val = "paused"
        
        payload = {"chatId": chat_id_formatted, "presence": val}
        requests.post(url, json=payload, headers=get_headers(), timeout=10)
    except Exception as e:
        logging.error(f"Error set_presence: {e}")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
def kirim_waha_raw(chat_id, message, session_name="default"):
    """
    Send text message via WAHA Plus
    Endpoint: /api/sendText
    Wrapped with Circuit Breaker for reliability.
    """
    from app.services.circuit_breaker import get_breaker
    breaker = get_breaker("WAHA_API")
    
    def _execute_send():
        url = f"{WAHA_BASE_URL}/api/sendText"
        payload = {
            "session": session_name,
            "chatId": format_nomor(chat_id),
            "text": message
        }
        
        logging.info(f"Sending to WAHA: {chat_id}")
        response = requests.post(url, json=payload, headers=get_headers(), timeout=60)
        
        if response.status_code not in [200, 201]:
             logging.error(f"WAHA Error: {response.text}")
             from app.services.error_monitoring import ErrorMonitor
             ErrorMonitor.log_error("WAHA_DELIVERY_FAILURE", f"Status {response.status_code}: {response.text[:200]}", severity="ERROR")
             # Trigger circuit breaker and retry for any 4xx or 5xx error
             # This ensures the worker knows the message wasn't delivered
             raise Exception(f"WAHA Delivery Failure: {response.status_code} - {response.text}")
                 
        return response

    try:
        return breaker.call(_execute_send)
    except Exception as e:
        logging.error(f"Circuit Breaker blocked or failed WAHA call: {e}")
        return None

def kirim_waha(chat_id, text, session_name="default", add_delay=True, mark_as_seen=False, use_adaptive_delay=False):
    """
    Kirim pesan dengan anti-spam features:
    - Random typing delay (or adaptive based on text length)
    - Mark seen
    - Set presence (DISABLED - WAHA NOWEB doesn't support)
    
    Args:
        chat_id: WhatsApp chat ID
        text: Message to send
        session_name: WAHA session name
        add_delay: Enable typing delay
        mark_as_seen: Mark message as read before replying
        use_adaptive_delay: Use smart delay based on text length (more realistic)
    """
    try:
        if mark_as_seen:
            mark_seen(chat_id, session_name)
            time.sleep(random.uniform(0.5, 1.5))
        
        # NOTE: Presence indicator disabled - WAHA NOWEB returns 501 Not Implemented
        # Show "typing..." indicator (DISABLED)
        # set_presence(chat_id, "composing", session_name)
        
        # Typing delay (ACTIVE - This is the main anti-spam feature)
        if add_delay:
            if use_adaptive_delay:
                # Smart delay based on message length
                from app.services.humanizer import Humanizer
                delay_info = Humanizer.get_adaptive_delay(text)
                total_delay = delay_info['latency'] + delay_info['typing']
                # Cap max delay at 8 seconds (untuk avoid terlalu lama)
                delay = min(total_delay, 8.0)
            else:
                # Simple random delay (current default)
                delay = random.uniform(1.5, 3.0)
            
            time.sleep(delay)
        
        # Send actual message
        kirim_waha_raw(chat_id, text, session_name)
        
        # Stop typing indicator (DISABLED)
        # set_presence(chat_id, "available", session_name)
        
        return True
    except Exception as e:
        logging.error(f"Error kirim_waha: {e}")
        # Build robustness: try sending raw if fancy way fails 
        # But wrap it so it doesn't propagate the exception and hang the worker
        try:
            kirim_waha_raw(chat_id, text, session_name)
        except: pass
        return False

def check_session_status(session_name="default"):
    """Check session status from WAHA"""
    try:
        url = f"{WAHA_BASE_URL}/api/sessions/{session_name}"
        res = requests.get(url, headers=get_headers(), timeout=5)
        if res.status_code == 200:
            return res.json().get('status', 'UNKNOWN')
    except: pass
    return 'DISCONNECTED'

def check_exists(phone, session_name="default"):
    """
    Check if a phone number is registered on WhatsApp.
    Endpoint: /api/contacts/check-exists
    """
    try:
        url = f"{WAHA_BASE_URL}/api/contacts/check-exists"
        payload = {
            "session": session_name,
            "phone": phone
        }
        res = requests.post(url, json=payload, headers=get_headers(), timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            # WAHA 2025 structure: {"chatId": "...", "numberExists": true}
            return data.get('numberExists', False)
        
        logging.warning(f"Existence check failed for {phone} (Status {res.status_code})")
        return True # Fallback to True to avoid accidental skipping if API errors
    except Exception as e:
        logging.error(f"Error checking existence for {phone}: {e}")
        return True # Fallback to True for safety

def create_waha_session(session_name, pairing_method="qr"):
    # WAHA Plus NOWEB: Start session with Webhook Config
    try:
        # 1. Define Webhook Config
        # Normalize: ensure no double '/webhook' or '/routes/'
        webhook_url = Config.WAHA_WEBHOOK_URL
        
        webhook_config = [
            {
                "url": webhook_url,
                "events": ["message", "session.status"],
                "customHeaders": [
                    {
                        "name": "X-Header-2",
                        "value": Config.WEBHOOK_SECRET
                    }
                ]
            }
        ]

        # 2. Check if exists
        url_all = f"{WAHA_BASE_URL}/api/sessions?all=true"
        res = requests.get(url_all, headers=get_headers())
        
        if res.status_code == 200:
            sessions = res.json()
            for s in sessions:
                if s.get('name') == session_name:
                    status = s.get('status')
                    if status == 'FAILED':
                        logging.warning(f"Session '{session_name}' is FAILED. Deleting and recreating...")
                        requests.delete(f"{WAHA_BASE_URL}/api/sessions/{session_name}", headers=get_headers())
                        time.sleep(1)
                        break # Go to create logic
                    elif status == 'STOPPED':
                        logging.info(f"Session '{session_name}' is STOPPED. Starting...")
                        requests.post(f"{WAHA_BASE_URL}/api/sessions/{session_name}/start", headers=get_headers())
                        return True
                    else:
                        return True 
        
        # 3. Create Session with Webhook
        url_create = f"{WAHA_BASE_URL}/api/sessions"
        payload = {
            "name": session_name, 
            "config": {
                "webhooks": webhook_config
            }
        }
        
        # For pairing code method, use real browser name (required by WAHA)
        if pairing_method == "code":
            payload["config"]["metadata"] = "Chrome"  # Use real browser name
            logging.info(f"Creating Session '{session_name}' with pairing code support (Chrome device)...")
        else:
            logging.info(f"Creating Session '{session_name}' with QR code...")
        
        res = requests.post(url_create, json=payload, headers=get_headers())
        if res.status_code in [200, 201]:
             logging.info("Session created. Starting it...")
             # Usually POST /sessions automatically starts it in some config, but let's be explicit
             requests.post(f"{WAHA_BASE_URL}/api/sessions/{session_name}/start", headers=get_headers())
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

def request_pairing_code(session_name):
    """
    Request pairing code (8-digit) for WhatsApp authentication
    Returns the pairing code or None if failed
    """
    try:
        url = f"{WAHA_BASE_URL}/api/{session_name}/auth/request-code"
        logging.info(f"Requesting pairing code for session: {session_name}")
        
        res = requests.post(url, headers=get_headers(), timeout=10)
        if res.status_code in [200, 201]:
            data = res.json()
            # WAHA returns the code in response
            code = data.get('code', '')
            logging.info(f"✅ Pairing code generated: {code}")
            return {"status": "success", "code": code}
        else:
            logging.error(f"Failed to get pairing code: {res.status_code} - {res.text}")
            return {"status": "error", "message": res.text}
    except Exception as e:
        logging.error(f"Error requesting pairing code: {e}")
        return {"status": "error", "message": str(e)}

def get_session_status(session_name):
    """
    Get current session status
    Returns: STARTING, SCAN_QR, WORKING, FAILED, STOPPED, etc.
    """
    try:
        url = f"{WAHA_BASE_URL}/api/sessions/{session_name}"
        res = requests.get(url, headers=get_headers(), timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            status = data.get('status', 'UNKNOWN')
            return {"status": "success", "session_status": status}
        else:
            return {"status": "error", "message": "Session not found"}
    except Exception as e:
        logging.error(f"Error getting session status: {e}")
        return {"status": "error", "message": str(e)}

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

def configure_session_webhook(session_name: str) -> bool:
    """
    Automatically configure webhook for a session when it becomes WORKING
    Called from webhook.py when session.status event is received
    Returns True if successful, False otherwise
    """
    import time
    try:
        logging.info(f"🔧 Auto-configuring webhook for session: {session_name}")
        
        # Webhook configuration payload (webhooks plural array format per WAHA docs)
        config = {
            "config": {
                "webhooks": [
                    {
                        "url": Config.WAHA_WEBHOOK_URL,
                        "events": ["message", "session.status"],
                        "customHeaders": [
                            {
                                "name": "X-Header-2",
                                "value": Config.WEBHOOK_SECRET
                            }
                        ]
                    }
                ]
            }
        }
        
        url = f"{WAHA_BASE_URL}/api/sessions/{session_name}"
        
        # Send PATCH request to configure webhook
        response = requests.patch(
            url,
            headers=get_headers(),
            json=config,
            timeout=10
        )
        
        if response.status_code == 200:
            logging.info(f"✅ Webhook auto-configured successfully for {session_name}")
            
            # Verify configuration
            time.sleep(2)  # Wait for config to propagate
            verify_response = requests.get(url, headers=get_headers(), timeout=5)
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                webhooks = verify_data.get('config', {}).get('webhooks', [])
                if webhooks and 'message' in webhooks[0].get('events', []):
                    logging.info(f"✅ Verification passed: message event configured for {session_name}")
                    return True
                else:
                    logging.warning(f"⚠️  Webhook configured but message event not found for {session_name}")
        else:
            logging.error(f"❌ Failed to configure webhook for {session_name}: {response.status_code} - {response.text}")
        
        return False
        
    except Exception as e:
        logging.error(f"❌ Error auto-configuring webhook for {session_name}: {e}")
        return False

def stop_waha_session(session_name: str) -> bool:
    """
    Stop a WAHA session gracefully.
    """
    try:
        url = f"{WAHA_BASE_URL}/api/sessions/{session_name}/stop"
        response = requests.post(url, headers=get_headers(), timeout=10)
        
        if response.status_code == 200:
            logging.info(f"✅ Session {session_name} stopped successfully.")
            return True
        else:
            logging.warning(f"⚠️ Failed to stop session {session_name}: {response.text}")
            return False
    except Exception as e:
        logging.error(f"❌ Error stopping session {session_name}: {e}")
        return False

def delete_waha_session(session_name: str) -> bool:
    """
    Delete a WAHA session completely.
    """
    try:
        # SECURITY GUARD: Protect Master Session
        if session_name in [Config.MASTER_SESSION, 'default']:
            logging.error(f"⛔ SECURITY ALERT: Attempted to DELETE Master Session ({session_name}). Blocked by Global Safety Protocol.")
            return False

        url = f"{WAHA_BASE_URL}/api/sessions/{session_name}"
        response = requests.delete(url, headers=get_headers(), timeout=10)
        
        if response.status_code == 200:
            logging.info(f"✅ Session {session_name} deleted successfully.")
            return True
        else:
            logging.warning(f"⚠️ Failed to delete session {session_name}: {response.text}")
            return False
    except Exception as e:
        logging.error(f"❌ Error deleting session {session_name}: {e}")
        return False
