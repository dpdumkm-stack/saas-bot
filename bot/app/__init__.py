from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.config import Config
from app.extensions import db, limiter
import threading
import logging
import sys

def create_app():
    # Configure logging to stdout for Docker
    logging.basicConfig(
        stream=sys.stdout, 
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    
    app = Flask(__name__, template_folder='../templates') # Templates are in root/templates
    app.config.from_object(Config)
    
    db.init_app(app)
    limiter.init_app(app)
    
    # SQLite optimization (only works for SQLite, silently skipped for PostgreSQL)
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            # PRAGMA commands are SQLite-specific, will fail on PostgreSQL
            # This is expected and can be safely ignored
            pass

    with app.app_context():
        # Import models
        from app import models
        db.create_all()
        
        # Initialize maintenance mode if missing
        from app.models import SystemConfig
        if not SystemConfig.query.get('maintenance_mode'):
             db.session.add(SystemConfig(key='maintenance_mode', value='false'))
             db.session.commit()

    # Register Blueprints
    from app.routes.webhook import webhook_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Start Background Workers
    from app.services.broadcast import worker_broadcast
    from app.services.backup import backup_system
    
    threading.Thread(target=worker_broadcast, args=(app,), daemon=True).start()
    threading.Thread(target=backup_system, args=(app,), daemon=True).start()
    
    # Start Session Management Worker
    from app.routes.api import create_and_start_session_bg
    threading.Thread(target=create_and_start_session_bg, daemon=True).start()
    
    # Start Polling Worker (Fallback for broken Webhooks)
    from app.services.poller import WahaPoller
    WahaPoller(app).start()
    
    return app
