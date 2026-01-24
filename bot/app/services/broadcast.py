import time
from datetime import datetime, timedelta
import json
import random
import logging
import requests
from app.extensions import db
from app.models import BroadcastJob, Toko, SystemConfig, BroadcastBlacklist
from app.services.waha import kirim_waha_raw
from app.services.humanizer import Humanizer

def get_maintenance_mode():
    try:
        with db.session.no_autoflush: 
            config = SystemConfig.query.get('maintenance_mode')
            return config and config.value.lower() == 'true'
    except: return False

def get_panic_mode():
    try:
        with db.session.no_autoflush: 
            config = SystemConfig.query.get('panic_mode')
            return config and config.value.lower() == 'true'
    except: return False

def calculate_progressive_delay(message_count: int) -> float:
    """
    Calculate randomized delay based on message count (progressive)
    Includes a 'human rest' every ~25 messages
    """
    # 1. Base progressive delay (Randomized) - WARMUP MODE (Anti-Block)
    if message_count < 10:
        delay = random.uniform(45, 90) # VERY SLOW START (Warmup)
    elif message_count < 50:
        delay = random.uniform(25, 50)
    elif message_count < 100:
        delay = random.uniform(15, 30)
    else:
        delay = random.uniform(12, 20) # Stabilization
        
    # 2. Add 'Human Rest' (Simulated break)
    # Every 20 messages, add a random long pause (3-7 minutes)
    if message_count > 0 and message_count % 20 == 0:
        rest_time = random.uniform(180, 420)
        logging.info(f"☕ Taking a human rest for {rest_time/60:.1f} minutes after {message_count} messages...")
        return delay + rest_time
        
    return delay


def send_with_retry(phone: str, message: str, session: str, max_retries: int = 3) -> bool:
    """
    Send message with retry logic and exponential backoff
    
    Args:
        phone: Target phone number
        message: Message to send
        session: Session name
        max_retries: Maximum retry attempts
        
    Returns:
        True if sent successfully, False otherwise
    """
    for attempt in range(max_retries):
        try:
            kirim_waha_raw(phone, message, session)
            return True
        except requests.exceptions.RequestException as e:
            error_str = str(e).lower()
            
            # Check for rate limit
            if '429' in error_str or 'rate limit' in error_str:
                logging.warning(f"Rate limited! Pausing for 5 minutes...")
                time.sleep(300)  # 5 minutes
                continue
            
            # Check for ban
            if 'banned' in error_str or '403' in error_str:
                logging.critical(f"Account may be banned! Error: {e}")
                return False
            
            # Regular retry with exponential backoff
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logging.warning(f"Retry {attempt + 1}/{max_retries} for {phone} in {wait_time}s. Error: {e}")
                time.sleep(wait_time)
            else:
                logging.error(f"Failed to send to {phone} after {max_retries} attempts: {e}")
                return False
    
    return False


