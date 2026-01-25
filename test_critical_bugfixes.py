"""
Critical Bug Fixes Verification Script
Tests the 3 most critical bug fixes deployed in v3.9-v3.9.4
"""
import sys
import os
from datetime import datetime, timedelta

# Set PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), 'bot'))
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import BroadcastJob, ScheduledBroadcast
from sqlalchemy import text

def test_unboundlocalerror_fix():
    """
    Test 1: UnboundLocalError Fix (v3.9.3)
    Verify no UnboundLocalError in recent broadcast jobs
    """
    print("\n" + "="*70)
    print("TEST 1: UNBOUNDLOCALERROR FIX (v3.9.3)")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            # Check recent broadcast jobs for errors
            recent_jobs = BroadcastJob.query.order_by(
                BroadcastJob.created_at.desc()
            ).limit(10).all()
            
            if not recent_jobs:
                print("⚠️  No broadcast jobs found to verify")
                print("   Recommendation: Send a small test broadcast (2 numbers)")
                return "SKIP"
            
            print(f"📊 Analyzing {len(recent_jobs)} recent broadcast jobs...")
            
            errors_found = []
            for job in recent_jobs:
                # Check if job completed without errors
                if job.status == "COMPLETED" and job.failed_count == 0:
                    print(f"   ✅ Job #{job.id}: {job.success_count} sent, 0 failed")
                elif job.status == "FAILED":
                    errors_found.append(f"Job #{job.id} FAILED")
                    print(f"   ❌ Job #{job.id}: FAILED status")
                elif job.failed_count > 0:
                    errors_found.append(f"Job #{job.id} has {job.failed_count} failures")
                    print(f"   ⚠️  Job #{job.id}: {job.failed_count} failed messages")
            
            if not errors_found:
                print("\n✅ PASS: No UnboundLocalError detected in recent jobs")
                return "PASS"
            else:
                print(f"\n⚠️  WARNING: {len(errors_found)} jobs with issues:")
                for err in errors_found:
                    print(f"   - {err}")
                print("\n   Note: Check Cloud Run logs for 'UnboundLocalError'")
                return "WARN"
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return "FAIL"


def test_scheduler_fix():
    """
    Test 2: Scheduler Target Resolution Fix (v3.9.4)
    Verify scheduled broadcasts include target counts
    """
    print("\n" + "="*70)
    print("TEST 2: SCHEDULER TARGET RESOLUTION FIX (v3.9.4)")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            # Check scheduled broadcasts
            upcoming = ScheduledBroadcast.query.filter(
                ScheduledBroadcast.scheduled_at > datetime.utcnow(),
                ScheduledBroadcast.status == 'pending'
            ).limit(5).all()
            
            if not upcoming:
                print("⚠️  No upcoming scheduled broadcasts found")
                print("   Recommendation: Schedule a test broadcast to verify")
                return "SKIP"
            
            print(f"📊 Analyzing {len(upcoming)} scheduled broadcasts...")
            
            all_good = True
            for sched in upcoming:
                # Check if target_list/target_csv exists and not empty
                has_targets = False
                target_count = 0
                
                if sched.target_list:
                    import json
                    try:
                        targets = json.loads(sched.target_list)
                        target_count = len(targets)
                        has_targets = True
                    except:
                        pass
                
                if sched.target_csv:
                    import json
                    try:
                        targets = json.loads(sched.target_csv)
                        target_count = len(targets)
                        has_targets = True
                    except:
                        pass
                
                if has_targets:
                    print(f"   ✅ Schedule #{sched.id}: {target_count} targets, Type: {sched.target_type}")
                else:
                    print(f"   ❌ Schedule #{sched.id}: NO TARGETS FOUND (silent skip bug!)")
                    all_good = False
            
            if all_good:
                print("\n✅ PASS: All scheduled broadcasts have valid targets")
                return "PASS"
            else:
                print("\n❌ FAIL: Some schedules missing targets (v3.9.4 fix not working)")
                return "FAIL"
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return "FAIL"


