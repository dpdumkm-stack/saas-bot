"""
Post-Deployment Health Check Script for v3.9.7
Automated verification of deployed features
"""
import sys
import os
from datetime import datetime

# Set PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), 'bot'))
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import Customer, BroadcastJob, SystemConfig
from sqlalchemy import text

def test_database_connection():
    """Test 1: Database Connection"""
    print("\n" + "="*70)
    print("TEST 1: DATABASE CONNECTION")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            # Simple query to test connection
            result = db.session.execute(text("SELECT 1"))
            print("✅ Database connection: HEALTHY")
            return True
        except Exception as e:
            print(f"❌ Database connection: FAILED - {e}")
            return False


def test_broadcast_context_columns():
    """Test 2: Broadcast Context Columns (v3.9.7)"""
    print("\n" + "="*70)
    print("TEST 2: BROADCAST CONTEXT COLUMNS (v3.9.7)")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('customer')]
            
            required = ['last_broadcast_msg', 'last_broadcast_at', 'broadcast_reply_count']
            missing = [r for r in required if r not in columns]
            
            if not missing:
                print("✅ All broadcast context columns exist")
                return True
            else:
                print(f"❌ Missing columns: {missing}")
                return False
        except Exception as e:
            print(f"❌ Schema check failed: {e}")
            return False


def test_recent_broadcast_jobs():
    """Test 3: Recent Broadcast Jobs"""
    print("\n" + "="*70)
    print("TEST 3: RECENT BROADCAST JOBS")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            jobs = BroadcastJob.query.order_by(BroadcastJob.created_at.desc()).limit(5).all()
            
            if jobs:
                print(f"✅ Found {len(jobs)} recent broadcast jobs:")
                for job in jobs:
                    status_icon = "✅" if job.status == "COMPLETED" else "⏳" if job.status == "RUNNING" else "❌"
                    print(f"   {status_icon} Job #{job.id}: {job.status} | {job.success_count}/{job.processed_count} sent")
                
                # Check for errors in recent jobs
                failed_jobs = [j for j in jobs if j.failed_count > 0]
                if failed_jobs:
                    print(f"\n⚠️  {len(failed_jobs)} jobs have failures:")
                    for job in failed_jobs:
                        print(f"   - Job #{job.id}: {job.failed_count} failed messages")
                
                return True
            else:
                print("⚠️  No broadcast jobs found (system may be new)")
                return True
        except Exception as e:
            print(f"❌ Broadcast job check failed: {e}")
            return False


def test_system_config():
    """Test 4: System Configuration"""
    print("\n" + "="*70)
    print("TEST 4: SYSTEM CONFIGURATION")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            # Check critical configs
            configs_to_check = [
                'maintenance_mode',
                'panic_mode',
                'gemini_prompt'
            ]
            
            all_good = True
            for config_key in configs_to_check:
                cfg = SystemConfig.query.get(config_key)
                if cfg:
                    value = cfg.value[:50] if len(cfg.value) > 50 else cfg.value
                    print(f"   ✅ {config_key}: {value}")
                else:
                    print(f"   ⚠️  {config_key}: Not set")
                    if config_key in ['maintenance_mode', 'panic_mode']:
                        all_good = False
            
            return all_good
        except Exception as e:
            print(f"❌ Config check failed: {e}")
            return False


def test_phone_normalization():
    """Test 5: Phone Normalization (v3.9.6)"""
    print("\n" + "="*70)
    print("TEST 5: PHONE NORMALIZATION (v3.9.6)")
    print("="*70)
    
    try:
        from app.utils import normalize_phone_number
        
        test_cases = [
            ("08123456789", "628123456789"),
            ("+6281234567890", "6281234567890"),
            ("62812 3456 789", "628123456789"),
            ("081-234-5678", "62812345678"),
        ]
        
        all_passed = True
        for input_num, expected in test_cases:
            result = normalize_phone_number(input_num)
            if result == expected:
                print(f"   ✅ {input_num} → {result}")
            else:
                print(f"   ❌ {input_num} → {result} (expected {expected})")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ Phone normalization test failed: {e}")
        return False


def test_broadcast_workers_running():
    """Test 6: Background Workers Status"""
    print("\n" + "="*70)
    print("TEST 6: BACKGROUND WORKERS")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            # Check if there are any jobs in RUNNING status (indicates workers are active)
            running_jobs = BroadcastJob.query.filter_by(status='RUNNING').count()
            pending_jobs = BroadcastJob.query.filter_by(status='PENDING').count()
            
            print(f"   Running Jobs: {running_jobs}")
            print(f"   Pending Jobs: {pending_jobs}")
            
            if running_jobs > 0:
                print("   ✅ Broadcast worker is ACTIVE")
            elif pending_jobs > 0:
                print("   ⚠️  Pending jobs exist but no running jobs (worker may be idle)")
            else:
                print("   ℹ️  No active broadcast jobs (normal if no recent broadcasts)")
            
            return True
        except Exception as e:
            print(f"❌ Worker status check failed: {e}")
            return False


def generate_health_report():
    """Generate comprehensive health report"""
    print("\n" + "="*70)
    print("POST-DEPLOYMENT HEALTH CHECK REPORT")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Version: v3.9.7")
    print("="*70)
    
    tests = {
        'Database Connection': test_database_connection(),
        'Broadcast Context Columns': test_broadcast_context_columns(),
        'Recent Broadcast Jobs': test_recent_broadcast_jobs(),
        'System Configuration': test_system_config(),
        'Phone Normalization': test_phone_normalization(),
        'Background Workers': test_broadcast_workers_running()
    }
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in tests.values() if v)
    total = len(tests)
    
    for test, result in tests.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test}")
    
    print(f"\n{'='*70}")
    print(f"Overall: {passed}/{total} tests passed ({passed*100//total}%)")
    print(f"{'='*70}")
    
    if passed == total:
        print("\n🎉 ALL HEALTH CHECKS PASSED! Production is HEALTHY!")
        return 0
    elif passed >= total * 0.8:
        print("\n⚠️  Most tests passed, but some issues detected. Review above.")
        return 1
    else:
        print("\n🚨 CRITICAL: Multiple tests failed. Immediate action required!")
        return 2


if __name__ == '__main__':
    exit_code = generate_health_report()
    sys.exit(exit_code)
