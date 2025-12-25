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
    last_reset = db.Column(db.String(20))
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
