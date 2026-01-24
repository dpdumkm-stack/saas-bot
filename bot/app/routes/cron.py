from flask import Blueprint, jsonify, request
from app.services.subscription_manager import check_daily_expirations
from app.config import Config
from datetime import datetime, timedelta
import logging

cron_bp = Blueprint('cron', __name__)

@cron_bp.route('/daily_checks', methods=['GET', 'POST'])
def daily_checks():
    """
    Secure endpoint to trigger daily subscription checks.
    Access: GET /api/cron/daily_checks?key=SECRET
    Or Header: X-App-Cron-Secret: SECRET
    """
    # 1. Security Check
    secret = request.headers.get('X-App-Cron-Secret')
    if not secret:
        secret = request.args.get('key') # Support ?key= for backward compatibility/browser
        
    # Validation
    expected_secret = Config.CRON_SECRET if hasattr(Config, 'CRON_SECRET') else "RahasiaNegara123"
    
    if secret != expected_secret:
        logging.warning(f"⛔ Unauthorized Cron Access Attempt from {request.remote_addr}")
        return jsonify({"error": "Unauthorized", "message": "Invalid Cron Secret"}), 401
        
    # 2. Check Dry Run Flag
    dry_run = request.args.get('dry_run', 'false').lower() == 'true'
    
    try:
        logging.info(f"⏰ Starting Daily Cron Job (DryRun={dry_run})...")
        
        # 1. Check expiring subscriptions and send reminders
        results = check_daily_expirations(dry_run=dry_run)
        
        # 2. Cleanup expired grace periods
        from app.services.subscription_manager import cleanup_expired_grace_periods
        grace_results = cleanup_expired_grace_periods(dry_run=dry_run)
        
        # 3. FAST RESCUE: Check for stuck broadcast jobs
        from app.services.broadcast_manager import BroadcastManager
        rescued_count = BroadcastManager.rescue_stuck_jobs()
        
        # Merge results
        results['grace_cleanup'] = grace_results
        
        logging.info(f"✅ Daily Cron Finished. {results}")
        
        return jsonify({
            "status": "success",
            "message": "Daily check completed",
            "dry_run": dry_run,
            "results": results
        }), 200
        
    except Exception as e:
        logging.error(f"❌ Cron Job Failed: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@cron_bp.route('/heartbeat', methods=['GET'])
def heartbeat():
    """
    Lightweight endpoint to keep Cloud Run instance alive.
    Also checks if background workers are still running.
    """
    import threading
    active_threads = [t.name for t in threading.enumerate()]
    
    worker_health = {
        "BroadcastWorker": "BroadcastWorker" in active_threads,
        "SalesEngine": "SalesEngine" in active_threads,
        "Scheduler": "Scheduler" in active_threads
    }
    
    all_workers_alive = all(worker_health.values())

    # Ensure BroadcastManager is available for the return statement
    from app.services.broadcast_manager import BroadcastManager

    # SELF-HEALING: Restart dead workers
    if not all_workers_alive:
        from flask import current_app
        import time
        
        if not worker_health["BroadcastWorker"]:
            logging.warning("⚠️ BroadcastWorker DEAD. Restarting...")
            from app.services.broadcast import worker_broadcast
            # Pass the concrete app object, not the proxy
            real_app = current_app._get_current_object() 
            threading.Thread(target=worker_broadcast, args=(real_app,), name="BroadcastWorker", daemon=True).start()
            
        if not worker_health["SalesEngine"]:
            logging.warning("⚠️ SalesEngine DEAD. Restarting...")
            from app.services.sales_engine import worker_sales_engine
            real_app = current_app._get_current_object()
            threading.Thread(target=worker_sales_engine, args=(real_app,), name="SalesEngine", daemon=True).start()
            
    return jsonify({
        "status": "alive" if all_workers_alive else "recovering",
        "timestamp": datetime.now().isoformat(),
        "workers": worker_health,
        "rescued_jobs": BroadcastManager.rescue_stuck_jobs(), # Also rescue on heartbeat
        "threads": {
            "total": threading.active_count(),
            "list": active_threads
        }
    }), 200


