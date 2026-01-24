-- Neon Database Schema for Wali AI
-- Generated from SQLAlchemy models
-- Target: postgresql://neondb_owner@ep-gentle-poetry-a1c4mc7x-pooler.ap-southeast-1.aws.neon.tech/neondb

-- Drop tables if exist (for clean setup)
DROP TABLE IF EXISTS broadcast_job CASCADE;
DROP TABLE IF EXISTS transaction CASCADE;
DROP TABLE IF EXISTS chat_log CASCADE;
DROP TABLE IF EXISTS customer CASCADE;
DROP TABLE IF EXISTS menu CASCADE;
DROP TABLE IF EXISTS toko CASCADE;
DROP TABLE IF EXISTS subscription CASCADE;
DROP TABLE IF EXISTS system_config CASCADE;

-- Create Subscription table (parent)
CREATE TABLE subscription (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) DEFAULT 'Unknown',
    admin_name VARCHAR(50) DEFAULT 'Admin',
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'DRAFT',
    tier VARCHAR(20) DEFAULT 'STARTER',
    step INTEGER DEFAULT 0,
    order_id VARCHAR(100) UNIQUE,
    payment_status VARCHAR(20) DEFAULT 'unpaid',
    payment_url VARCHAR(500),
    expired_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscription_phone ON subscription(phone_number);

-- Create Toko table (parent)
CREATE TABLE toko (
    id VARCHAR(50) PRIMARY KEY,
    session_name VARCHAR(50) UNIQUE NOT NULL,
    nama VARCHAR(100),
    admin_name VARCHAR(50) DEFAULT 'Admin',
    kategori VARCHAR(20) DEFAULT 'umum',
    status_active BOOLEAN DEFAULT FALSE,
    status_buka BOOLEAN DEFAULT TRUE,
    remote_token VARCHAR(50) UNIQUE,
    remote_pin VARCHAR(10) DEFAULT '1234',
    payment_bank VARCHAR(200) DEFAULT 'BCA (Belum Diset)',
    payment_qris VARCHAR(500) DEFAULT 'https://via.placeholder.com/300',
    last_reset VARCHAR(20),
    knowledge_base_file_id VARCHAR(100),
    knowledge_base_name VARCHAR(100),
    admins TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_toko_session ON toko(session_name);

-- Create Menu table (child of toko)
CREATE TABLE menu (
    id SERIAL PRIMARY KEY,
    toko_id VARCHAR(50) REFERENCES toko(id) ON DELETE CASCADE,
    item VARCHAR(100),
    harga INTEGER,
    stok INTEGER DEFAULT -1
);

CREATE INDEX idx_menu_toko ON menu(toko_id);

-- Create Customer table (child of toko)
CREATE TABLE customer (
    id SERIAL PRIMARY KEY,
    toko_id VARCHAR(50) REFERENCES toko(id) ON DELETE CASCADE,
    nomor_hp VARCHAR(50),
    is_muted_until TIMESTAMP,
    order_status VARCHAR(20) DEFAULT 'NONE',
    current_bill INTEGER DEFAULT 0,
    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    followup_status VARCHAR(20) DEFAULT 'NONE',
    last_context TEXT DEFAULT ''
);

CREATE INDEX idx_customer_toko ON customer(toko_id);

-- Create ChatLog table (child of toko)
CREATE TABLE chat_log (
    id SERIAL PRIMARY KEY,
    toko_id VARCHAR(50) REFERENCES toko(id) ON DELETE CASCADE,
    customer_hp VARCHAR(50),
    role VARCHAR(10),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chatlog_toko ON chat_log(toko_id);
CREATE INDEX idx_chatlog_customer ON chat_log(customer_hp);

-- Create Transaction table (child of toko)
CREATE TABLE transaction (
    id SERIAL PRIMARY KEY,
    toko_id VARCHAR(50) REFERENCES toko(id) ON DELETE CASCADE,
    customer_hp VARCHAR(50),
    nominal INTEGER,
    status VARCHAR(20),
    tanggal VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create BroadcastJob table
CREATE TABLE broadcast_job (
    id SERIAL PRIMARY KEY,
    toko_id VARCHAR(50),
    pesan TEXT,
    target_list TEXT,
    processed_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING'
);

-- Create SystemConfig table
CREATE TABLE system_config (
    key VARCHAR(50) PRIMARY KEY,
    value VARCHAR(200)
);

-- Verify tables created
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
