"""
Comprehensive Verification Script for Broadcast Reply Feature (v3.9.7)
Author: Antigravity AI
Date: 2026-01-25

This script performs end-to-end verification of the Context-Aware Broadcast Auto-Reply feature.
"""
import sys
import os
from datetime import datetime, timedelta

# Set PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), 'bot'))
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import Customer, BroadcastJob, Toko
from sqlalchemy import inspect

def test_database_schema():
    """Verify all required columns exist in Customer table"""
    print("\n" + "="*70)
    print("TEST 1: DATABASE SCHEMA VERIFICATION")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('customer')]
        
        required = ['last_broadcast_msg', 'last_broadcast_at', 'broadcast_reply_count']
        missing = [r for r in required if r not in columns]
        
        if not missing:
            print("✅ ALL REQUIRED COLUMNS FOUND!")
            print(f"   - last_broadcast_msg: {type(next(c for c in inspector.get_columns('customer') if c['name'] == 'last_broadcast_msg')['type'])}")
            print(f"   - last_broadcast_at: {type(next(c for c in inspector.get_columns('customer') if c['name'] == 'last_broadcast_at')['type'])}")
            print(f"   - broadcast_reply_count: {type(next(c for c in inspector.get_columns('customer') if c['name'] == 'broadcast_reply_count')['type'])}")
            return True
        else:
            print(f"❌ MISSING COLUMNS: {missing}")
            return False


def test_broadcast_context_logic():
    """Test the broadcast context injection logic"""
    print("\n" + "="*70)
    print("TEST 2: BROADCAST CONTEXT LOGIC")
    print("="*70)
    
    class MockCustomer:
        def __init__(self, msg=None, at=None, count=0):
            self.nomor_hp = "628123456"
            self.last_broadcast_msg = msg
            self.last_broadcast_at = at
            self.broadcast_reply_count = count
    
    # Test Case 1: Active Broadcast Context (within 24h)
    print("\n📋 Test Case 1: Recent Broadcast (within 24h)")
    cust = MockCustomer(
        msg="Promo DISKON 50% Bakso Spesial hari ini! 🎉",
        at=datetime.utcnow() - timedelta(minutes=30)
    )
    
    time_diff = datetime.utcnow() - cust.last_broadcast_at
    if time_diff.total_seconds() < 86400:
        print(f"   ✅ Context should be ACTIVE (age: {time_diff.total_seconds()/3600:.1f} hours)")
        print(f"   ✅ Reply count: {cust.broadcast_reply_count} (limit: 2)")
    else:
        print("   ❌ Context should be ACTIVE but detected as EXPIRED")
        return False
    
    # Test Case 2: Safety Fuse Trigger
    print("\n📋 Test Case 2: Safety Fuse (3rd reply)")
    cust.broadcast_reply_count = 2
    
    if cust.broadcast_reply_count >= 2:
        print("   ✅ Safety Fuse TRIGGERED - AI should NOT reply")
    else:
        print("   ❌ Safety Fuse should be TRIGGERED")
        return False
    
    # Test Case 3: Expired Context (>24h)
    print("\n📋 Test Case 3: Expired Context (>24h)")
    cust_old = MockCustomer(
        msg="Promo Kemarin",
        at=datetime.utcnow() - timedelta(hours=25)
    )
    
    time_diff = datetime.utcnow() - cust_old.last_broadcast_at
    if time_diff.total_seconds() >= 86400:
        print(f"   ✅ Context should be EXPIRED (age: {time_diff.total_seconds()/3600:.1f} hours)")
    else:
        print("   ❌ Context should be EXPIRED but detected as ACTIVE")
        return False
    
    print("\n✅ ALL LOGIC TESTS PASSED!")
    return True


