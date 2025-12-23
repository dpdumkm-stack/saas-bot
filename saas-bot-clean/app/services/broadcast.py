import time
import json
import random
from app.extensions import db
from app.models import BroadcastJob, Toko, SystemConfig
from app.services.waha import kirim_waha_raw

def get_maintenance_mode():
    try:
        with db.session.no_autoflush: 
            config = SystemConfig.query.get('maintenance_mode')
            return config and config.value.lower() == 'true'
    except: return False

def worker_broadcast(app):
    with app.app_context():
        # Reset stuck jobs
        BroadcastJob.query.filter_by(status='RUNNING').update({'status': 'PENDING'})
        db.session.commit()
        
    while True:
        with app.app_context():
            try:
                # Simple job queue processing
                job = BroadcastJob.query.filter(BroadcastJob.status != 'COMPLETED').first()
                if job and not get_maintenance_mode():
                     # Mark running
                    if job.status == 'PENDING': 
                        job.status = 'RUNNING'
                        db.session.commit()
                        
                    targets = json.loads(job.target_list)
                    idx = job.processed_count
                    
                    if idx >= len(targets):
                        job.status = 'COMPLETED'
                        db.session.commit()
                        toko = Toko.query.get(job.toko_id)
                        if toko: kirim_waha_raw(job.toko_id, "✅ Broadcast Selesai!", toko.session_name)
                        continue
                        
                    try:
                        toko = Toko.query.get(job.toko_id)
                        target = targets[idx]
                        if toko: kirim_waha_raw(target, job.pesan, toko.session_name)
                        
                        job.processed_count += 1
                        db.session.commit()
                        time.sleep(random.uniform(8, 15)) # Anti-ban delay
                    except Exception as e:
                         # Log error but don't crash
                         print(f"Broadcast error: {e}")
                         time.sleep(5)
                else:
                    time.sleep(5)
            except Exception as e:
                print(f"Worker loop error: {e}")
                time.sleep(5)
