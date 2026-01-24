import os
import json
import sqlite3
import psycopg2
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if '?' in db_url:
            if 'sslmode' not in db_url:
                db_url += '&sslmode=require'
        else:
            db_url += '?sslmode=require'
        db_url = db_url.replace("postgres://", "postgresql://")
        return psycopg2.connect(db_url)
    else:
        db_path = os.path.join('instance', 'saas_umkm.db')
        return sqlite3.connect(db_path)

def investigate():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check WAHA Session Status
    print("--- WAHA SESSION STATUS ---")
    try:
        waha_url = os.environ.get('WAHA_BASE_URL', 'https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id')
        api_key = os.environ.get('WAHA_API_KEY', '')
        headers = {}
        if api_key: headers['X-Api-Key'] = api_key
        
        res = requests.get(f"{waha_url}/api/sessions?all=true", headers=headers, timeout=10)
        if res.status_code == 200:
            sessions = res.json()
            for s in sessions:
                name = s.get('name')
                status = s.get('status')
                print(f"Session: {name}, Status: {status}")
                if name == 'default' and status == 'FAILED':
                    # Get more details for the failed session
                    res_det = requests.get(f"{waha_url}/api/sessions/{name}", headers=headers, timeout=10)
                    if res_det.status_code == 200:
                        print(f"  Session Details: {json.dumps(res_det.json(), indent=2)}")
        else:
            print(f"Failed to get sessions: {res.status_code}")
    except Exception as e:
        print(f"Error checking WAHA: {e}")

    print("\n--- LATEST BROADCAST JOBS ---")
    try:
        # Check if it's Postgres or SQLite to adjust query if needed
        # For now use generic SQL
        cursor.execute("SELECT id, toko_id, status, processed_count, success_count, failed_count, updated_at FROM broadcast_job ORDER BY created_at DESC LIMIT 5")
        jobs = cursor.fetchall()
        for job in jobs:
            print(f"ID: {job[0]}, Toko: {job[1]}, Status: {job[2]}, Processed: {job[3]}, Success: {job[4]}, Failed: {job[5]}, Updated: {job[6]}")
            
            if job[2] in ['FAILED', 'PAUSED', 'PENDING']:
                # Get more details for failed/paused jobs
                cursor.execute("SELECT target_list, pesan FROM broadcast_job WHERE id = %s" if os.environ.get('DATABASE_URL') else "SELECT target_list, pesan FROM broadcast_job WHERE id = ?", (job[0],))
                row = cursor.fetchone()
                target_list_json = row[0]
                pesan = row[1]
                targets = json.loads(target_list_json)
                print(f"  Pesan: {pesan[:100]}...")
                print(f"  Total Targets: {len(targets)}")
                
                # Look for errors in targets
                errors = [t.get('error') for t in targets if t.get('error')]
                if errors:
                    print(f"  Sample Errors: {list(set(errors))[:3]}")
    except Exception as e:
        print(f"Error querying broadcast_job: {e}")

    print("\n--- ERROR COUNTS IN SYSTEM_CONFIG ---")
    try:
        cursor.execute("SELECT key, value FROM system_config WHERE key LIKE 'error_count_%'")
        configs = cursor.fetchall()
        for cfg in configs:
            print(f"{cfg[0]}: {cfg[1]}")
    except Exception as e:
        print(f"Error querying system_config: {e}")

    print("\n--- RECENT CHAT LOGS (AI RESPONSES) ---")
    try:
        cursor.execute("SELECT role, message, created_at FROM chat_log ORDER BY created_at DESC LIMIT 5")
        chats = cursor.fetchall()
        for chat in chats:
            print(f"[{chat[2]}] {chat[0]}: {chat[1][:100]}...")
    except Exception as e:
        print(f"Error querying chat_log: {e}")

    conn.close()

if __name__ == "__main__":
    investigate()
