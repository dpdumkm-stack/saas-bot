# SUMOPOD Polling Worker (Temporary Workaround)
# Karena webhook tidak berfungsi, gunakan polling
import os
import time
import logging
import requests
from datetime import datetime

SUMOPOD_URL = os.getenv("SUMOPOD_URL", "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id")
SUMOPOD_API_KEY = os.getenv("SUMOPOD_API_KEY")
SESSION_NAME = "session_01kdw5dvr5119e6bdxay5bkfqn"
POLL_INTERVAL = 5  # seconds

logger = logging.getLogger(__name__)

class SumopodPoller:
    def __init__(self, app):
        self.app = app
        self.last_message_id = None
        self.headers = {
            "X-Api-Key": SUMOPOD_API_KEY
        }
    
    def poll_messages(self):
        """Poll for new messages"""
        try:
            # Get messages
            url = f"{SUMOPOD_URL}/api/{SESSION_NAME}/messages"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Poll failed: {response.status_code}")
                return
            
            messages = response.json()
           
            if not isinstance(messages, list):
                return
            
            # Process new messages
            for msg in messages:
                msg_id = msg.get("id")
                
                # Skip if already processed
                if msg_id == self.last_message_id:
                    break
                
                # Skip if from me
                if msg.get("fromMe"):
                    continue
                
                # Process message
                self.process_message(msg)
                
                # Update last ID
                if not self.last_message_id:
                    self.last_message_id = msg_id
                    
        except Exception as e:
            logger.error(f"Polling error: {e}")
    
    def process_message(self, msg):
        """Process a single message by forwarding to webhook endpoint"""
        try:
            # Transform to webhook format
            webhook_data = {
                "event": "message",
                "session": SESSION_NAME,
                "payload": msg
            }
            
            # Forward to internal webhook handler
            with self.app.app_context():
                from app.routes.webhook import handle_webhook_internal
                handle_webhook_internal(webhook_data)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def start(self):
        """Start polling loop"""
        logger.info(f"Starting SUMOPOD poller (interval: {POLL_INTERVAL}s)")
        
        while True:
            try:
                self.poll_messages()
                time.sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Poller error: {e}")
                time.sleep(POLL_INTERVAL)

def start_poller(app):
    """Start poller in background thread"""
    if not SUMOPOD_API_KEY:
        logger.warning("SUMOPOD_API_KEY not set, poller disabled")
        return
    
    poller = SumopodPoller(app)
    import threading
    thread = threading.Thread(target=poller.start, daemon=True)
    thread.start()
    logger.info("SUMOPOD poller thread started")
