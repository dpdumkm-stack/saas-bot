import os
import shutil
import time
import logging
from datetime import datetime

def backup_system(app):
    if not os.path.exists('backups'): os.makedirs('backups')
    while True:
        time.sleep(21600) # 6 hours
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            shutil.copy2('saas_umkm.db', f'backups/backup_{ts}.db')
            backups = sorted(os.listdir('backups'))
            if len(backups) > 10: os.remove(os.path.join('backups', backups[0]))
        except Exception as e: logging.error(f"Backup Fail: {e}")
