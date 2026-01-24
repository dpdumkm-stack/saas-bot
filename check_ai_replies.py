import sys
import os
from sqlalchemy import text

# Setup minimal app context
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))
from app.extensions import db
from app import create_app
from app.models import ChatLog

app = create_app()

def check_ai_replies():
    with app.app_context():
        print("🔍 Checking Recent AI Interactions (Last 20)")
        print("===========================================")
        
        # Get last 20 messages
        logs = ChatLog.query.order_by(ChatLog.created_at.desc()).limit(20).all()
        
        if not logs:
            print("❌ No chat logs found!")
            return

        for log in logs:
            role_icon = "🤖" if log.role in ['AI', 'BOT'] else "👤"
            print(f"[{log.created_at.strftime('%H:%M:%S')}] {role_icon} {log.role} (to {log.customer_hp}): {log.message[:50]}...")

        # Stats
        print("\n📊 Summary (Last 24h)")
        
        sql = text("SELECT role, COUNT(*) FROM chat_log WHERE created_at > datetime('now', '-1 day') GROUP BY role")
        try:
             # Try SQLite syntax first (local)
             results = db.session.execute(sql).fetchall()
        except:
             # Postgres syntax if deployed/connected to prod DB
             sql = text("SELECT role, COUNT(*) FROM chat_log WHERE created_at > NOW() - INTERVAL '1 day' GROUP BY role")
             results = db.session.execute(sql).fetchall()

        for row in results:
            print(f"   - {row[0]}: {row[1]}")

if __name__ == "__main__":
    check_ai_replies()
