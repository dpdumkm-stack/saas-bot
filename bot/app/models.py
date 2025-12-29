from datetime import datetime
from app.extensions import db

class Toko(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    session_name = db.Column(db.String(50), unique=True, index=True)
    nama = db.Column(db.String(100))
    kategori = db.Column(db.String(20), default="umum")
    status_active = db.Column(db.Boolean, default=False)
    status_buka = db.Column(db.Boolean, default=True)
    remote_token = db.Column(db.String(50), unique=True)
    remote_pin = db.Column(db.String(10), default="1234")
    payment_bank = db.Column(db.String(200), default="BCA (Belum Diset)")
    payment_qris = db.Column(db.String(500), default="https://via.placeholder.com/300")
    payment_qris = db.Column(db.String(500), default="https://via.placeholder.com/300")
    last_reset = db.Column(db.String(20))
    
    # Knowledge Base (RAG)
    knowledge_base_file_id = db.Column(db.String(100), nullable=True)
    knowledge_base_name = db.Column(db.String(100), nullable=True)
    
    # Shipping
    shipping_origin_id = db.Column(db.Integer, nullable=True) # RajaOngkir City ID
    shipping_couriers = db.Column(db.String(50), default="jne") # jne,tiki,pos
    setup_step = db.Column(db.String(20), default="NONE") # NONE, LOC_SEARCH
    
    admins = db.Column(db.Text, default="[]") 
    created_at = db.Column(db.DateTime, default=datetime.now)
    menus = db.relationship('Menu', backref='toko', lazy=True)
    customers = db.relationship('Customer', backref='toko', lazy=True)
    chats = db.relationship('ChatLog', backref='toko', lazy=True)
    transactions = db.relationship('Transaction', backref='toko', lazy=True)

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'), index=True)
    item = db.Column(db.String(100))
    harga = db.Column(db.Integer)
    stok = db.Column(db.Integer, default=-1)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'), index=True)
    nomor_hp = db.Column(db.String(50))
    is_muted_until = db.Column(db.DateTime, nullable=True)
    order_status = db.Column(db.String(20), default="NONE")
    current_bill = db.Column(db.Integer, default=0)
    
    # Sales Engine Fields
    last_interaction = db.Column(db.DateTime, default=datetime.now)
    followup_status = db.Column(db.String(20), default="NONE") # NONE, PENDING, SENT
    last_context = db.Column(db.Text, default="")

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'), index=True)
    customer_hp = db.Column(db.String(50), index=True)
    role = db.Column(db.String(10))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50), db.ForeignKey('toko.id'))
    customer_hp = db.Column(db.String(50))
    nominal = db.Column(db.Integer)
    status = db.Column(db.String(20))
    tanggal = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now)

class BroadcastJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    toko_id = db.Column(db.String(50))
    pesan = db.Column(db.Text)
    target_list = db.Column(db.Text)
    processed_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="PENDING")

class SystemConfig(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200))

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(50), index=True, unique=True)
    name = db.Column(db.String(100), default="Unknown")
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
    
    expired_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
