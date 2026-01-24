"""
Database Migration: Add Subscription Cancellation Fields
Run this ONCE to add new columns for unsubscribe feature
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from app import create_app
from app.extensions import db

def migrate_subscription_fields():
    """Add new fields to subscription table for cancellation tracking"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Starting migration: Add subscription cancellation fields...")
        
        try:
            # Check if columns already exist
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='subscription' AND column_name='cancelled_at'
            """))
            
            if result.fetchone():
                print("⚠️ Columns already exist. Skipping migration.")
                return
            
            print("📝 Adding new columns to subscription table...")
            
            # Add new columns
            db.session.execute(db.text("""
                ALTER TABLE subscription 
                ADD COLUMN cancelled_at TIMESTAMP,
                ADD COLUMN cancellation_reason VARCHAR(500),
                ADD COLUMN grace_period_ends TIMESTAMP,
                ADD COLUMN active_at TIMESTAMP
            """))
            
            db.session.commit()
            
            print("✅ Migration successful!")
            print("   - Added: cancelled_at (TIMESTAMP)")
            print("   - Added: cancellation_reason (VARCHAR(500))")
            print("   - Added: grace_period_ends (TIMESTAMP)")
            print("   - Added: active_at (TIMESTAMP)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_subscription_fields()
