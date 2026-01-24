"""
Opt-Out Management Service
Handles broadcast blacklist operations for GDPR compliance
"""
import logging
from datetime import datetime
from app.extensions import db
from app.models import BroadcastBlacklist

class OptOutManager:
    """Manages broadcast opt-out/opt-in operations"""
    
    @staticmethod
    def add_to_blacklist(phone_number: str, reason: str = 'user_request', notes: str = None) -> bool:
        """
        Add phone number to blacklist
        
        Args:
            phone_number: Phone number to blacklist
            reason: Reason for blacklisting
            notes: Optional notes
            
        Returns:
            True if successful
        """
        try:
            # Check if already blacklisted
            existing = BroadcastBlacklist.query.get(phone_number)
            if existing:
                logging.info(f"{phone_number} already in blacklist")
                return True
            
            # Add to blacklist
            entry = BroadcastBlacklist(
                phone_number=phone_number,
                opted_out_at=datetime.now(),
                reason=reason,
                can_resubscribe=True,
                notes=notes
            )
            db.session.add(entry)
            db.session.commit()
            
            logging.info(f"Added {phone_number} to blacklist (reason: {reason})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to add {phone_number} to blacklist: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def remove_from_blacklist(phone_number: str) -> bool:
        """
        Remove phone number from blacklist (opt-in)
        
        Args:
            phone_number: Phone number to remove
            
        Returns:
            True if successful
        """
        try:
            entry = BroadcastBlacklist.query.get(phone_number)
            if not entry:
                logging.info(f"{phone_number} not in blacklist")
                return True
            
            if not entry.can_resubscribe:
                logging.warning(f"{phone_number} cannot resubscribe (permanent ban)")
                return False
            
            db.session.delete(entry)
            db.session.commit()
            
            logging.info(f"Removed {phone_number} from blacklist")
            return True
            
        except Exception as e:
            logging.error(f"Failed to remove {phone_number} from blacklist: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def is_blacklisted(phone_number: str) -> bool:
        """
        Check if phone number is blacklisted
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            True if blacklisted
        """
        try:
            return BroadcastBlacklist.query.get(phone_number) is not None
        except Exception as e:
            logging.error(f"Failed to check blacklist for {phone_number}: {e}")
            return False  # Fail open (allow if check fails)
    
    @staticmethod
    def get_all_blacklisted(limit: int = 1000):
        """
        Get all blacklisted numbers
        
        Args:
            limit: Maximum results
            
        Returns:
            List of BroadcastBlacklist entries
        """
        try:
            return BroadcastBlacklist.query.order_by(
                BroadcastBlacklist.opted_out_at.desc()
            ).limit(limit).all()
        except Exception as e:
            logging.error(f"Failed to get blacklist: {e}")
            return []
    
    @staticmethod
    def get_blacklist_count() -> int:
        """Get total count of blacklisted numbers"""
        try:
            return BroadcastBlacklist.query.count()
        except:
            return 0
