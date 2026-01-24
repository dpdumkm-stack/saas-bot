from datetime import datetime
from app.extensions import db

class Toko(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    session_name = db.Column(db.String(50), unique=True, index=True)
    nama = db.Column(db.String(100))
    admin_name = db.Column(db.String(50), default="Admin")
    kategori = db.Column(db.String(20), default="umum")
    status_active = db.Column(db.Boolean, default=False)
    status_buka = db.Column(db.Boolean, default=True)
    remote_token = db.Column(db.String(50), unique=True)
    remote_pin = db.Column(db.String(10), default="1234")
    payment_bank = db.Column(db.String(200), default="BCA (Belum Diset)")
    payment_qris = db.Column(db.String(500), default="https://via.placeholder.com/300")
    payment_qris = db.Column(db.String(500), default="https://via.placeholder.com/300")
    timezone = db.Column(db.String(50), default="Asia/Jakarta") # WIB, WITA, WIT
    last_reset = db.Column(db.String(20))
    
    # Knowledge Base (RAG)
    knowledge_base_file_id = db.Column(db.String(100), nullable=True)
    knowledge_base_name = db.Column(db.String(100), nullable=True)
    
    admins = db.Column(db.Text, default="[]") 
    created_at = db.Column(db.DateTime, default=datetime.now)
    menus = db.relationship('Menu', backref='toko', lazy=True)
    customers = db.relationship('Customer', backref='toko', lazy=True)
    chats = db.relationship('ChatLog', backref='toko', lazy=True)
    transactions = db.relationship('Transaction', backref='toko', lazy=True)

    def format_menu(self):
        """Format daftar menu untuk prompt AI"""
        if not self.menus:
            return "- Belum ada menu yang terdaftar."
        
        return "\n".join([f"- {m.item}: Rp{m.harga:,} (Stok: {m.stok})" for m in self.menus])

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'), index=True)
    item = db.Column(db.String(100))
    harga = db.Column(db.Integer)
    stok = db.Column(db.Integer, default=-1)
    category = db.Column(db.String(50), default="Umum") # NEW
    image_url = db.Column(db.String(500), nullable=True) # NEW
    description = db.Column(db.Text, nullable=True) # NEW

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'), index=True)
    nomor_hp = db.Column(db.String(50))
    is_muted_until = db.Column(db.DateTime, nullable=True)
    order_status = db.Column(db.String(20), default="NONE")
    current_bill = db.Column(db.Integer, default=0)
    
    # Sales Engine Fields
    last_interaction = db.Column(db.DateTime, default=datetime.now)
    followup_status = db.Column(db.String(20), default="NONE")
    last_context = db.Column(db.Text, default="")
    
    # Broadcast flow state
    flow_state = db.Column(db.String(50), nullable=True)
    # Context Aware Broadcast & Safety Fuse (v3.9.7)
    last_broadcast_msg = db.Column(db.Text, nullable=True)
    last_broadcast_at = db.Column(db.DateTime, nullable=True)
    broadcast_reply_count = db.Column(db.Integer, default=0)

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'), index=True)
    customer_hp = db.Column(db.String(50), index=True)
    role = db.Column(db.String(10))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Transaction(db.Model):
    """
    Transaction/Order model for tracking customer purchases and payment verification.
    Enhanced with AI payment verification fields for order matching.
    """
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'), index=True)
    customer_hp = db.Column(db.String(50), index=True)
    nominal = db.Column(db.Integer)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, PAID, CANCELLED, EXPIRED
    tanggal = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Order Matching Fields (ADD-ONLY Migration)
    order_id = db.Column(db.String(50), unique=True, nullable=True, index=True)  # Unique order reference
    items_json = db.Column(db.Text, nullable=True)  # JSON list of ordered items
    
    # Payment Verification Fields
    payment_proof_url = db.Column(db.String(500), nullable=True)  # URL to uploaded proof
    verification_status = db.Column(db.String(20), default='UNVERIFIED')  # UNVERIFIED, VERIFIED, REJECTED, MANUAL_REVIEW
    confidence_score = db.Column(db.Integer, nullable=True)  # AI confidence 0-100
    detected_amount = db.Column(db.Integer, nullable=True)  # Amount detected by AI OCR
    detected_bank = db.Column(db.String(50), nullable=True)  # Bank detected by AI
    
    # Verification Metadata
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.String(20), nullable=True)  # 'AI', 'MANUAL', or admin phone
    verification_notes = db.Column(db.Text, nullable=True)  # Notes from merchant
    fraud_hints_json = db.Column(db.Text, nullable=True)  # JSON list of fraud hints
    
    # Timestamps
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class BroadcastJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50))
    pesan = db.Column(db.Text)
    target_list = db.Column(db.Text)
    processed_count = db.Column(db.Integer, default=0) # Total numbers attempted
    success_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    skipped_count = db.Column(db.Integer, default=0) # Blacklisted/Muted
    status = db.Column(db.String(20), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    locked_until = db.Column(db.DateTime, nullable=True)

class SystemConfig(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200))

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(50), index=True, unique=True)
    name = db.Column(db.String(100), default="Unknown")
    admin_name = db.Column(db.String(50), default="Admin")
    category = db.Column(db.String(50)) # F&B, Jasa, etc.
    
    # Status Flow
    status = db.Column(db.String(20), default="DRAFT") # DRAFT -> TRIAL -> ACTIVE (Paid) -> EXPIRED
    tier = db.Column(db.String(20), default="STARTER") # STARTER, BUSINESS, PRO
    
    # Registration State
    step = db.Column(db.Integer, default=0) # 1=AskName, 2=AskCategory
    
    # Payment Info
    order_id = db.Column(db.String(100), unique=True, nullable=True)
    payment_status = db.Column(db.String(20), default="unpaid") # unpaid, paid, expired
    payment_url = db.Column(db.String(500), nullable=True)
    
    # Cancellation & Grace Period
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.String(500), nullable=True)
    grace_period_ends = db.Column(db.DateTime, nullable=True)
    
    # Lifecycle Dates
    active_at = db.Column(db.DateTime, nullable=True)
    expired_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


