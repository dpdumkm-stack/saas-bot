import os
import sys
# Add 'bot' directory to path so we can import 'app'
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from app import create_app, db
from app.models import Toko, Subscription, ChatLog
from sqlalchemy import text

app = create_app()

print("--- DATABASE VERIFICATION ---")
print(f"URL Configured: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}") # Print host only for safety

with app.app_context():
    try:
        # 1. Test Connection
        db.session.execute(text('SELECT 1'))
        print("✅ Connection: SUCCESS")
        
        # 2. Check Tables
        toko_count = Toko.query.count()
        sub_count = Subscription.query.count()
        chat_count = ChatLog.query.count()
        
        print("\n--- DATA INTEGRITY CHECK ---")
        print(f"📊 Toko (Stores): {toko_count}")
        print(f"📊 Subscriptions: {sub_count}")
        print(f"📊 Chat Logs:     {chat_count}")
        
        # 3. Validation
        if toko_count >= 0:
            print("\n✅ Data Access: SUCCESS (Tables are readable)")
        else:
            print("\n❌ Data Access: FAILED (Err reading tables)")
            
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        print("Cek kembali password di .env!")
