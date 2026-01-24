"""
Phase 8 Database Migration (Working Version)
Run from saas_bot root directory
"""
import os
import sys

# Set working directory to bot/
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'bot'))
sys.path.insert(0, os.getcwd())

print("=" * 60)
print("  Phase 8 Database Migration")
print("=" * 60)
print()

try:
    # Import using run.py pattern
    from run import app
    from app.extensions import db
    from app.models import BroadcastBlacklist, ScheduledBroadcast, BroadcastTemplate
    
    print("[OK] Imports successful")
    
    with app.app_context():
        # Test connection
        print("\n[1/4] Testing database connection...")
        db.session.execute(db.text('SELECT 1'))
        print("  [OK] Database connected")
        
        # Check existing tables
        print("\n[2/4] Checking existing tables...")
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        phase8_tables = ['broadcast_blacklist', 'scheduled_broadcast', 'broadcast_template']
        already_exist = [t for t in phase8_tables if t in existing_tables]
        
        if already_exist:
            print(f"  [WARN] Tables already exist: {', '.join(already_exist)}")
            print("  Migration will be skipped for existing tables")
        else:
            print("  [OK] No Phase 8 tables found - will create")
        
        # Create tables
        print("\n[3/4] Creating tables...")
        db.create_all()
        print("  [OK] db.create_all() executed")
        
        # Verify
        print("\n[4/4] Verifying tables...")
        new_tables = db.inspect(db.engine).get_table_names()
        all_good = True
        
        for table in phase8_tables:
            if table in new_tables:
                cols = len(inspector.get_columns(table))
                print(f"  [OK] {table} ({cols} columns)")
            else:
                print(f"  [FAIL] {table} NOT FOUND")
                all_good = False
        
        if all_good:
            print("\n" + "=" * 60)
            print("  SUCCESS - All Phase 8 tables ready!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Enable opt-out: gcloud run services update saas-bot --update-env-vars FEATURE_OPT_OUT=true")
            print("2. Test STOP command from WhatsApp")
            print()
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("  FAILED - Some tables not created")
            print("=" * 60)
            sys.exit(1)
            
except Exception as e:
    print(f"\n[ERROR] Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
