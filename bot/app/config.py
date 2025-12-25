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
    WAHA_BASE_URL = os.environ.get('WAHA_BASE_URL', 'http://localhost:3000')
    MASTER_SESSION = os.environ.get('MASTER_SESSION', 'default')
    TARGET_LIMIT_USER = int(os.environ.get('TARGET_LIMIT_USER', '500'))
    WARNING_THRESHOLD = int(os.environ.get('WARNING_THRESHOLD', '450'))
    WAHA_API_KEY = os.environ.get('WAHA_API_KEY', "abc123secretkeyQM8")
    WAHA_WEBHOOK_URL = os.environ.get('WAHA_WEBHOOK_URL', 'http://172.25.0.10:5000/webhook')
