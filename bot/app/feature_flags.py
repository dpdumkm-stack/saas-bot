"""
Feature Flags for Broadcast System
Allows enabling/disabling features without redeployment
"""
import os

class FeatureFlags:
    """Centralized feature flag system"""
    
    # Phase 7: Broadcast Features
    FEATURE_BROADCAST_ENABLED = os.getenv('FEATURE_BROADCAST_ENABLED', 'false').lower() == 'true'
    FEATURE_BROADCAST_CSV = os.getenv('FEATURE_BROADCAST_CSV', 'false').lower() == 'true'
    FEATURE_BROADCAST_SEGMENTS = os.getenv('FEATURE_BROADCAST_SEGMENTS', 'false').lower() == 'true'
    
    # Phase 8: Marketing Analytics & Automation
    FEATURE_OPT_OUT = os.getenv('FEATURE_OPT_OUT', 'false').lower() == 'true'
    FEATURE_SCHEDULED = os.getenv('FEATURE_SCHEDULED', 'false').lower() == 'true'
    FEATURE_TEMPLATES = os.getenv('FEATURE_TEMPLATES', 'false').lower() == 'true'
    FEATURE_ANALYTICS = os.getenv('FEATURE_ANALYTICS', 'false').lower() == 'true'
    FEATURE_ALERTS = os.getenv('FEATURE_ALERTS', 'false').lower() == 'true'
    
    # Safety Limits
    BROADCAST_MAX_TARGETS = int(os.getenv('BROADCAST_MAX_TARGETS', '500'))
    BROADCAST_DAILY_LIMIT = int(os.getenv('BROADCAST_DAILY_LIMIT', '1000'))
    
    @staticmethod
    def is_broadcast_enabled():
        return FeatureFlags.FEATURE_BROADCAST_ENABLED
    
    @staticmethod
    def is_opt_out_enabled():
        return FeatureFlags.FEATURE_OPT_OUT
    
    @staticmethod
    def is_scheduled_enabled():
        return FeatureFlags.FEATURE_SCHEDULED
    
    @staticmethod
    def is_templates_enabled():
        return FeatureFlags.FEATURE_TEMPLATES
    
    @staticmethod
    def is_analytics_enabled():
        return FeatureFlags.FEATURE_ANALYTICS
    
    @staticmethod
    def is_alerts_enabled():
        return FeatureFlags.FEATURE_ALERTS
    
    @classmethod
    def get_status(cls):
        """Get status of all feature flags"""
        return {
            'broadcast_csv': cls.BROADCAST_CSV_UPLOAD,
            'broadcast_segments': cls.BROADCAST_DB_SEGMENTS,
            'broadcast_enabled': cls.BROADCAST_ENABLED,
            'max_targets': cls.BROADCAST_MAX_TARGETS,
            'daily_limit': cls.BROADCAST_DAILY_LIMIT,
        }