def worker_broadcast(app):
    with app.app_context():
        # Reset stuck jobs on startup
        BroadcastJob.query.filter_by(status='RUNNING').update({'status': 'PENDING'})
        db.session.commit()
        
    while True:
        with app.app_context():
            try:
                # 1. Non-blocking query: Look for RUNNING/PENDING jobs that ARE NOT currently locked
                # This allows other workers to check the job but still ensures sequential processing per job
                job = BroadcastJob.query.filter(
                    (BroadcastJob.status.in_(['PENDING', 'RUNNING'])),
                    (BroadcastJob.locked_until == None) | (BroadcastJob.locked_until <= datetime.utcnow())
                ).with_for_update(skip_locked=True).first()
                
                if job and not get_maintenance_mode() and not get_panic_mode():
                    from app.services.message_variation import generate_message_variations
                    
                    # Mark as running if PENDING
                    if job.status == 'PENDING':
                        job.status = 'RUNNING'
                        logging.info(f"🚀 Job #{job.id} started")
                    
                    # Safety Bridge: Lock the job immediately to prevent other workers from picking it up
                    # when the DB row lock is released by the next commit.
                    job.locked_until = datetime.utcnow() + timedelta(minutes=1)
                    db.session.commit() # Row lock released here, but logic lock (locked_until) keeps it safe
                    
                    # Refresh targets
                    targets = json.loads(job.target_list)
                    
                    # Check if completed
                    if job.processed_count >= len(targets):
                        job.status = 'COMPLETED'
                        db.session.commit()
                        
                        # Notify completion (Phase 8E: Alerts)
                        from app.feature_flags import FeatureFlags
                        if FeatureFlags.is_alerts_enabled():
                            # ... (notification logic) ...
                            from app.config import Config
                            toko = Toko.query.get(job.toko_id)
                            success_rate = 100 # Simplification for notification
                            completion_msg = (
                                f"✅ *Broadcast Selesai!*\n\n"
                                f"📊 Total: {len(targets)}\n"
                                f"✅ Terkirim: {job.processed_count}\n"
                                f"🕐 Job ID: #{job.id}"
                            )
                            try:
                                n_session = Config.MASTER_SESSION if job.toko_id == 'SUPERADMIN' else (toko.session_name if toko else Config.MASTER_SESSION)
                                from app.services.waha import kirim_waha_raw
                                kirim_waha_raw(job.toko_id, completion_msg, n_session)
                            except Exception as e:
                                logging.error(f"Failed to send completion notification: {e}")
                        continue

                    try:
                        # 1. Verify Session Status before processing (Smart Guard)
                        from app.services.waha import check_session_status
                        from app.config import Config
                        session_name = Config.MASTER_SESSION
                        session_name = Config.MASTER_SESSION
                        if job.toko_id != 'SUPERADMIN':
                            toko = Toko.query.get(job.toko_id)
                            if toko: session_name = toko.session_name
                        
                        sess_status = check_session_status(session_name)
                        if sess_status != 'WORKING':
                            logging.warning(f"⏸️ Job #{job.id} paused: Session {session_name} is {sess_status}")
                            job.status = 'PENDING'
                            db.session.commit()
                            continue 

                        # 2. Sequential Check: Progress Cursor
                        idx = job.processed_count
                        
                        # 3. SELECTIVE RETRY: Skip targets that are already 'success'
                        while idx < len(targets) and targets[idx].get('status') == 'success':
                            idx += 1
                        
                        if idx >= len(targets):
                            job.status = 'COMPLETED'
                            job.updated_at = datetime.utcnow()
                            db.session.commit()
                            continue
                        
                        # Update cursor for the worker
                        job.processed_count = idx
                        db.session.commit()

                        # 4. Generate variations (AI-powered) if not already done
                        from app.services.message_variation import generate_message_variations
                        try:
                            if 'current_job_id' not in locals() or current_job_id != job.id:
                                global_variations = generate_message_variations(job.pesan, count=10)
                                current_job_id = job.id
                            variations = global_variations
                        except Exception as ai_err:
                            logging.error(f"AI Variation Error: {ai_err}")
                            variations = [job.pesan] # Fallback to original
                        
                        # Get target details
                        target = targets[idx]
                        
                        # ROBUST FIX: Auto-convert string targets to dicts on the fly
                        # This prevents "TypeError: 'str' object does not support item assignment"
                        if isinstance(target, str):
                            target = {'phone': target, 'name': ''}
                            targets[idx] = target
                            # Sync back to DB immediately to fix the data structure permanently
                            job.target_list = json.dumps(targets)
                            
                        from app.utils import normalize_phone_number
                        phone = normalize_phone_number(target.get('phone', target.get('phone_number', '')))
                        name = target.get('name', target.get('nama', ''))
                        is_blacklisted = BroadcastBlacklist.query.filter_by(phone_number=phone).first()
                        if is_blacklisted:
                            logging.info(f"Skipping {phone}: blacklisted")
                            targets[idx]['status'] = 'skipped'
                            job.target_list = json.dumps(targets)
                            job.processed_count += 1
                            job.skipped_count += 1
                            db.session.commit()
                            continue

                        # 4. WA Existence Check (Anti-Spam Shield)
                        from app.services.waha import check_exists
                        from app.config import Config
                        
                        # Get session: SUPERADMIN uses MASTER_SESSION, others use Toko session
                        session_name = Config.MASTER_SESSION
                        if job.toko_id != 'SUPERADMIN':
                            toko = Toko.query.get(job.toko_id)
                            if toko: session_name = toko.session_name

                        if not check_exists(phone, session_name=session_name):
                            logging.warning(f"🛡️ Skipping {phone}: Not on WhatsApp. Protecting account.")
                            targets[idx]['status'] = 'skipped'
                            job.target_list = json.dumps(targets)
                            job.processed_count += 1
                            job.skipped_count += 1
                            
                            # Track consecutive skips for emergency pause
                            if not hasattr(worker_broadcast, 'consecutive_skips'):
                                worker_broadcast.consecutive_skips = 0
                            worker_broadcast.consecutive_skips += 1
                            
                            if worker_broadcast.consecutive_skips >= 10:
                                job.status = 'PAUSED' # LOCK IT
                                logging.critical("🚨 EMERGENCY PAUSE: 10 consecutive non-WA numbers detected!")
                                try:
                                    from app.services.waha import kirim_waha_raw
                                    kirim_waha_raw(job.toko_id, "🚨 *BROADCAST DI-PAUSE*: Terdeteksi 10 nomor non-WA berturut-turut. Mohon cek kualitas daftar kontak Anda demi keamanan akun.", Config.MASTER_SESSION)
                                except: pass
                            
                            db.session.commit()
                            continue
                        
                        # Reset consecutive skips if number exists
                        worker_broadcast.consecutive_skips = 0

                        # Render and send
                        variation_idx = idx % len(variations)
                        message_template = variations[variation_idx]
                        from app.services.message_variation import render_personalized_message
                        final_message = render_personalized_message(message_template, {'nama': name})
                        
                        # 4.5. MANDATORY HUMANIZER (Anti-Block Shield)
                        # Apply physical variations (typos, invisible chars) to EVERY SINGLE MESSAGE
                        # This protects us even if AI Variation fails and returns identical templates.
                        final_message = Humanizer.humanize_text(final_message)

                        # 5. Tracking: Set 'sending' status and protective lock
                        targets[idx]['status'] = 'sending'
                        job.target_list = json.dumps(targets)
                        # Protect the job from other workers while we are doing the network call
                        job.locked_until = datetime.utcnow() + timedelta(minutes=2)
                        db.session.commit() # Lock released, but locked_until protects it

                        from app.services.waha import kirim_waha
                        # Get session: SUPERADMIN uses MASTER_SESSION, others use Toko session
                        # This block is redundant as session_name is already determined above, but keeping for consistency with original.
                        # session_name = Config.MASTER_SESSION
                        # if job.toko_id != 'SUPERADMIN':
                        #     toko = Toko.query.get(job.toko_id)
                        #     if toko: session_name = toko.session_name

                        success = kirim_waha(phone, final_message, session_name=session_name, add_delay=True, use_adaptive_delay=True)
                        
                        # 5. Granular Statistics (Phase 10A)
                        if success:
                            job.success_count += 1
                            targets[idx]['status'] = 'success' # Update status
                            worker_broadcast.consecutive_failures = 0 # Reset on success
                            
                            # Update Customer Context for AI Replies (Phase 10B)
                            try:
                                from app.models import Customer
                                customer = Customer.query.filter_by(toko_id=job.toko_id, nomor_hp=phone).first()
                                if customer:
                                    customer.last_broadcast_msg = final_message
                                    customer.last_broadcast_at = datetime.utcnow()
                                    customer.broadcast_reply_count = 0 # Reset safety fuse
                                    db.session.commit()
                            except Exception as context_err:
                                logging.error(f"Failed to update customer context: {context_err}")
                                db.session.rollback()
                        else:
                            job.failed_count += 1
                            targets[idx]['status'] = 'failed' # Update status
                            
                            # Capture error reason (Enhanced Logging)
                            # 'success' variable from kirim_waha is just boolean, but we can capture context if needed
                            # Ideally kirim_waha should return (success, error_msg) tuple, but for now we assume generic Delivery Failed if no exception
                            targets[idx]['error'] = "Delivery Failed (WAHA Error or Network Issue)"
                            
                            # Track consecutive failures for emergency pause (Session Down/Blocked)
                            if not hasattr(worker_broadcast, 'consecutive_failures'):
                                worker_broadcast.consecutive_failures = 0
                            worker_broadcast.consecutive_failures += 1
                            
                            # SMART CIRCUIT BREAKER: Pause after 5 consecutive failures (Limit Risk)
                            if worker_broadcast.consecutive_failures >= 5:
                                job.status = 'PAUSED' # LOCK IT
                                logging.critical(f"🚨 EMERGENCY PAUSE: 5 consecutive failures detected for Job #{job.id}!")
                                
                                # Add system note to job target list
                                targets[idx]['error'] = "Delivery Failed & Job Paused (Circuit Breaker Triggered)"
                                
                                try:
                                    from app.services.waha import kirim_waha_raw
                                    pause_msg = (
                                        f"🚨 *BROADCAST DI-PAUSE OTOMATIS*\n"
                                        f"Terdeteksi 5 kegagalan berturut-turut pada Job #{job.id}.\n"
                                        f"Demi keamanan akun, broadcast dihentikan sementara.\n"
                                        f"👉 Cek koneksi WAHA / Kualitas nomor tujuan."
                                    )
                                    kirim_waha_raw(job.toko_id, pause_msg, Config.MASTER_SESSION)
                                except: pass
                                
                                # COMMIT & CONTINUE to avoid tight loop
                                job.target_list = json.dumps(targets) 
                                # Add a 5-minute safety lock even if paused, just in case
                                job.locked_until = datetime.utcnow() + timedelta(minutes=5)
                                db.session.commit()
                                continue # Move to next job or next poll

                        # 6. Serialization Fix: Update target_list with final status (success/failed)
                        job.target_list = json.dumps(targets)
                        
                        # 6. IMMEDIATE PROGRESS UPDATE (Fixes UI Lag)
                        job.processed_count += 1
                        
                        # 7. Calculate safety delay and release the protective lock
                        delay_seconds = calculate_progressive_delay(idx + 1)
                        job.locked_until = datetime.utcnow() + timedelta(seconds=delay_seconds)
                        
                        # Commit now to show progress and allow next pickup after delay
                        db.session.commit()
                        
                        if success:
                            logging.info(f"✅ Sent {idx + 1}/{len(targets)} to {phone}")
                        else:
                            logging.error(f"❌ Failed to send to {phone}")

                        time.sleep(0.5) # Stability

                    except Exception as e:
                        logging.error(f"Error processing target index {idx}: {e}")
                        db.session.rollback()
                        time.sleep(5)
                else:
                    time.sleep(5)  # No job or maintenance mode
                    
            except Exception as e:
                logging.error(f"Worker loop error: {e}")
                time.sleep(5)
