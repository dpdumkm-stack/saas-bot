import logging
import time
import json
import threading
from datetime import datetime, timedelta
from app.extensions import db
from app.models import ScheduledBroadcast, BroadcastJob, Subscription, Toko

def worker_scheduler(app):
    """
    Background worker that checks for scheduled broadcasts and recurring tasks.
    Runs every 60 seconds.
    """
    with app.app_context():
        logging.info("Scheduler Worker Started")
        while True:
            try:
                now = datetime.utcnow()
                
                # Use SKIP LOCKED and .first() to ensure only one worker picks up a specific job
                s_job = ScheduledBroadcast.query.filter(
                    ScheduledBroadcast.status == 'pending',
                    ScheduledBroadcast.scheduled_at <= now
                ).with_for_update(skip_locked=True).first()
                
                if s_job:
                    logging.info(f"Triggering scheduled job: {s_job.name}")
                    # ATOMIC CLAIM: Mark as executing immediately to prevent others from picking it up
                    # even if they have the row-lock released
                    s_job.status = 'executing'
                    db.session.commit()
                    
                    try:
                        # 1. Resolve Targets
                        target_list = []
                        if s_job.target_type == 'segment':
                            # Resolve dynamic segment
                            if s_job.target_segment == 'active':
                                subs = Subscription.query.filter_by(status='ACTIVE').all()
                                target_list = [{'phone': s.phone_number, 'name': s.name} for s in subs]
                            elif s_job.target_segment == 'trial':
                                subs = Subscription.query.filter_by(status='TRIAL').all()
                                target_list = [{'phone': s.phone_number, 'name': s.name} for s in subs]
                        elif s_job.target_type in ['list', 'paste', 'csv']:
                            # UNIFIED FIX: Everything resolved (List, Paste, CSV) is now saved in target_list
                            # Check target_list first, fallback to target_csv for legacy CSV schedules
                            raw_data = s_job.target_list or s_job.target_csv
                            if raw_data:
                                raw_targets = json.loads(raw_data)
                                # ROBUST FIX: Normalize data if it was saved as list of strings (Legacy/Buggy data)
                                target_list = []
                                for t in raw_targets:
                                    if isinstance(t, str):
                                        target_list.append({'phone': t, 'name': 'Unknown'})
                                    else:
                                        target_list.append(t)
                        
                        if target_list:
                            logging.info(f"🚀 Promoting SchedJob {s_job.id} to BroadcastJob (Targets: {len(target_list)})")
                            # 2. Create actual BroadcastJob
                            new_job = BroadcastJob(
                                toko_id=s_job.created_by or 'SUPERADMIN',
                                pesan=s_job.message,
                                target_list=json.dumps(target_list),
                                status='PENDING'
                            )
                            db.session.add(new_job)
                        else:
                            logging.warning(f"⚠️ SchedJob {s_job.id} skipped - Resolved target_list is EMPTY (type={s_job.target_type})")
                            # Optional: mark as failed instead of executed? 
                            # Let's mark as executed to stop the loop but log clearly.

                        # 3. Handle Recurrence Logic
                        if s_job.recurrence == 'once':
                            s_job.status = 'executed'
                        else:
                            # Calculate next schedule
                            if s_job.recurrence == 'daily':
                                s_job.scheduled_at += timedelta(days=1)
                            elif s_job.recurrence == 'weekly':
                                s_job.scheduled_at += timedelta(weeks=1)
                            elif s_job.recurrence == 'monthly':
                                # FIX: Use relativedelta for accurate monthly recurrence (e.g. 1 Jan -> 1 Feb)
                                from dateutil.relativedelta import relativedelta
                                s_job.scheduled_at += relativedelta(months=+1)
                            
                            s_job.status = 'pending' # Stay pending for next cycle
                        
                        s_job.last_executed = now
                        s_job.execution_count += 1
                        db.session.commit()
                        logging.info(f"Scheduled job '{s_job.name}' processed successfully.")

                    except Exception as e:
                        logging.error(f"Error processing scheduled job {s_job.id}: {e}")
                        s_job.status = 'failed'
                        db.session.commit()

                # 4. Daily Maintenance (Grace Period Cleanup)
                # Run once a day at midnight (roughly)
                if now.hour == 0 and now.minute == 0:
                     from app.services.subscription_manager import cleanup_expired_grace_periods
                     logging.info("Starting daily grace period cleanup...")
                     cleanup_expired_grace_periods()

            except Exception as outer_e:
                logging.error(f"Scheduler worker outer error: {outer_e}")
                db.session.rollback()
            
            time.sleep(60) # Poll every minute
