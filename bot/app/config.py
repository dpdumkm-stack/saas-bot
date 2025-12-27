import os
from dotenv import load_dotenv
import secrets

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///saas_umkm.db?timeout=30'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_size': 10, 'max_overflow': 20}
    
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    SUPER_ADMIN_WA = os.environ.get('SUPER_ADMIN_WA', '')
    
    # WAHA Plus Configuration (SUMOPOD Hosted)
    # Production: https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id
    WAHA_BASE_URL = os.environ.get('WAHA_BASE_URL', 'https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id') 
    WAHA_API_KEY = os.environ.get('WAHA_API_KEY', '')  # Required for SUMOPOD API access
    
    # Session Configuration
    MASTER_SESSION = 'saas_bot'
    TARGET_LIMIT_USER = int(os.environ.get('TARGET_LIMIT_USER', '500'))
    WARNING_THRESHOLD = int(os.environ.get('WARNING_THRESHOLD', '450'))
    
    # Webhook URL (set in SUMOPOD to point to Cloud Run)
    WAHA_WEBHOOK_URL = os.environ.get('WAHA_WEBHOOK_URL', 'https://saas-bot-643221888510.asia-southeast2.run.app/webhook')
