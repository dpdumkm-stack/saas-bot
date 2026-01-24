"""
Broadcast Manager for Superadmin
Handles CSV upload, DB segments, and broadcast orchestration
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.extensions import db
from app.models import BroadcastJob, Subscription, Customer
from app.feature_flags import FeatureFlags

class BroadcastManager:
    """Manages broadcast campaigns for superadmin"""
    
    @staticmethod
    def get_segment_targets(segment_name: str) -> List[Dict]:
        """
        Get phone numbers for predefined segments
        
        Args:
            segment_name: Name of segment (e.g., 'all_merchants', 'active')
            
        Returns:
            List of dicts with 'phone' and 'name' keys
        """
        segments = {
            'all_merchants': lambda: Subscription.query.all(),
            'active': lambda: Subscription.query.filter_by(status='ACTIVE').all(),
            'expired': lambda: Subscription.query.filter_by(status='EXPIRED').all(),
            'trial': lambda: Subscription.query.filter_by(tier='TRIAL').all(),
            'starter': lambda: Subscription.query.filter_by(tier='STARTER', status='ACTIVE').all(),
            'business': lambda: Subscription.query.filter_by(tier='BUSINESS', status='ACTIVE').all(),
            'pro': lambda: Subscription.query.filter_by(tier='PRO', status='ACTIVE').all(),
        }
        
        if segment_name not in segments:
            return []
        
        from app.utils import normalize_phone_number
        subs = segments[segment_name]()
        return [{'phone': normalize_phone_number(sub.phone_number), 'name': ''} for sub in subs if sub.phone_number]
    
    @staticmethod
    def get_available_segments() -> Dict[str, int]:
        """
        Get all available segments with counts
        
        Returns:
            Dict mapping segment name to count
        """
        return {
            'all_merchants': Subscription.query.count(),
            'active': Subscription.query.filter_by(status='ACTIVE').count(),
            'expired': Subscription.query.filter_by(status='EXPIRED').count(),
            'trial': Subscription.query.filter_by(tier='TRIAL').count(),
            'starter': Subscription.query.filter_by(tier='STARTER', status='ACTIVE').count(),
            'business': Subscription.query.filter_by(tier='BUSINESS', status='ACTIVE').count(),
            'pro': Subscription.query.filter_by(tier='PRO', status='ACTIVE').count(),
        }
    
    @staticmethod
    def create_broadcast_job(
        toko_id: str, 
        message: str, 
        targets: List,  # Can be List[str] or List[Dict]
        source: str = 'manual'
    ) -> Optional[int]:
        """
        Create a new broadcast job
        
        Args:
            toko_id: Toko ID (use 'SUPERADMIN' for superadmin broadcasts)
            message: Broadcast message
            targets: List of phone numbers (strings) or dicts with 'phone' and 'name'
            source: Source of targets ('csv', 'segment', 'manual')
            
        Returns:
            Job ID if successful, None otherwise
        """
        # Safety checks
        if not targets:
            logging.error("Cannot create broadcast job: no targets")
            return None
        
        # Normalize targets to consistent format (list of dicts)
        normalized_targets = []
        for target in targets:
            if isinstance(target, str):
                # Old format: just phone number
                normalized_targets.append({'phone': target, 'name': ''})
            elif isinstance(target, dict):
                # New format: already dict
                normalized_targets.append(target)
            else:
                logging.warning(f"Invalid target type: {type(target)}")
        
        if len(normalized_targets) > FeatureFlags.BROADCAST_MAX_TARGETS:
            logging.error(f"Too many targets: {len(normalized_targets)} > {FeatureFlags.BROADCAST_MAX_TARGETS}")
            return None
        
        # Check daily limit
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        total_today = db.session.query(db.func.sum(BroadcastJob.processed_count)).filter(
            BroadcastJob.created_at >= today_start,
            BroadcastJob.toko_id == toko_id
        ).scalar() or 0
        
        if total_today + len(normalized_targets) > FeatureFlags.BROADCAST_DAILY_LIMIT:
            logging.error(f"Daily limit exceeded: {total_today} + {len(normalized_targets)} > {FeatureFlags.BROADCAST_DAILY_LIMIT}")
            return None
        
        try:
            job = BroadcastJob(
                toko_id=toko_id,
                pesan=message,
                target_list=json.dumps(normalized_targets),
                status='PENDING'
            )
            db.session.add(job)
            db.session.commit()
            
            logging.info(f"Created broadcast job {job.id} with {len(normalized_targets)} targets (source: {source})")
            return job.id
            
        except Exception as e:
            logging.error(f"Failed to create broadcast job: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def rescue_stuck_jobs():
        """
        Reset stuck RUNNING jobs to PENDING if not updated in last 5 mins
        Called by cron/heartbeat
        """
        try:
            five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
            stuck_jobs = BroadcastJob.query.filter(
                BroadcastJob.status == 'RUNNING',
                BroadcastJob.updated_at < five_mins_ago
            ).all()
            
            if stuck_jobs:
                count = 0
                for job in stuck_jobs:
                    job.status = 'PENDING'
                    job.locked_until = None
                    count += 1
                db.session.commit()
                logging.warning(f"Rescued {count} stuck broadcast jobs (reset to PENDING)")
                return count
        except Exception as e:
            logging.error(f"Error rescuing jobs: {e}")
            return 0

    @staticmethod
    def format_segment_menu() -> str:
        """
        Format segment menu for display
        
        Returns:
            Formatted menu string
        """
        segments = BroadcastManager.get_available_segments()
        
        menu = "📊 *PILIH TARGET BROADCAST*\n\n"
        menu += "💡 Ketik angka untuk pilih segment:\n\n"
        
        menu_items = [
            ('1', 'all_merchants', '📢 Semua Merchant'),
            ('2', 'active', '✅ Merchant Aktif'),
            ('3', 'expired', '⏰ Merchant Expired'),
            ('4', 'trial', '🆓 Trial Users'),
            ('5', 'starter', '📦 Starter Plan'),
            ('6', 'business', '💼 Business Plan'),
            ('7', 'pro', '⭐ Pro Plan'),
        ]
        
        for num, key, label in menu_items:
            count = segments.get(key, 0)
            menu += f"{num}️⃣ {label} ({count:,} nomor)\n"
        
        menu += "\n📎 *Atau kirim file CSV* untuk custom list\n"
        menu += "📋 Format CSV: kolom 'phone' atau 'nomor'\n"
        
        return menu
