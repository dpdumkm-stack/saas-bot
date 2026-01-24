"""
Error Monitoring Service
Automatically tracks errors and sends WhatsApp alerts to admin
"""

import logging
from datetime import datetime, timedelta
from app.models import SystemConfig
from app.extensions import db
from app.services.waha import kirim_waha
from app.config import Config

class ErrorMonitor:
    """Track and alert on application errors"""
    
    ERROR_THRESHOLD = 5  # Alert after N errors
    WINDOW_MINUTES = 5   # Within N minutes
    
    @staticmethod
    def log_error(error_type, message, severity="ERROR"):
        """
        Log error and send alert if threshold exceeded
        
        Args:
            error_type: str - Category (GEMINI_FAILURE, DB_ERROR, WAHA_ERROR, etc)
            message: str - Error details
            severity: str - ERROR, CRITICAL, WARNING
        
        Usage:
            from app.services.error_monitoring import ErrorMonitor
            
            try:
                ai_response = get_gemini_response(...)
            except Exception as e:
                ErrorMonitor.log_error("GEMINI_FAILURE", str(e), "CRITICAL")
        """
        # 1. Log to Cloud Logging (automatic)
        if severity == "CRITICAL":
            logging.critical(f"[{error_type}] {message}")
        elif severity == "ERROR":
            logging.error(f"[{error_type}] {message}")
        else:
            logging.warning(f"[{error_type}] {message}")
        
        # 2. Count errors in time window
        error_count_key = f"error_count_{error_type}"
        
        try:
            error_count = SystemConfig.query.get(error_count_key)
            
            if not error_count:
                error_count = SystemConfig(key=error_count_key, value="0")
                db.session.add(error_count)
            
            current_count = int(error_count.value or 0) + 1
            error_count.value = str(current_count)
            error_count.updated_at = datetime.utcnow()
            db.session.commit()
            
            # 3. Check if threshold exceeded
            if current_count >= ErrorMonitor.ERROR_THRESHOLD:
                ErrorMonitor._send_admin_alert(error_type, message, current_count)
                # Reset counter after alert sent
                error_count.value = "0"
                db.session.commit()
        
        except Exception as e:
            # Don't let monitoring errors break the app
            logging.error(f"Error in ErrorMonitor: {e}")
    
    @staticmethod
    def _send_admin_alert(error_type, message, count):
        """Send WhatsApp alert to admin"""
        alert_msg = (
            f"🚨 *ALERT: {error_type}*\n\n"
            f"Error terjadi {count}x dalam {ErrorMonitor.WINDOW_MINUTES} menit!\n\n"
            f"*Details:*\n{message[:200]}...\n\n"
            f"_Check logs: https://console.cloud.google.com/logs_"
        )
        
        try:
            if Config.SUPER_ADMIN_WA:
                kirim_waha(
                    Config.SUPER_ADMIN_WA, 
                    alert_msg, 
                    Config.MASTER_SESSION
                )
                logging.info(f"Admin alert sent for {error_type}")
        except Exception as e:
            logging.error(f"Failed to send admin alert: {e}")
    
    @staticmethod
    def reset_old_counters():
        """
        Reset error counters older than time window
        Call this via cron job every hour
        
        Add to cron.py:
            @cron_bp.route('/hourly_cleanup')
            def hourly_cleanup():
                ErrorMonitor.reset_old_counters()
                return jsonify({"status": "ok"})
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=ErrorMonitor.WINDOW_MINUTES)
            
            old_counters = SystemConfig.query.filter(
                SystemConfig.key.like('error_count_%'),
                SystemConfig.updated_at < cutoff_time
            ).all()
            
            for counter in old_counters:
                counter.value = "0"
            
            db.session.commit()
            logging.info(f"Reset {len(old_counters)} old error counters")
            
        except Exception as e:
            logging.error(f"Error resetting counters: {e}")
