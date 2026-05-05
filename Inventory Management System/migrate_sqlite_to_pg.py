"""
Migration script: Transfer data from SQLite to PostgreSQL
Run this ONCE to migrate your existing inventory data.

Usage:
    python migrate_sqlite_to_pg.py
"""

import sqlite3
import psycopg2
from datetime import datetime
from pathlib import Path

# SQLite database path
SQLITE_DB = "inventory.db"

# PostgreSQL config (must match database_config.py)
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'inventory_db',
    'user': 'inventory_user',
    'password': 'your_secure_password_here',  # CHANGE THIS!
}


def migrate_data():
    """Migrate all data from SQLite to PostgreSQL."""
    
    print("[MIGRATION] Starting data transfer from SQLite to PostgreSQL...\n")
    
    # Check SQLite database exists
    if not Path(SQLITE_DB).exists():
        print(f"[ERROR] SQLite database '{SQLITE_DB}' not found!")
        return False
    
    try:
        # Connect to both databases
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_cursor = pg_conn.cursor()
        
        print("[✓] Connected to both databases\n")
        
        # ── Migrate Users ────────────────────────────────────────────────────
        print("Migrating users...")
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        
        for user in users:
            pg_cursor.execute("""
                INSERT INTO users (id, username, password_hash, email, created_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """, (user['id'], user['username'], user['password_hash'], 
                  user['email'], user['created_at'], user['is_active']))
        
        pg_conn.commit()
        print(f"  ✓ Migrated {len(users)} users\n")
        
        # ── Migrate Categories ───────────────────────────────────────────────
        print("Migrating categories...")
        sqlite_cursor.execute("SELECT * FROM categories")
        categories = sqlite_cursor.fetchall()
        
        for cat in categories:
            pg_cursor.execute("""
                INSERT INTO categories (id, name, description, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (cat['id'], cat['name'], cat['description'], cat['created_at']))
        
        pg_conn.commit()
        print(f"  ✓ Migrated {len(categories)} categories\n")
        
        # ── Migrate Items ────────────────────────────────────────────────────
        print("Migrating items...")
        sqlite_cursor.execute("SELECT * FROM items")
        items = sqlite_cursor.fetchall()
        
        for item in items:
            pg_cursor.execute("""
                INSERT INTO items (id, name, sku, category_id, description, price, 
                                   quantity, low_stock_threshold, image_path, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (item['id'], item['name'], item['sku'], item['category_id'],
                  item['description'], item['price'], item['quantity'],
                  item['low_stock_threshold'], item['image_path'],
                  item['created_at'], item['updated_at']))
        
        pg_conn.commit()
        print(f"  ✓ Migrated {len(items)} items\n")
        
        # ── Migrate Inventory Movements ──────────────────────────────────────
        print("Migrating inventory movements...")
        sqlite_cursor.execute("SELECT * FROM inventory_movements")
        movements = sqlite_cursor.fetchall()
        
        for mov in movements:
            pg_cursor.execute("""
                INSERT INTO inventory_movements (id, item_id, movement_type, quantity,
                                                 previous_quantity, new_quantity, notes, user_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (mov['id'], mov['item_id'], mov['movement_type'], mov['quantity'],
                  mov['previous_quantity'], mov['new_quantity'], mov['notes'],
                  mov['user_id'], mov['created_at']))
        
        pg_conn.commit()
        print(f"  ✓ Migrated {len(movements)} inventory movements\n")
        
        # ── Migrate Sales ────────────────────────────────────────────────────
        print("Migrating sales...")
        sqlite_cursor.execute("SELECT * FROM sales")
        sales = sqlite_cursor.fetchall()
        
        for sale in sales:
            pg_cursor.execute("""
                INSERT INTO sales (id, item_id, quantity_sold, sale_price, sale_date, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (sale['id'], sale['item_id'], sale['quantity_sold'], sale['sale_price'],
                  sale['sale_date'], sale['user_id']))
        
        pg_conn.commit()
        print(f"  ✓ Migrated {len(sales)} sales\n")
        
        print("=" * 60)
        print("[✓] MIGRATION COMPLETE!")
        print("=" * 60)
        print(f"\nData Summary:")
        print(f"  • Users:      {len(users)}")
        print(f"  • Categories: {len(categories)}")
        print(f"  • Items:      {len(items)}")
        print(f"  • Movements:  {len(movements)}")
        print(f"  • Sales:      {len(sales)}")
        print(f"\nNext steps:")
        print(f"  1. Update database_config.py with your PostgreSQL server details")
        print(f"  2. Update imports in main.py and web_server.py")
        print(f"  3. Install psycopg2: pip install psycopg2")
        
        sqlite_conn.close()
        pg_conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"\n[ERROR] PostgreSQL error: {e}")
        print(f"\nMake sure your PostgreSQL server is running and credentials are correct!")
        return False
    except sqlite3.Error as e:
        print(f"\n[ERROR] SQLite error: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False


if __name__ == "__main__":
    success = migrate_data()
    exit(0 if success else 1)
