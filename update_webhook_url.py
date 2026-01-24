import sys
import os
import requests
import json

# Setup minimal app context
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))
from app.config import Config

def update_webhook():
    session = Config.MASTER_SESSION
    base_url = Config.WAHA_BASE_URL
    api_key = Config.WAHA_API_KEY
    target_url = "https://saas-bot-643221888510.asia-southeast2.run.app/routes/webhook"
    
    headers = {
        'Content-Type': 'application/json',
    }
    if api_key: headers['X-Api-Key'] = api_key
    
    print(f"🔧 UPDATING WEBHOOK for Session: '{session}'")
    print(f"   Target URL: {target_url}")
    
    # 1. Update Config (PATCH)
    url = f"{base_url}/api/sessions/{session}"
    
    payload = {
        "config": {
            "webhookUrl": target_url
        }
    }
    
    try:
        res = requests.patch(url, headers=headers, json=payload, timeout=15)
        
        print("\n📥 Response:")
        print(f"   Status: {res.status_code}")
        
        if res.status_code == 200:
            print("   ✅ SUCCESS! Webhook URL updated.")
            print("   👉 Checking config again to confirm...")
            
            # Re-check
            res_check = requests.get(url, headers=headers)
            current_url = res_check.json().get('config', {}).get('webhookUrl')
            print(f"   🔍 Final URL in WAHA: {current_url}")
            
            if current_url == target_url:
                 print("   🎉 VERIFIED MATCH!")
            else:
                 print("   ⚠️ WARNING: Update returned success but config didn't change?")
        else:
            print(f"   ❌ FAILED: {res.text}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    update_webhook()