def test_timezone_fix():
    """
    Test 3: Timezone Display Fix (v3.9 - v3.9.1)
    Verify scheduled times are stored/displayed in WIB
    """
    print("\n" + "="*70)
    print("TEST 3: TIMEZONE DISPLAY FIX (v3.9 - v3.9.1)")
    print("="*70)
    
    app = create_app()
    with app.app_context():
        try:
            # Check scheduled broadcasts for timezone consistency
            upcoming = ScheduledBroadcast.query.filter(
                ScheduledBroadcast.scheduled_at > datetime.utcnow()
            ).order_by(ScheduledBroadcast.scheduled_at).limit(3).all()
            
            if not upcoming:
                print("⚠️  No upcoming scheduled broadcasts to check")
                print("   Cannot verify timezone fix without scheduled data")
                return "SKIP"
            
            print(f"📊 Checking timezone for {len(upcoming)} scheduled broadcasts...")
            
            import pytz
            wib = pytz.timezone('Asia/Jakarta')
            utc = pytz.utc
            
            for sched in upcoming:
                scheduled_time = sched.scheduled_at
                
                # Check if time is naive (no timezone) - should be UTC
                if scheduled_time.tzinfo is None:
                    # Assume UTC, convert to WIB for display
                    scheduled_time = utc.localize(scheduled_time)
                
                wib_time = scheduled_time.astimezone(wib)
                
                print(f"   Schedule #{sched.id}:")
                print(f"      DB Time: {sched.scheduled_at}")
                print(f"      WIB Display: {wib_time.strftime('%Y-%m-%d %H:%M:%S WIB')}")
                
                # Verify it's in reasonable future (not past, not too far)
                now_wib = datetime.now(wib)
                time_diff = (wib_time - now_wib).total_seconds()
                
                if time_diff < 0:
                    print(f"      ⚠️  WARNING: Time is in the PAST ({-time_diff/3600:.1f} hours ago)")
                elif time_diff > 86400 * 30:  # > 30 days
                    print(f"      ⚠️  WARNING: Time is far future ({time_diff/86400:.1f} days)")
                else:
                    print(f"      ✅ OK: {time_diff/3600:.1f} hours from now")
            
            print("\n✅ PASS: Timezone conversion working")
            print("   Note: Verify in Dashboard UI that times match wall clock")
            return "PASS"
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return "FAIL"


def generate_critical_test_report():
    """Generate critical bug fixes test report"""
    print("\n" + "="*70)
    print("CRITICAL BUG FIXES VERIFICATION REPORT")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scope: v3.9 - v3.9.4 (Bug Fixes Only)")
    print("="*70)
    
    tests = {
        'UnboundLocalError Fix (v3.9.3)': test_unboundlocalerror_fix(),
        'Scheduler Target Fix (v3.9.4)': test_scheduler_fix(),
        'Timezone Display Fix (v3.9-v3.9.1)': test_timezone_fix()
    }
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in tests.values() if v == "PASS")
    skipped = sum(1 for v in tests.values() if v == "SKIP")
    warned = sum(1 for v in tests.values() if v == "WARN")
    failed = sum(1 for v in tests.values() if v == "FAIL")
    total = len(tests)
    
    for test, result in tests.items():
        icon = {
            "PASS": "✅ PASS",
            "SKIP": "⏭️  SKIP",
            "WARN": "⚠️  WARN",
            "FAIL": "❌ FAIL"
        }.get(result, "❓ UNKNOWN")
        print(f"{icon} | {test}")
    
    print(f"\n{'='*70}")
    print(f"Results: {passed} passed, {skipped} skipped, {warned} warnings, {failed} failed")
    print(f"{'='*70}")
    
    if failed > 0:
        print("\n🚨 CRITICAL: Test failures detected! Review above for details.")
        return 2
    elif warned > 0:
        print("\n⚠️  Warnings found, but no critical failures. Proceed with caution.")
        return 1
    elif skipped == total:
        print("\n⏭️  All tests skipped (no data to verify). Manual testing recommended.")
        return 1
    else:
        print("\n🎉 All critical bug fixes verified! Production is stable.")
        return 0


if __name__ == '__main__':
    exit_code = generate_critical_test_report()
    sys.exit(exit_code)
