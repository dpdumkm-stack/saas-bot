#!/usr/bin/env python3
"""
Database Migration Script
Adds missing columns to existing tables
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    exit(1)

# Fix postgres:// to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("=" * 50)
print("Database Migration Script")
print("=" * 50)
print()

engine = create_engine(DATABASE_URL)

def column_exists(table_name, column_name):
    """Check if column exists in table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate():
    with engine.connect() as conn:
        print("[1/3] Checking Customer table...")
        
        # Check and add last_interaction
        if not column_exists('customer', 'last_interaction'):
            print("  Adding column: last_interaction")
            conn.execute(text("""
                ALTER TABLE customer 
                ADD COLUMN last_interaction TIMESTAMP DEFAULT NOW()
            """))
            conn.commit()
            print("  ✓ Added last_interaction")
        else:
            print("  ✓ last_interaction already exists")
        
        # Check and add followup_status
        if not column_exists('customer', 'followup_status'):
            print("  Adding column: followup_status")
            conn.execute(text("""
                ALTER TABLE customer 
                ADD COLUMN followup_status VARCHAR(20) DEFAULT 'NONE'
            """))
            conn.commit()
            print("  ✓ Added followup_status")
        else:
            print("  ✓ followup_status already exists")
        
        # Check and add last_context
        if not column_exists('customer', 'last_context'):
            print("  Adding column: last_context")
            conn.execute(text("""
                ALTER TABLE customer 
                ADD COLUMN last_context TEXT DEFAULT ''
            """))
            conn.commit()
            print("  ✓ Added last_context")
        else:
            print("  ✓ last_context already exists")
        
        print()
        print("[2/3] Checking Toko table...")
        
        # Check knowledge base columns
        if not column_exists('toko', 'knowledge_base_file_id'):
            print("  Adding column: knowledge_base_file_id")
            conn.execute(text("""
                ALTER TABLE toko 
                ADD COLUMN knowledge_base_file_id VARCHAR(100)
            """))
            conn.commit()
            print("  ✓ Added knowledge_base_file_id")
        else:
            print("  ✓ knowledge_base_file_id already exists")
        
        if not column_exists('toko', 'knowledge_base_name'):
            print("  Adding column: knowledge_base_name")
            conn.execute(text("""
                ALTER TABLE toko 
                ADD COLUMN knowledge_base_name VARCHAR(100)
            """))
            conn.commit()
            print("  ✓ Added knowledge_base_name")
        else:
            print("  ✓ knowledge_base_name already exists")
        
        # Check shipping columns
        if not column_exists('toko', 'shipping_origin_id'):
            print("  Adding column: shipping_origin_id")
            conn.execute(text("""
                ALTER TABLE toko 
                ADD COLUMN shipping_origin_id INTEGER
            """))
            conn.commit()
            print("  ✓ Added shipping_origin_id")
        else:
            print("  ✓ shipping_origin_id already exists")
        
        if not column_exists('toko', 'shipping_couriers'):
            print("  Adding column: shipping_couriers")
            conn.execute(text("""
                ALTER TABLE toko 
                ADD COLUMN shipping_couriers VARCHAR(50) DEFAULT 'jne'
            """))
            conn.commit()
            print("  ✓ Added shipping_couriers")
        else:
            print("  ✓ shipping_couriers already exists")
        
        if not column_exists('toko', 'setup_step'):
            print("  Adding column: setup_step")
            conn.execute(text("""
                ALTER TABLE toko 
                ADD COLUMN setup_step VARCHAR(20) DEFAULT 'NONE'
            """))
            conn.commit()
            print("  ✓ Added setup_step")
        else:
            print("  ✓ setup_step already exists")
        
        print()
        print("[3/3] Verifying changes...")
        
        # Verify customer columns
        customer_cols = [col['name'] for col in inspect(engine).get_columns('customer')]
        print(f"  Customer columns: {len(customer_cols)}")
        print(f"    {', '.join(customer_cols)}")
        
        print()
        print("=" * 50)
        print("Migration Complete!")
        print("=" * 50)

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
