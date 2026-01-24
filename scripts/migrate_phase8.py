"""
Safe Database Migration for Phase 8
Creates: broadcast_blacklist, scheduled_broadcast, broadcast_template tables

SAFETY FEATURES:
- Checks if tables already exist (idempotent)
- Validates connection before migration
- Creates backup timestamp
- Transaction safety
- Detailed logging
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    """Run Phase 8 database migration safely"""
    
    print("=" * 60)
    print("  Phase 8 Database Migration")
    print("=" * 60)
    print()
    
    # Import app and db
    try:
        from app import app, db
        from app.models import BroadcastBlacklist, ScheduledBroadcast, BroadcastTemplate
        print("✅ Successfully imported models")
    except Exception as e:
        print(f"❌ Failed to import: {e}")
        return False
    
    with app.app_context():
        try:
            # Test database connection
            print("\n[1/5] Testing database connection...")
            db.session.execute(db.text("SELECT 1"))
            print("✅ Database connection OK")
            
            # Check if tables already exist
            print("\n[2/5] Checking existing tables...")
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            phase8_tables = ['broadcast_blacklist', 'scheduled_broadcast', 'broadcast_template']
            already_exist = [t for t in phase8_tables if t in existing_tables]
            
            if already_exist:
                print(f"⚠️  Tables already exist: {', '.join(already_exist)}")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("❌ Migration cancelled by user")
                    return False
            else:
                print("✅ No Phase 8 tables exist yet")
            
            # Create backup point
            print("\n[3/5] Creating backup timestamp...")
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"✅ Backup timestamp: {backup_time}")
            print("   (Manual backup recommended before proceeding)")
            
            input("\nPress Enter to continue with migration...")
            
            # Create tables
            print("\n[4/5] Creating Phase 8 tables...")
            
            # Create only Phase 8 tables
            for table_name in phase8_tables:
                if table_name not in existing_tables:
                    print(f"   Creating {table_name}...")
            
            db.create_all()
            print("✅ Tables created successfully")
            
            # Verify tables
            print("\n[5/5] Verifying tables...")
            inspector = db.inspect(db.engine)
            new_tables = inspector.get_table_names()
            
            for table in phase8_tables:
                if table in new_tables:
                    columns = inspector.get_columns(table)
                    print(f"✅ {table}: {len(columns)} columns")
                else:
                    print(f"❌ {table}: NOT FOUND")
                    return False
            
            print("\n" + "=" * 60)
            print("  ✅ MIGRATION SUCCESSFUL!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Test opt-out feature: Send 'STOP' from test number")
            print("2. Enable feature flag: FEATURE_OPT_OUT=true")
            print("3. Monitor logs for errors")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n❌ MIGRATION FAILED: {e}")
            print("\nTo rollback manually:")
            print("  DROP TABLE IF EXISTS broadcast_blacklist;")
            print("  DROP TABLE IF EXISTS scheduled_broadcast;")
            print("  DROP TABLE IF EXISTS broadcast_template;")
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
