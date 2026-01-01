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
    
    # SQLite optimization - Only register for SQLite databases
    # Check database type from connection string before registering event listener
    database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if database_url.startswith('sqlite'):
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    with app.app_context():
        # Import models
        from app import models
        
        # Create tables if they don't exist
        # Wrapped in try-except to handle race conditions when multiple instances start
        try:
            db.create_all()
        except Exception as e:
            # If tables already exist or another instance is creating them, that's fine
            # Log but don't crash
            app.logger.warning(f"db.create_all() warning (expected on concurrent startup): {e}")
        
        # Auto-migrate: Add missing columns
        try:
            from sqlalchemy import text, inspect
            inspector = inspect(db.engine)
            
            app.logger.info("=== Starting database migration check ===")
            
            # Check Customer table
            customer_cols = [col['name'] for col in inspector.get_columns('customer')]
            app.logger.info(f"Current customer columns: {customer_cols}")
            migrations_run = False
            
            if 'last_interaction' not in customer_cols:
                app.logger.info("Adding missing column: customer.last_interaction")
                try:
                    db.session.execute(text("ALTER TABLE customer ADD COLUMN last_interaction TIMESTAMP DEFAULT NOW()"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add customer.last_interaction: {col_err}")
            
            if 'followup_status' not in customer_cols:
                app.logger.info("Adding missing column: customer.followup_status")
                try:
                    db.session.execute(text("ALTER TABLE customer ADD COLUMN followup_status VARCHAR(20) DEFAULT 'NONE'"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add customer.followup_status: {col_err}")
            
            if 'last_context' not in customer_cols:
                app.logger.info("Adding missing column: customer.last_context")
                try:
                    db.session.execute(text("ALTER TABLE customer ADD COLUMN last_context TEXT DEFAULT ''"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add customer.last_context: {col_err}")
            
            # Check Toko table
            toko_cols = [col['name'] for col in inspector.get_columns('toko')]
            app.logger.info(f"Current toko columns: {toko_cols}")
            
            if 'knowledge_base_file_id' not in toko_cols:
                app.logger.info("Adding missing column: toko.knowledge_base_file_id")
                try:
                    db.session.execute(text("ALTER TABLE toko ADD COLUMN knowledge_base_file_id VARCHAR(100)"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add toko.knowledge_base_file_id: {col_err}")
            
            if 'knowledge_base_name' not in toko_cols:
                app.logger.info("Adding missing column: toko.knowledge_base_name")
                try:
                    db.session.execute(text("ALTER TABLE toko ADD COLUMN knowledge_base_name VARCHAR(100)"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add toko.knowledge_base_name: {col_err}")
            
            if 'shipping_origin_id' not in toko_cols:
                app.logger.info("Adding missing column: toko.shipping_origin_id")
                try:
                    db.session.execute(text("ALTER TABLE toko ADD COLUMN shipping_origin_id INTEGER"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add toko.shipping_origin_id: {col_err}")
            
            if 'shipping_couriers' not in toko_cols:
                app.logger.info("Adding missing column: toko.shipping_couriers")
                try:
                    db.session.execute(text("ALTER TABLE toko ADD COLUMN shipping_couriers VARCHAR(50) DEFAULT 'jne'"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add toko.shipping_couriers: {col_err}")
            
            if 'setup_step' not in toko_cols:
                app.logger.info("Adding missing column: toko.setup_step")
                try:
                    db.session.execute(text("ALTER TABLE toko ADD COLUMN setup_step VARCHAR(20) DEFAULT 'NONE'"))
                    migrations_run = True
                except Exception as col_err:
                    app.logger.error(f"Failed to add toko.setup_step: {col_err}")
            
            if migrations_run:
                db.session.commit()
                app.logger.info("=== Database migrations committed successfully ===")
            else:
                app.logger.info("=== Database schema is up to date ===")
                
        except Exception as e:
            app.logger.error(f"Migration error (non-fatal): {e}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
        
        # Initialize maintenance mode if missing
        from app.models import SystemConfig
        if not SystemConfig.query.get('maintenance_mode'):
             db.session.add(SystemConfig(key='maintenance_mode', value='false'))
             db.session.commit()

    # Register Blueprints
    from app.routes.webhook import webhook_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.payment_webhook import payment_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(payment_bp)
    app.register_blueprint(dashboard_bp)
    
    # Start Background Workers
    from app.services.broadcast import worker_broadcast
    from app.services.backup import backup_system
    
    threading.Thread(target=worker_broadcast, args=(app,), daemon=True).start()
    threading.Thread(target=backup_system, args=(app,), daemon=True).start()
    
    # Start Session Management Worker
    # from app.routes.api import create_and_start_session_bg
    # threading.Thread(target=create_and_start_session_bg, daemon=True).start()
    
    
    # Polling disabled - using webhooks only
    # from app.services.poller import WahaPoller
    # WahaPoller(app).start()
    
    return app
