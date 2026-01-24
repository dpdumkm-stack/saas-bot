import sys
import os
import requests
import json
import time

# Setup minimal app context
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))
from app.config import Config

# Correct URL explicitly for this fix
RIGHT_WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"
SECRET = Config.WEBHOOK_SECRET

def fix_waha():
    session = Config.MASTER_SESSION
    base_url = Config.WAHA_BASE_URL
    api_key = Config.WAHA_API_KEY
    
    headers = {'Content-Type': 'application/json'}
    if api_key: headers['X-Api-Key'] = api_key
    
    print(f"🔧 FIXING WAHA WEBHOOK for '{session}'")
    print(f"   Target URL: {RIGHT_WEBHOOK_URL}")
    
    # 1. STOP Session
    print(f"   1. Stopping session...")
    requests.post(f"{base_url}/api/sessions/{session}/stop", headers=headers)
    time.sleep(2)
    
    # 2. CREATE Session (Overwrite config)
    # Even if it exists, some versions allow updating config via POST if it matches name?
    # Or we might need to DELETE if this fails.
    print(f"   2. Attempting to update config via CREATE...")
    
    payload = {
        "name": session,
        "config": {
            "webhooks": [
                {
                    "url": RIGHT_WEBHOOK_URL,
                    "events": ["message", "session.status"],
                    "customHeaders": [{"name": "X-Header-2", "value": SECRET}]
                }
            ]
        }
    }
    
    res = requests.post(f"{base_url}/api/sessions", json=payload, headers=headers)
    print(f"      Status: {res.status_code}")
    print(f"      Response: {res.text}")
    
    # 3. START Session
    print(f"   3. Starting session...")
    start_res = requests.post(f"{base_url}/api/sessions/{session}/start", headers=headers)
    print(f"      Start Status: {start_res.status_code}")
    
    # 4. VERIFY
    time.sleep(3)
    print(f"   4. Verifying config...")
    res_check = requests.get(f"{base_url}/api/sessions/{session}", headers=headers)
    if res_check.status_code == 200:
        curr_config = res_check.json().get('config', {})
        # Check both styles
        url1 = curr_config.get('webhookUrl')
        url2 = "NOT FOUND"
        if curr_config.get('webhooks') and len(curr_config['webhooks']) > 0:
            url2 = curr_config['webhooks'][0].get('url')
            
        print(f"      Current WebhookUrl: {url1}")
        print(f"      Current Webhooks[0]: {url2}")
        
        if url1 == RIGHT_WEBHOOK_URL or url2 == RIGHT_WEBHOOK_URL:
            print("   ✅ SUCCESS! Configuration Updated.")
        else:
            print("   ❌ FAILED! Still old/empty config.")
            print("   ⚠️  If this failed, we might need to DELETE and Re-PAIR.")

if __name__ == "__main__":
    fix_waha()
