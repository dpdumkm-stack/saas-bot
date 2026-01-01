"""
One-time database migration via direct SQL
Run this locally to fix database schema
"""
import os
import sys

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv('bot/.env')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    sys.exit(1)

# Fix postgres:// to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("Connecting to database...")
engine = create_engine(DATABASE_URL)

print("\nRunning migrations...")

with engine.connect() as conn:
    inspector = inspect(engine)
    
    # Customer table migrations
    customer_cols = [col['name'] for col in inspector.get_columns('customer')]
    
    migrations = []
    
    if 'last_interaction' not in customer_cols:
        migrations.append(("customer", "last_interaction", "ALTER TABLE customer ADD COLUMN last_interaction TIMESTAMP DEFAULT NOW()"))
    
    if 'followup_status' not in customer_cols:
        migrations.append(("customer", "followup_status", "ALTER TABLE customer ADD COLUMN followup_status VARCHAR(20) DEFAULT 'NONE'"))
    
    if 'last_context' not in customer_cols:
        migrations.append(("customer", "last_context", "ALTER TABLE customer ADD COLUMN last_context TEXT DEFAULT ''"))
    
    # Toko table migrations
    toko_cols = [col['name'] for col in inspector.get_columns('toko')]
    
    if 'knowledge_base_file_id' not in toko_cols:
        migrations.append(("toko", "knowledge_base_file_id", "ALTER TABLE toko ADD COLUMN knowledge_base_file_id VARCHAR(100)"))
    
    if 'knowledge_base_name' not in toko_cols:
        migrations.append(("toko", "knowledge_base_name", "ALTER TABLE toko ADD COLUMN knowledge_base_name VARCHAR(100)"))
    
    if 'shipping_origin_id' not in toko_cols:
        migrations.append(("toko", "shipping_origin_id", "ALTER TABLE toko ADD COLUMN shipping_origin_id INTEGER"))
    
    if 'shipping_couriers' not in toko_cols:
        migrations.append(("toko", "shipping_couriers", "ALTER TABLE toko ADD COLUMN shipping_couriers VARCHAR(50) DEFAULT 'jne'"))
    
    if 'setup_step' not in toko_cols:
        migrations.append(("toko", "setup_step", "ALTER TABLE toko ADD COLUMN setup_step VARCHAR(20) DEFAULT 'NONE'"))
    
    if not migrations:
        print("\n✓ Database schema is up to date!")
    else:
        print(f"\n Found {len(migrations)} missing columns:")
        for table, column, sql in migrations:
            print(f"  - {table}.{column}")
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"    ✓ Added")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        print("\n✓ Migrations completed!")

print("\nDone.")
