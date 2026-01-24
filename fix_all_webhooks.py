import sys
import os
import requests
import json
import time

# Setup minimal app context
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))
from app.config import Config

TARGET_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"
SECRET = Config.WEBHOOK_SECRET

def fix_all_sessions():
    base_url = Config.WAHA_BASE_URL
    api_key = Config.WAHA_API_KEY
    headers = {'Content-Type': 'application/json'}
    if api_key: headers['X-Api-Key'] = api_key
    
    print(f"🔧 STARTING MASS WEBHOOK UPDATE")
    print(f"   Target URL: {TARGET_URL}")
    print(f"   Base URL: {base_url}")
    print("="*50)

    # 1. Get ALL Sessions
    try:
        res = requests.get(f"{base_url}/api/sessions?all=true", headers=headers, timeout=15)
        if res.status_code != 200:
            print(f"❌ Failed to fetch sessions: {res.text}")
            return
            
        sessions = res.json()
        print(f"📊 Found {len(sessions)} total sessions.")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for sess in sessions:
            name = sess.get('name')
            status = sess.get('status')
            
            # Check current config (if available in list)
            # Some WAHA versions don't return full config in list, so we might need to fetch individual
            # But let's check what we have or just force update active ones.
            
            # Skip if it's not a merchant session (optional check, but safer to do all)
            # if not name.startswith('session_') and name != 'default': continue
            
            print(f"\nScanning '{name}' ({status})...")
            
            # Fetch details to check URL
            try:
                d_res = requests.get(f"{base_url}/api/sessions/{name}", headers=headers, timeout=5)
                curr_config = d_res.json().get('config', {}) if d_res.status_code == 200 else {}
                
                # Check URLs
                url1 = curr_config.get('webhookUrl')
                url2 = None
                if curr_config.get('webhooks') and len(curr_config['webhooks']) > 0:
                    url2 = curr_config['webhooks'][0].get('url')
                
                if url1 == TARGET_URL or url2 == TARGET_URL:
                    print(f"   ✅ Already correct. Skipping.")
                    skip_count += 1
                    continue
                
                print(f"   ⚠️  Incorrect URL ({url1 or url2}). Fixing...")
                
                # --- APPLY FIX ---
                # Strategy: STOP -> CREATE (Updater) -> START
                # This is more robust than PATCH
                
                if status not in ['STOPPED', 'FAILED']:
                    print(f"   1. Stopping...")
                    requests.post(f"{base_url}/api/sessions/{name}/stop", headers=headers)
                    time.sleep(1)
                
                # Payload to overwrite config
                payload = {
                    "name": name,
                    "config": {
                        "webhooks": [
                            {
                                "url": TARGET_URL,
                                "events": ["message", "session.status"],
                                "customHeaders": [{"name": "X-Header-2", "value": SECRET}]
                            }
                        ]
                    }
                }
                
                print(f"   2. Updating Config...")
                up_res = requests.post(f"{base_url}/api/sessions", json=payload, headers=headers)
                
                # If 422, it means it exists (expected), but we wanted to update? 
                # Actually POST /sessions on existing might fail depending on version.
                # If POST fails with 422, maybe we need DELETE first? 
                # STARTING WITH DELETE IS RISKY (Unpairs?). 
                # Let's try PATCH first as per waha.py logic, if that fails, we fallback.
                
                if up_res.status_code == 422:
                    # Fallback to PATCH
                    print("      POST returned 422 (Exists). Trying PATCH...")
                    p_res = requests.patch(f"{base_url}/api/sessions/{name}", json=payload, headers=headers)
                    if p_res.status_code == 200:
                        print("      ✅ PATCH Success.")
                    else:
                        print(f"      ❌ PATCH Failed: {p_res.status_code}")
                        # Last Resort: If status was STOPPED, maybe we just START it and hope?
                        # No, we need to change config.
                        fail_count += 1
                        continue
                elif up_res.status_code not in [200, 201]:
                     print(f"      ❌ Update Failed: {up_res.status_code} - {up_res.text}")
                     fail_count += 1
                     continue
                
                print(f"   3. Starting...")
                requests.post(f"{base_url}/api/sessions/{name}/start", headers=headers)
                success_count += 1
                time.sleep(1) # Breath
                
            except Exception as e:
                print(f"   ❌ Error processing {name}: {e}")
                fail_count += 1
        
        print("\n" + "="*50)
        print(f"🏁 DONE.")
        print(f"   ✅ Fixed/Updated: {success_count}")
        print(f"   ⏩ Skipped (Already OK): {skip_count}")
        print(f"   ❌ Failed: {fail_count}")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    fix_all_sessions()