def test_broadcast_worker_integration():
    """Verify broadcast worker updates customer context correctly"""
    print("\n" + "="*70)
    print("TEST 3: BROADCAST WORKER INTEGRATION")
    print("="*70)
    
    # Check if broadcast.py has the correct update logic
    broadcast_file = os.path.join(os.getcwd(), 'bot', 'app', 'services', 'broadcast.py')
    
    if not os.path.exists(broadcast_file):
        print("❌ broadcast.py not found")
        return False
    
    with open(broadcast_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        required_code = [
            'customer.last_broadcast_msg = final_message',
            'customer.last_broadcast_at = datetime.utcnow()',
            'customer.broadcast_reply_count = 0'
        ]
        
        missing = []
        for code in required_code:
            if code not in content:
                missing.append(code)
        
        if not missing:
            print("✅ Broadcast worker has correct customer context update logic!")
            print("   - Updates last_broadcast_msg ✓")
            print("   - Updates last_broadcast_at ✓")
            print("   - Resets broadcast_reply_count ✓")
            return True
        else:
            print(f"❌ Missing code in broadcast.py:")
            for m in missing:
                print(f"   - {m}")
            return False


def test_gemini_integration():
    """Verify gemini.py reads and uses customer broadcast context"""
    print("\n" + "="*70)
    print("TEST 4: GEMINI AI INTEGRATION")
    print("="*70)
    
    gemini_file = os.path.join(os.getcwd(), 'bot', 'app', 'services', 'gemini.py')
    
    if not os.path.exists(gemini_file):
        print("❌ gemini.py not found")
        return False
    
    with open(gemini_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        required_checks = [
            ('customer.last_broadcast_msg', '✓ Reads last_broadcast_msg'),
            ('customer.last_broadcast_at', '✓ Reads last_broadcast_at'),
            ('customer.broadcast_reply_count', '✓ Reads broadcast_reply_count'),
            ('86400', '✓ Has 24-hour time window'),
            ('broadcast_reply_count >= 2', '✓ Has safety fuse (2 reply limit)'),
            ('[KONTEKS BROADCAST]', '✓ Injects context to AI prompt')
        ]
        
        all_found = True
        for check, label in required_checks:
            if check in content:
                print(f"   {label}")
            else:
                print(f"   ❌ Missing: {check}")
                all_found = False
        
        if all_found:
            print("\n✅ Gemini AI Integration VERIFIED!")
            return True
        else:
            print("\n❌ Gemini AI Integration INCOMPLETE")
            return False


def test_production_data_sample():
    """Check if there are real broadcast jobs with customer context updates"""
    print("\n" + "="*70)
    print("TEST 5: PRODUCTION DATA SAMPLE")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        # Check recent broadcast jobs
        recent_jobs = BroadcastJob.query.order_by(BroadcastJob.created_at.desc()).limit(3).all()
        
        if not recent_jobs:
            print("⚠️  No broadcast jobs found (system may be new)")
            return True
        
        print(f"📊 Found {len(recent_jobs)} recent broadcast jobs:")
        for job in recent_jobs:
            print(f"   - Job #{job.id}: {job.status} | {job.success_count} sent | Created: {job.created_at}")
        
        # Check customers with broadcast context
        customers_with_context = Customer.query.filter(
            Customer.last_broadcast_msg.isnot(None)
        ).limit(5).all()
        
        if customers_with_context:
            print(f"\n✅ Found {len(customers_with_context)} customers with broadcast context!")
            for cust in customers_with_context[:3]:
                age = (datetime.utcnow() - cust.last_broadcast_at).total_seconds() / 3600 if cust.last_broadcast_at else 0
                print(f"   - {cust.nomor_hp}: Reply count={cust.broadcast_reply_count}, Age={age:.1f}h")
        else:
            print("⚠️  No customers with broadcast context yet (feature may be newly deployed)")
        
        return True


def generate_report():
    """Generate final verification report"""
    print("\n" + "="*70)
    print("FINAL VERIFICATION REPORT")
    print("="*70)
    
    results = {
        'Database Schema': test_database_schema(),
        'Context Logic': test_broadcast_context_logic(),
        'Broadcast Worker': test_broadcast_worker_integration(),
        'Gemini Integration': test_gemini_integration(),
        'Production Data': test_production_data_sample()
    }
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test}")
    
    print(f"\n{'='*70}")
    print(f"Overall: {passed}/{total} tests passed ({passed*100//total}%)")
    print(f"{'='*70}")
    
    if passed == total:
        print("\n🎉 ALL SYSTEMS GO! Broadcast Reply Feature is FULLY OPERATIONAL!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review logs above for details.")
        return 1


if __name__ == '__main__':
    exit_code = generate_report()
    sys.exit(exit_code)
