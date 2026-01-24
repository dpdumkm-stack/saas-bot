from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.config import Config
from app.extensions import db, limiter
import threading
import logging
import sys
import os

# POSIX locking (for Linux/Cloud Run)
try:
    import fcntl
except ImportError:
    fcntl = None # Fallback for local Windows development

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
            
            # Auto-migrate: Add missing columns
            if True:
                inspector = inspect(db.engine)
                
                # app.logger.info("=== Starting database migration check ===")
                # TEMPORARY DISABLE: Migration check causing startup hang
                migrations_run = False
                
                # Check Customer table
                if 'customer' in inspector.get_table_names():
                    customer_cols = [col['name'] for col in inspector.get_columns('customer')]
                    app.logger.info(f"Current customer columns: {customer_cols}")
                    migrations_run = False
                else:
                    app.logger.info("Table 'customer' doesn't exist yet, skipping migration check.")
                    customer_cols = []
                    migrations_run = False
                
                if 'last_interaction' not in customer_cols:
                    app.logger.info("Adding missing column: customer.last_interaction")
                    try:
                        default_now = "CURRENT_TIMESTAMP" if database_url.startswith('sqlite') else "now()"
                        db.session.execute(text(f"ALTER TABLE customer ADD COLUMN last_interaction TIMESTAMP DEFAULT {default_now}"))
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
                        # SQLite doesn't support DEFAULT value with ALTER TABLE ADD COLUMN and a non-constant (sometimes)
                        # Use a simple approach compatible with both
                        db.session.execute(text("ALTER TABLE customer ADD COLUMN last_context TEXT"))
                        migrations_run = True
                    except Exception as col_err:
                        app.logger.error(f"Failed to add customer.last_context: {col_err}")
                
                if 'customer' in inspector.get_table_names():
                    cust_cols = [col['name'] for col in inspector.get_columns('customer')]
                    # Context Aware Broadcast & Safety Fuse (v3.9.7)
                    if 'last_broadcast_msg' not in cust_cols:
                        app.logger.info("Adding missing column: customer.last_broadcast_msg")
                        try:
                            db.session.execute(text("ALTER TABLE customer ADD COLUMN last_broadcast_msg TEXT"))
                            migrations_run = True
                        except Exception as col_err:
                            app.logger.error(f"Failed to add customer.last_broadcast_msg: {col_err}")
                            
                    if 'last_broadcast_at' not in cust_cols:
                        app.logger.info("Adding missing column: customer.last_broadcast_at")
                        try:
                            db.session.execute(text("ALTER TABLE customer ADD COLUMN last_broadcast_at TIMESTAMP NULL"))
                            migrations_run = True
                        except Exception as col_err:
                            app.logger.error(f"Failed to add customer.last_broadcast_at: {col_err}")
                            
                    if 'broadcast_reply_count' not in cust_cols:
                        app.logger.info("Adding missing column: customer.broadcast_reply_count")
                        try:
                            db.session.execute(text("ALTER TABLE customer ADD COLUMN broadcast_reply_count INTEGER DEFAULT 0"))
                            migrations_run = True
                        except Exception as col_err:
                            app.logger.error(f"Failed to add customer.broadcast_reply_count: {col_err}")
                
                # Check Toko table
                if 'toko' in inspector.get_table_names():
                    toko_cols = [col['name'] for col in inspector.get_columns('toko')]
                    app.logger.info(f"Current toko columns: {toko_cols}")
                else:
                    app.logger.info("Table 'toko' doesn't exist yet, skipping migration check.")
                    toko_cols = []
                
                if 'timezone' not in toko_cols:
                    app.logger.info("Adding missing column: toko.timezone")
                    try:
                        db.session.execute(text("ALTER TABLE toko ADD COLUMN timezone VARCHAR(50) DEFAULT 'Asia/Jakarta'"))
                        migrations_run = True
                    except Exception as col_err:
                        app.logger.error(f"Failed to add toko.timezone: {col_err}")

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

                # Check Menu table
                if 'menu' in inspector.get_table_names():
                    menu_cols = [col['name'] for col in inspector.get_columns('menu')]
                    app.logger.info(f"Current menu columns: {menu_cols}")
                else:
                        # Should exist by now if create_all ran, but just in case
                    menu_cols = []
                
                if 'category' not in menu_cols:
                    app.logger.info("Adding missing column: menu.category")
                    try:
                        db.session.execute(text("ALTER TABLE menu ADD COLUMN category VARCHAR(50) DEFAULT 'Umum'"))
                        migrations_run = True
                    except Exception as col_err:
                        app.logger.error(f"Failed to add menu.category: {col_err}")

                if 'image_url' not in menu_cols:
                    app.logger.info("Adding missing column: menu.image_url")
                    try:
                        db.session.execute(text("ALTER TABLE menu ADD COLUMN image_url VARCHAR(500)"))
                        migrations_run = True
                    except Exception as col_err:
                        app.logger.error(f"Failed to add menu.image_url: {col_err}")

                if 'description' not in menu_cols:
                    app.logger.info("Adding missing column: menu.description")
                    try:
                        db.session.execute(text("ALTER TABLE menu ADD COLUMN description TEXT"))
                        migrations_run = True
                    except Exception as col_err:
                        app.logger.error(f"Failed to add menu.description: {col_err}")
                
                # Check BroadcastJob table
                if 'broadcast_job' in inspector.get_table_names():
                    broadcast_cols = [col['name'] for col in inspector.get_columns('broadcast_job')]
                    if 'updated_at' not in broadcast_cols:
                        app.logger.info("Adding missing column: broadcast_job.updated_at")
                        try:
                            default_now = "CURRENT_TIMESTAMP" if database_url.startswith('sqlite') else "now()"
                            db.session.execute(text(f"ALTER TABLE broadcast_job ADD COLUMN updated_at TIMESTAMP DEFAULT {default_now}"))
                            migrations_run = True
                        except Exception as col_err:
                            app.logger.error(f"Failed to add broadcast_job.updated_at: {col_err}")
                    
                    if 'locked_until' not in broadcast_cols:
                        app.logger.info("Adding missing column: broadcast_job.locked_until")
                        try:
                            db.session.execute(text("ALTER TABLE broadcast_job ADD COLUMN locked_until TIMESTAMP NULL"))
                            migrations_run = True
                        except Exception as col_err:
                            app.logger.error(f"Failed to add broadcast_job.locked_until: {col_err}")

                    # Analytics Columns (Phase 10)
                    for col_name in ['success_count', 'failed_count', 'skipped_count']:
                        if col_name not in broadcast_cols:
                            app.logger.info(f"Adding missing column: broadcast_job.{col_name}")
                            try:
                                db.session.execute(text(f"ALTER TABLE broadcast_job ADD COLUMN {col_name} INTEGER DEFAULT 0"))
                                migrations_run = True
                            except Exception as col_err:
                                app.logger.error(f"Failed to add broadcast_job.{col_name}: {col_err}")
                
                
                # Check for AuditLog table
                if 'scheduled_broadcast' in inspector.get_table_names():
                    sched_cols = [col['name'] for col in inspector.get_columns('scheduled_broadcast')]
                    if 'target_list' not in sched_cols:
                        app.logger.info("Adding missing column: scheduled_broadcast.target_list")
                        try:
                            db.session.execute(text("ALTER TABLE scheduled_broadcast ADD COLUMN target_list TEXT"))
                            migrations_run = True
                        except Exception as col_err:
                            app.logger.error(f"Failed to add scheduled_broadcast.target_list: {col_err}")
                
                # Check for AuditLog table
                if 'audit_log' not in inspector.get_table_names():
                    app.logger.info("Creating missing table: audit_log")
                    try:
                        db.create_all()
                        migrations_run = True
                    except Exception as e:
                        app.logger.error(f"Failed to create audit_log table: {e}")
                
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

    # --- GLOBAL ERROR HANDLER (Phase 9B) ---
    @app.errorhandler(500)
    def handle_internal_error(e):
        from app.services.error_monitoring import ErrorMonitor
        import traceback
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        app.logger.error(f"Global 500 Error: {error_msg}\n{stack_trace}")
        
        # Non-blocking alert
        try:
            ErrorMonitor.log_error("GLOBAL_500_ERROR", f"{error_msg}\nTrace: {stack_trace[:300]}", severity="CRITICAL")
        except: pass
        
        from flask import jsonify
        return jsonify({"status": "error", "message": "Internal Server Error"}), 500

    @app.errorhandler(404)
    def handle_not_found_error(e):
        return "404 Not Found", 404

    with app.app_context():
        # Initialize maintenance mode if missing
        from app.models import SystemConfig
        if not SystemConfig.query.get('maintenance_mode'):
             db.session.add(SystemConfig(key='maintenance_mode', value='false'))
             db.session.commit()
        if not SystemConfig.query.get('panic_mode'):
             db.session.add(SystemConfig(key='panic_mode', value='false'))
             db.session.commit()

    # Register Blueprints
    from app.routes.webhook import webhook_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.payment_webhook import payment_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.cron import cron_bp
    from app.routes.superadmin import superadmin_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(payment_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cron_bp, url_prefix='/api/cron')
    app.register_blueprint(superadmin_bp)
    
    # Start Background Workers (Surgical Guard: Only ONE process/worker allowed)
    def start_workers_safe():
        lock_path = '/tmp/saas_worker.lock'
        
        # In non-POSIX environments (like local Windows), threads will always start
        if not fcntl:
            logging.info("⚠️ Non-POSIX environment detected. Starting workers without system lock.")
        else:
            try:
                # Open or create the lock file
                lock_file = open(lock_path, 'w')
                # Acquire an exclusive lock (non-blocking)
                # If this fails, it means another gunicorn worker already has the lock
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logging.info(f"✨ Process {os.getpid()} acquired worker lock. Starting background threads...")
                # Keep a reference to the lock_file to prevent it from being closed/unlocked
                app.worker_lock_file = lock_file 
            except (IOError, OSError):
                logging.info(f"💤 Process {os.getpid()} is a standby worker (No background threads started).")
                return

        from app.services.broadcast import worker_broadcast
        from app.services.sales_engine import worker_sales_engine
        from app.services.scheduler import worker_scheduler
        
        threading.Thread(target=worker_broadcast, args=(app,), name="BroadcastWorker", daemon=True).start()
        threading.Thread(target=worker_sales_engine, args=(app,), name="SalesEngine", daemon=True).start()
        threading.Thread(target=worker_scheduler, args=(app,), name="Scheduler", daemon=True).start()
    
    # Run the safest worker startup
    start_workers_safe()
    
    return app
