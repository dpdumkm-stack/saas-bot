import time
import requests
import threading
import logging
import json
from app.config import Config

WAHA_BASE_URL = Config.WAHA_BASE_URL
ACTIVE_SESSION = Config.MASTER_SESSION
API_KEY = Config.WAHA_API_KEY

class WahaPoller:
    def __init__(self, app):
        self.app = app
        self.last_message_id = None
        self.is_running = False
        self.processed_ids = set()

    def start(self):
        if self.is_running: return
        self.is_running = True
        threading.Thread(target=self._poll_loop, daemon=True).start()
        logging.info("🚀 Polling Worker Started: Monitoring /api/sessions/default/messages")

    def _poll_loop(self):
        # Initial delay to let WAHA start
        time.sleep(5)
        
        headers = {'X-Api-Key': API_KEY}
        url = f"{WAHA_BASE_URL}/api/sessions/{ACTIVE_SESSION}/messages?limit=20"

        while self.is_running:
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    messages = response.json()
                    # Sort by timestamp/id if needed, but mostly they come generic
                    self._process_batch(messages)
                else:
                    # If 404 (Session stopped), just wait
                    pass
            except Exception as e:
                logging.error(f"Polling Error: {e}")
            
            time.sleep(1.5) # Poll every 1.5 seconds

    def _process_batch(self, messages):
        # If first run, just mark all current as processed to avoid processing old history
        if self.last_message_id is None:
            if messages:
                self.last_message_id = messages[0]['id'] # Assuming newest first? Waha usually returns newest first
                # Actually, best to just track all current IDs
                for m in messages: self.processed_ids.add(m['id'])
            else:
                self.last_message_id = "START"
            return

        new_messages = []
        for m in messages:
            if m['id'] in self.processed_ids: continue
            
            # Timestamp check (optional, but good)
            # if m['timestamp'] < ...
            
            new_messages.append(m)
            self.processed_ids.add(m['id'])
            
            # Keep set small
            if len(self.processed_ids) > 1000:
                self.processed_ids = set(list(self.processed_ids)[-500:])

        # Process from oldest to newest if they came in newest-first
        # Usually API returns newest first. So reverse to process correctly.
        for msg in reversed(new_messages):
            self._inject_to_webhook(msg)

    def _inject_to_webhook(self, msg_data):
        """Simulate a Webhook POST internally"""
        # Adapt format to match what webhook() expects
        # Webhook expects: { "event": "message", "payload": { ...message_data... } }
        
        # Check if fromMe
        if msg_data.get('fromMe'): return # Skip own messages here to match webhook usually

        payload = {
            "event": "message",
            "session": ACTIVE_SESSION,
            "payload": msg_data
        }
        
        # We need to run this inside App Context
        with self.app.app_context():
            # Import here to avoid circular
            from app.routes.webhook import webhook
            
            # Mock request object? 
            # Flask's `webhook()` function uses `request.json`. 
            # We can't easily call valid flask route functions without a request context.
            # BETTER APPROACH: Extract logic from webhook() or call it via test_client/requests?
            # Calling via requests is safer as it simulates real traffic.
            
            try:
                # Internal Loopback Call
                # requests.post(f"http://localhost:5000/webhook", json=payload)
                # But to avoid network overhead, let's use the logic directly.
                # Refactor webhook.py to have `process_webhook_payload(data)` function?
                # For now, loopback POST is Easiest and Safest implementation.
                requests.post("http://localhost:5000/webhook", json=payload, timeout=1)
                logging.info(f"📥 Polled Message Processed: {msg_data.get('body')}")
            except Exception as e:
                logging.error(f"Injection Error: {e}")

