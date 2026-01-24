import sys
import os

# Set PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), 'bot'))
sys.path.append(os.getcwd())

from app import create_app, db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('customer')]
    print("Columns in 'customer' table:")
    for col in columns:
        print(f"- {col}")
    
    # Check specific columns
    required = ['last_broadcast_msg', 'last_broadcast_at', 'broadcast_reply_count']
    missing = [r for r in required if r not in columns]
    if not missing:
        print("\n✨ ALL REQUIRED COLUMNS FOUND!")
    else:
        print(f"\n❌ MISSING COLUMNS: {missing}")
