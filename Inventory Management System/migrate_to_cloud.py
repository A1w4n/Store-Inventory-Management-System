"""
migrate_to_cloud.py
────────────────────
One-shot migration: copies every row from your local inventory.db
into the Supabase PostgreSQL database.

Usage:
    1. Set DATABASE_URL in your environment (copy from Supabase → Settings → Database → Connection string → Python):
         export DATABASE_URL="postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres"

    2. Run:
         python migrate_to_cloud.py

Safe to re-run — uses ON CONFLICT DO NOTHING so existing rows are skipped.
"""

import os
import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv  # add this

load_dotenv()  # add this — reads .env file automatically

SQLITE_DB = "c:/Users/orens/OneDrive/Documents/Coding Python/Inventory Management System/inventory.db"

def migrate():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        print("        Export it first:")
        print('        export DATABASE_URL="postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres"')
        sys.exit(1)

    if not Path(SQLITE_DB).exists():
        print(f"[ERROR] Local database '{SQLITE_DB}' not found. Run setup_database.py first.")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("[ERROR] psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)

    print(f"[Migration] Connecting to SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row

    url = database_url
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url += sep + "sslmode=require"

    print(f"[Migration] Connecting to Supabase PostgreSQL...")
    pg_conn = psycopg2.connect(url)
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()

    # ── Ensure tables exist ───────────────────────────────────────────────────
    # Create tables directly using psycopg2
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category_id INTEGER,
            description TEXT,
            price REAL NOT NULL,
            quantity INTEGER DEFAULT 0,
            low_stock_threshold INTEGER DEFAULT 10,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            previous_quantity INTEGER,
            new_quantity INTEGER,
            notes TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            quantity_sold INTEGER NOT NULL,
            sale_price REAL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER
        );
    """)
    pg_conn.commit()
    print("[Migration] Tables verified/created in Supabase.\n")

    totals = {}

    # ── Users ──────────────────────────────────────────────────────────────────
    rows = sqlite_conn.execute("SELECT * FROM users").fetchall()
    for r in rows:
        pg_cur.execute("""
            INSERT INTO users (id, username, password_hash, email, created_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, (r["id"], r["username"], r["password_hash"],
              r["email"], r["created_at"], bool(r["is_active"])))
    pg_conn.commit()
    totals["users"] = len(rows)
    print(f"  ✓ Users:      {len(rows)}")

    # ── Categories ────────────────────────────────────────────────────────────
    rows = sqlite_conn.execute("SELECT * FROM categories").fetchall()
    for r in rows:
        pg_cur.execute("""
            INSERT INTO categories (id, name, description, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
        """, (r["id"], r["name"], r["description"], r["created_at"]))
    pg_conn.commit()
    totals["categories"] = len(rows)
    print(f"  ✓ Categories: {len(rows)}")

    # ── Items ─────────────────────────────────────────────────────────────────
    rows = sqlite_conn.execute("SELECT * FROM items").fetchall()
    for r in rows:
        pg_cur.execute("""
            INSERT INTO items (id, name, sku, category_id, description, price,
                               quantity, low_stock_threshold, image_path,
                               created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (r["id"], r["name"], r["sku"], r["category_id"], r["description"],
              r["price"], r["quantity"], r["low_stock_threshold"],
              r["image_path"], r["created_at"], r["updated_at"]))
    pg_conn.commit()
    totals["items"] = len(rows)
    print(f"  ✓ Items:      {len(rows)}")

    # ── Inventory movements ───────────────────────────────────────────────────
    rows = sqlite_conn.execute("SELECT * FROM inventory_movements").fetchall()
    for r in rows:
        pg_cur.execute("""
            INSERT INTO inventory_movements
            (id, item_id, movement_type, quantity, previous_quantity,
             new_quantity, notes, user_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (r["id"], r["item_id"], r["movement_type"], r["quantity"],
              r["previous_quantity"], r["new_quantity"], r["notes"],
              r["user_id"], r["created_at"]))
    pg_conn.commit()
    totals["movements"] = len(rows)
    print(f"  ✓ Movements:  {len(rows)}")

    # ── Sales ─────────────────────────────────────────────────────────────────
    rows = sqlite_conn.execute("SELECT * FROM sales").fetchall()
    for r in rows:
        pg_cur.execute("""
            INSERT INTO sales (id, item_id, quantity_sold, sale_price, sale_date, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (r["id"], r["item_id"], r["quantity_sold"],
              r["sale_price"], r["sale_date"], r["user_id"]))
    pg_conn.commit()
    totals["sales"] = len(rows)
    print(f"  ✓ Sales:      {len(rows)}")

    # ── Sync sequences so future INSERTs don't conflict ───────────────────────
    for table in ("users", "categories", "items", "inventory_movements", "sales"):
        pg_cur.execute(f"""
            SELECT setval(pg_get_serial_sequence('{table}', 'id'),
                          COALESCE(MAX(id), 1))
            FROM {table}
        """)
    pg_conn.commit()

    sqlite_conn.close()
    pg_conn.close()

    print("\n" + "=" * 50)
    print("✅  Migration complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("  1. Push the cloud_deploy/ folder to a GitHub repo")
    print("  2. Deploy on Railway (see DEPLOYMENT_GUIDE.md)")
    print("  3. Set DATABASE_URL in Railway environment variables")
    print("  4. On your desktop, set DATABASE_URL to point to Supabase")
    print("     so the desktop app also uses the cloud database.")

if __name__ == "__main__":
    migrate()
