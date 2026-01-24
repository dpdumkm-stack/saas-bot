import logging
from datetime import datetime
from app.models import AuditLog
from app.extensions import db

def log_audit(toko_id, admin_hp, action, target_type, target_id, old_value=None, new_value=None):
    """
    Log a sensitive system change to the audit trail.
    
    Args:
        toko_id: ID of the store (or 'SYSTEM')
        admin_hp: Phone number of the admin performing the action
        action: Short string describing the action (e.g., 'UPDATE_PRICE')
        target_type: Object type affected (e.g., 'MENU', 'CUSTOMER')
        target_id: ID of the specific object
        old_value: Previous state (JSON or string)
        new_value: New state (JSON or string)
    """
    try:
        log = AuditLog(
            toko_id=toko_id,
            admin_hp=admin_hp,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        logging.info(f"AUDIT LOG: {action} by {admin_hp} on {target_type}:{target_id}")
    except Exception as e:
        logging.error(f"FAILED TO WRITE AUDIT LOG: {e}")
        db.session.rollback()