# ============================================================
# Phase 8: Marketing Analytics & Automation Models
# ============================================================

class BroadcastBlacklist(db.Model):
    """
    Opt-out management for broadcast recipients
    Users can unsubscribe by sending STOP and resubscribe with START
    """
    __tablename__ = 'broadcast_blacklist'
    
    phone_number = db.Column(db.String(20), primary_key=True)
    opted_out_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    reason = db.Column(db.String(100), default='user_request')  # user_request, manual, bounce, spam
    can_resubscribe = db.Column(db.Boolean, default=True)
    notes = db.Column(db.String(500))
    
    def __repr__(self):
        return f'<BroadcastBlacklist {self.phone_number}>'


class ScheduledBroadcast(db.Model):
    """
    Scheduled and recurring broadcasts
    Executed by cron job at specified times
    """
    __tablename__ = 'scheduled_broadcast'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False, index=True)
    recurrence = db.Column(db.String(20), default='once')  # once, daily, weekly, monthly
    message = db.Column(db.Text, nullable=False)
    
    # Target configuration
    target_type = db.Column(db.String(20), nullable=False)  # segment, csv
    target_segment = db.Column(db.String(50))  # active, trial, etc.
    target_list = db.Column(db.Text)  # JSON list of phone numbers (NEW)
    target_csv = db.Column(db.Text)  # JSON array of targets
    
    # Status tracking
    status = db.Column(db.String(20), default='pending', index=True)  # pending, executed, failed, cancelled
    last_executed = db.Column(db.DateTime)
    execution_count = db.Column(db.Integer, default=0)
    
    # Metadata
    created_by = db.Column(db.String(20), default='SUPERADMIN')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<ScheduledBroadcast {self.name}>'


class BroadcastTemplate(db.Model):
    """
    Reusable message templates for broadcasts
    """
    __tablename__ = 'broadcast_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='other')  # promo, announcement, reminder, other
    
    # Usage tracking
    use_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)
    
    # Metadata
    created_by = db.Column(db.String(20), default='SUPERADMIN')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
class AuditLog(db.Model):
    """
    Audit trail for sensitive system changes
    """
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), index=True)
    admin_hp = db.Column(db.String(20))
    action = db.Column(db.String(50)) # e.g., UPDATE_PRICE, DELETE_CUSTOMER, PANIC_TOGGLE
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.String(50))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.admin_hp}>'
