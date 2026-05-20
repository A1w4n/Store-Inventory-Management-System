"""
Unified Inventory Database Module
Supports both SQLite (local) and PostgreSQL (remote server)
Automatically selects based on configuration

Configuration:
    USE_LOCAL_SQLITE = True  → Uses local inventory.db
    USE_LOCAL_SQLITE = False → Uses remote PostgreSQL server

Usage:
    from database import InventoryDatabase
    db = InventoryDatabase()
    items = d
    b.get_all_items()
"""

import sqlite3
import hashlib
import psycopg2
from psycopg2 import pool, extras
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Customize Here
# ═══════════════════════════════════════════════════════════════════════════════

USE_LOCAL_SQLITE = False  # Set to False for PostgreSQL

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DB_CONFIG = {"dsn": DATABASE_URL}
else:
    DB_CONFIG = {
        "host":     "localhost",
        "port":     5432,
        "database": "inventory",
        "user":     "inventory_user",
        "password": "admin123",
    }

DEBUG_SQL = False

# ═══════════════════════════════════════════════════════════════════════════════
# COMMON INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class InventoryDatabase:
    """
    Unified wrapper that delegates to SQLiteDatabase or PostgreSQLDatabase
    based on the USE_LOCAL_SQLITE flag.
    All methods are forwarded to the active backend automatically.
    """
    def __init__(self, backend=None, db_path="inventory.db", pg_url=None):
        # Select backend: explicit arg > env flag
        use_sqlite = USE_LOCAL_SQLITE if backend is None else (backend == "sqlite")
        if use_sqlite:
            self._db = SQLiteDatabase(db_path=db_path)
        else:
            self._db = PostgreSQLDatabase()
        self.db_type = self._db.db_type

    def __getattr__(self, name):
        """Delegate any method call to the active backend."""
        return getattr(self._db, name)


# ═══════════════════════════════════════════════════════════════════════════════
# SQLITE IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

class SQLiteDatabase:
    """SQLite-based database for local development."""

    def __init__(self, db_path="inventory.db"):
        """Initialize SQLite database."""
        self.db_path = Path(db_path)
        self.connection = None
        self.db_type = "SQLite"
        self.init_db()
        print(f"[DB] Using SQLite database: {self.db_path}")

    def connect(self):
        """Create database connection."""
        self.connection = sqlite3.connect(
            str(self.db_path), 
            timeout=15, 
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.execute("PRAGMA busy_timeout=15000;")
        self.connection.execute("PRAGMA synchronous=NORMAL;")
        return self.connection

    def get_connection(self):
        """Return a SQLite connection suitable for use with a context manager."""
        return self.connect()

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def init_db(self):
        """Create all necessary tables."""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT UNIQUE,
                category_id INTEGER,
                description TEXT,
                price REAL NOT NULL,
                quantity INTEGER DEFAULT 0,
                low_stock_threshold INTEGER DEFAULT 10,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                previous_quantity INTEGER,
                new_quantity INTEGER,
                notes TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                quantity_sold INTEGER NOT NULL,
                sale_price REAL,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                FOREIGN KEY (item_id) REFERENCES items(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        self.disconnect()

    # ── USER OPERATIONS ──────────────────────────────────────────────────────

    def add_user(self, username, password, email=None):
        """Add a new user."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, email)
                VALUES (?, ?, ?)
            """, (username, self._hash_password(password), email))
            conn.commit()
            user_id = cursor.lastrowid
            self.disconnect()
            return user_id
        except sqlite3.IntegrityError:
            self.disconnect()
            return None

    def get_user_by_username(self, username):
        """Get user by username."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        self.disconnect()
        return user

    def verify_password(self, stored_hash, password):
        """Verify password."""
        return stored_hash == self._hash_password(password)

    @staticmethod
    def _hash_password(password):
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    # ── CATEGORY OPERATIONS ──────────────────────────────────────────────────

    def add_category(self, name, description=None):
        """Add a category."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO categories (name, description)
                VALUES (?, ?)
            """, (name, description))
            conn.commit()
            category_id = cursor.lastrowid
            self.disconnect()
            return category_id
        except sqlite3.IntegrityError:
            self.disconnect()
            return None

    def get_all_categories(self):
        """Get all categories."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        categories = cursor.fetchall()
        self.disconnect()
        return categories

    # ── ITEM OPERATIONS ──────────────────────────────────────────────────────

    def add_item(self, name, price, category_id=None, sku=None, description=None,
                 quantity=0, low_stock_threshold=10, image_path=None):
        """Add an item."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO items (name, sku, category_id, description, price,
                                   quantity, low_stock_threshold, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, sku, category_id, description, price, quantity,
                  low_stock_threshold, image_path))
            conn.commit()
            item_id = cursor.lastrowid
            self.disconnect()
            return item_id
        except sqlite3.IntegrityError as e:
            print(f"[DB ERROR] Failed to add item: {e}")
            print(f"[DB] Item details: name={name}, sku={sku}, price={price}")
            self.disconnect()
            return None
        except Exception as e:
            print(f"[DB ERROR] Unexpected error adding item: {e}")
            self.disconnect()
            return None

    def get_item(self, item_id):
        """Get item by ID."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        self.disconnect()
        return item

    def get_all_items(self):
        """Get all items."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, c.name as category_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            ORDER BY i.name
        """)
        items = cursor.fetchall()
        self.disconnect()
        return items

    def search_items(self, search_term):
        """Search items."""
        conn = self.connect()
        cursor = conn.cursor()
        search_pattern = f"%{search_term}%"
        cursor.execute("""
            SELECT i.*, c.name as category_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.name LIKE ? OR i.sku LIKE ?
            ORDER BY i.name
        """, (search_pattern, search_pattern))
        items = cursor.fetchall()
        self.disconnect()
        return items

    def update_item(self, item_id, **kwargs):
        """Update item."""
        conn = self.connect()
        cursor = conn.cursor()
        allowed_fields = {'name', 'price', 'description', 'category_id',
                         'low_stock_threshold', 'image_path'}
        fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not fields:
            self.disconnect()
            return False
        fields['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
        values = list(fields.values()) + [item_id]
        cursor.execute(f"UPDATE items SET {set_clause} WHERE id = ?", values)
        conn.commit()
        self.disconnect()
        return cursor.rowcount > 0

    def delete_item(self, item_id):
        """Delete item."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        self.disconnect()
        return cursor.rowcount > 0

    # ── INVENTORY OPERATIONS ─────────────────────────────────────────────────

    def update_quantity(self, item_id, new_quantity, movement_type, user_id=None, notes=None):
        """Update quantity."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM items WHERE id = ?", (item_id,))
        result = cursor.fetchone()
        if not result:
            self.disconnect()
            return False
        previous_quantity = result[0]
        cursor.execute("""
            UPDATE items SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_quantity, item_id))
        cursor.execute("""
            INSERT INTO inventory_movements
            (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_id, movement_type, abs(new_quantity - previous_quantity),
              previous_quantity, new_quantity, notes, user_id))
        conn.commit()
        self.disconnect()
        return True

    def get_low_stock_items(self):
        """Get low stock items."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, c.name as category_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.quantity <= i.low_stock_threshold
            ORDER BY i.quantity ASC
        """)
        items = cursor.fetchall()
        self.disconnect()
        return items

    def get_inventory_movements(self, item_id=None, limit=100):
        """Get inventory movements."""
        conn = self.connect()
        cursor = conn.cursor()
        if item_id:
            cursor.execute("""
                SELECT im.*, i.name as item_name, u.username
                FROM inventory_movements im
                JOIN items i ON im.item_id = i.id
                LEFT JOIN users u ON im.user_id = u.id
                WHERE im.item_id = ?
                ORDER BY im.created_at DESC
                LIMIT ?
            """, (item_id, limit))
        else:
            cursor.execute("""
                SELECT im.*, i.name as item_name, u.username
                FROM inventory_movements im
                JOIN items i ON im.item_id = i.id
                LEFT JOIN users u ON im.user_id = u.id
                ORDER BY im.created_at DESC
                LIMIT ?
            """, (limit,))
        movements = cursor.fetchall()
        self.disconnect()
        return movements

    # ── SALES OPERATIONS ─────────────────────────────────────────────────────

    def record_sale(self, item_id, quantity_sold, user_id=None, sale_price=None):
        """Record a sale."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT quantity, price FROM items WHERE id = ?", (item_id,))
            result = cursor.fetchone()
            if not result:
                conn.rollback()
                return False
            current_quantity, default_price = result
            sale_price = sale_price or default_price
            if current_quantity < quantity_sold:
                conn.rollback()
                return False
            new_quantity = current_quantity - quantity_sold
            cursor.execute("""
                INSERT INTO sales (item_id, quantity_sold, sale_price, user_id)
                VALUES (?, ?, ?, ?)
            """, (item_id, quantity_sold, sale_price, user_id))
            cursor.execute("""
                UPDATE items SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_quantity, item_id))
            cursor.execute("""
                INSERT INTO inventory_movements
                (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (item_id, "SALE", quantity_sold, current_quantity, new_quantity,
                  f"Sold {quantity_sold} units at Php {sale_price}", user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] record_sale failed: {e}")
            conn.rollback()
            return False
        finally:
            self.disconnect()

    def get_sales_history(self, item_id=None, limit=100):
        """Get sales history."""
        conn = self.connect()
        cursor = conn.cursor()
        if item_id:
            cursor.execute("""
                SELECT s.*, i.name as item_name, u.username
                FROM sales s
                JOIN items i ON s.item_id = i.id
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.item_id = ?
                ORDER BY s.sale_date DESC
                LIMIT ?
            """, (item_id, limit))
        else:
            cursor.execute("""
                SELECT s.*, i.name as item_name, u.username
                FROM sales s
                JOIN items i ON s.item_id = i.id
                LEFT JOIN users u ON s.user_id = u.id
                ORDER BY s.sale_date DESC
                LIMIT ?
            """, (limit,))
        sales = cursor.fetchall()
        self.disconnect()
        return sales

    def get_item_count_trend(self, days=7):
        """Get item count trend."""
        conn = self.connect()
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        previous_cutoff = (datetime.now() - timedelta(days=days*2)).isoformat()
        previous_end = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM items WHERE created_at >= ?", (cutoff_date,))
        current_items = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM items WHERE created_at >= ? AND created_at < ?
        """, (previous_cutoff, previous_end))
        previous_items = cursor.fetchone()[0]
        if previous_items == 0:
            trend = 0 if current_items == 0 else 100
        else:
            trend = ((current_items - previous_items) / previous_items) * 100
        self.disconnect()
        return trend

    def get_low_stock_status(self):
        """Get low stock status."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items WHERE quantity <= low_stock_threshold")
        low_stock_count = cursor.fetchone()[0]
        cursor.execute("SELECT AVG(low_stock_threshold) FROM items")
        avg_threshold = cursor.fetchone()[0] or 10
        self.disconnect()
        return low_stock_count, avg_threshold

    def get_sales_trend(self, days=7):
        """Get sales trend."""
        conn = self.connect()
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        previous_cutoff = (datetime.now() - timedelta(days=days*2)).isoformat()
        previous_end = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_sold), 0) FROM sales WHERE sale_date >= ?
        """, (cutoff_date,))
        current_sales = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
            WHERE sale_date >= ? AND sale_date < ?
        """, (previous_cutoff, previous_end))
        previous_sales = cursor.fetchone()[0]
        if previous_sales == 0:
            trend = 0 if current_sales == 0 else 100
        else:
            trend = ((current_sales - previous_sales) / previous_sales) * 100
        self.disconnect()
        return trend

    def get_best_seller(self, days=7):
        """Get best selling item.
        Returns: (id, name, price, quantity, image_path, total_sold)
        """
        conn = self.connect()
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT i.id, i.name, i.price, i.quantity, i.image_path,
                   SUM(s.quantity_sold) as total_sold
            FROM sales s
            JOIN items i ON s.item_id = i.id
            WHERE s.sale_date >= ?
            GROUP BY i.id, i.name, i.price, i.quantity, i.image_path
            ORDER BY total_sold DESC
            LIMIT 1
        """, (cutoff_date,))
        result = cursor.fetchone()
        self.disconnect()
        return result

    def get_dashboard_stats(self):
        """Get dashboard statistics."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Get total items
        cursor.execute("SELECT COUNT(*) FROM items")
        total_items = cursor.fetchone()[0]
        
        # Get low stock items
        cursor.execute("SELECT COUNT(*) FROM items WHERE quantity <= low_stock_threshold")
        low_stock_items = cursor.fetchone()[0]
        
        # Get units sold today
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
            WHERE DATE(sale_date) = ?
        """, (today,))
        units_sold_today = cursor.fetchone()[0]
        
        # Get total quantity in stock
        cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM items")
        total_quantity = cursor.fetchone()[0]
        
        # Get total inventory value
        cursor.execute("SELECT COALESCE(SUM(quantity * price), 0) FROM items")
        total_inventory_value = cursor.fetchone()[0]
        
        self.disconnect()
        return {
            'total_items': total_items,
            'low_stock_items': low_stock_items,
            'low_stock_count': low_stock_items,
            'units_sold_today': units_sold_today,
            'total_quantity': total_quantity,
            'total_inventory_value': total_inventory_value,
        }

    def get_items_added_per_day(self, days=7):
        """Get items added per day for the last days."""
        conn = self.connect()
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT strftime('%Y-%m-%d', created_at) as date, COUNT(*) as count
            FROM items
            WHERE created_at >= ? AND created_at IS NOT NULL
            GROUP BY strftime('%Y-%m-%d', created_at)
            ORDER BY date ASC
        """, (cutoff_date,))
        rows = cursor.fetchall()
        self.disconnect()
        return rows

    def get_saleability_increase(self, days=7):
        """Get saleability increase trend for best seller."""
        conn = self.connect()
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        previous_cutoff = (datetime.now() - timedelta(days=days*2)).isoformat()
        previous_end = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Get current period sales
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
            WHERE sale_date >= ?
        """, (cutoff_date,))
        current_sales = cursor.fetchone()[0]
        
        # Get previous period sales
        cursor.execute("""
            SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
            WHERE sale_date >= ? AND sale_date < ?
        """, (previous_cutoff, previous_end))
        previous_sales = cursor.fetchone()[0]
        
        # Calculate trend
        if previous_sales == 0:
            trend = 0 if current_sales == 0 else 100
        else:
            trend = ((current_sales - previous_sales) / previous_sales) * 100
        
        self.disconnect()
        return trend
    
    # Additional methods for inventory movements, sales history, etc. can be added here as needed.

    def create_table_if_not_exists(self, table_name, columns):
        """Create table if it doesn't exist with given columns."""
        conn = self.connect()
        cursor = conn.cursor()
        col_defs = ", ".join([f"{col} TEXT" for col in columns])
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {col_defs}
            )
        """)
        conn.commit()
        self.disconnect()

    def clear_table(self, table_name):
        """Clear all rows from a table."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name}")
        conn.commit()
        self.disconnect()

    def bulk_insert(self, table_name, columns, rows):
        """Bulk insert rows into table."""
        conn = self.connect()
        cursor = conn.cursor()
        placeholders = ", ".join(["?" for _ in columns])
        cursor.executemany(
            f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
            rows
        )
        conn.commit()
        self.disconnect()

# ═══════════════════════════════════════════════════════════════════════════════
# POSTGRESQL IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

class PostgreSQLDatabase:
    """PostgreSQL-based database for remote server access."""

    def __init__(self):
        """Initialize PostgreSQL database."""
        import psycopg2
        from psycopg2 import pool, extras
        self.psycopg2 = psycopg2
        self.extras = extras
        self.db_type = "PostgreSQL"
        
        try:
            if "dsn" in DB_CONFIG:
                self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1, maxconn=10,
                    dsn=DB_CONFIG['dsn']
                )
                print(f"[DB] Connected to PostgreSQL via DATABASE_URL")
            else:
                self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1, maxconn=10,
                    host=DB_CONFIG['host'],
                    port=DB_CONFIG['port'],
                    database=DB_CONFIG['database'],
                    user=DB_CONFIG['user'],
                    password=DB_CONFIG['password'],
                )
                print(f"[DB] Connected to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            self.init_db()
        except psycopg2.Error as e:
            print(f"[ERROR] Failed to connect to PostgreSQL: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get a connection from pool."""
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)

    def init_db(self):
        """Create all necessary tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE)
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL,
                    description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY, name TEXT NOT NULL, sku TEXT UNIQUE,
                    category_id INTEGER REFERENCES categories(id),
                    description TEXT, price REAL NOT NULL, quantity INTEGER DEFAULT 0,
                    low_stock_threshold INTEGER DEFAULT 10, image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id),
                    movement_type TEXT NOT NULL, quantity INTEGER NOT NULL,
                    previous_quantity INTEGER, new_quantity INTEGER, notes TEXT,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id SERIAL PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id),
                    quantity_sold INTEGER NOT NULL, sale_price REAL,
                    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER REFERENCES users(id))
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_sku ON items(sku)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_item ON sales(item_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movements_item ON inventory_movements(item_id)")
            conn.commit()

    def add_user(self, username, password, email=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""INSERT INTO users (username, password_hash, email)
                    VALUES (%s, %s, %s) RETURNING id""",
                    (username, self._hash_password(password), email))
                user_id = cursor.fetchone()[0]
                conn.commit()
                return user_id
            except self.psycopg2.IntegrityError:
                conn.rollback()
                return None

    def get_user_by_username(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()

    def verify_password(self, stored_hash, password):
        return stored_hash == self._hash_password(password)

    @staticmethod
    def _hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def add_category(self, name, description=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""INSERT INTO categories (name, description)
                    VALUES (%s, %s) RETURNING id""", (name, description))
                category_id = cursor.fetchone()[0]
                conn.commit()
                return category_id
            except self.psycopg2.IntegrityError:
                conn.rollback()
                return None

    def get_all_categories(self):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            cursor.execute("SELECT * FROM categories ORDER BY name")
            return cursor.fetchall()

    def add_item(self, name, price, category_id=None, sku=None, description=None,
                 quantity=0, low_stock_threshold=10, image_path=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""INSERT INTO items (name, sku, category_id, description, price,
                    quantity, low_stock_threshold, image_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (name, sku, category_id, description, price, quantity,
                     low_stock_threshold, image_path))
                item_id = cursor.fetchone()[0]
                conn.commit()
                return item_id
            except self.psycopg2.IntegrityError as e:
                print(f"[DB ERROR] Failed to add item: {e}")
                print(f"[DB] Item details: name={name}, sku={sku}, price={price}")
                conn.rollback()
                return None
            except Exception as e:
                print(f"[DB ERROR] Unexpected error adding item: {e}")
                conn.rollback()
                return None

    def get_item(self, item_id):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
            return cursor.fetchone()

    def get_all_items(self):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            cursor.execute("""SELECT i.*, c.name as category_name FROM items i
                LEFT JOIN categories c ON i.category_id = c.id ORDER BY i.name""")
            return cursor.fetchall()

    def search_items(self, search_term):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            search_pattern = f"%{search_term}%"
            cursor.execute("""SELECT i.*, c.name as category_name FROM items i
                LEFT JOIN categories c ON i.category_id = c.id
                WHERE i.name ILIKE %s OR i.sku ILIKE %s ORDER BY i.name""",
                (search_pattern, search_pattern))
            return cursor.fetchall()

    def update_item(self, item_id, **kwargs):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            allowed_fields = {'name', 'price', 'description', 'category_id',
                            'low_stock_threshold', 'image_path'}
            fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
            if not fields:
                return False
            fields['updated_at'] = datetime.now()
            set_clause = ", ".join([f"{k} = %s" for k in fields.keys()])
            values = list(fields.values()) + [item_id]
            cursor.execute(f"UPDATE items SET {set_clause} WHERE id = %s", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_item(self, item_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_quantity(self, item_id, new_quantity, movement_type, user_id=None, notes=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM items WHERE id = %s", (item_id,))
            result = cursor.fetchone()
            if not result:
                return False
            previous_quantity = result[0]
            cursor.execute("""UPDATE items SET quantity = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s""", (new_quantity, item_id))
            cursor.execute("""INSERT INTO inventory_movements
                (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (item_id, movement_type, abs(new_quantity - previous_quantity),
                 previous_quantity, new_quantity, notes, user_id))
            conn.commit()
            return True

    def get_low_stock_items(self):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            cursor.execute("""SELECT i.*, c.name as category_name FROM items i
                LEFT JOIN categories c ON i.category_id = c.id
                WHERE i.quantity <= i.low_stock_threshold ORDER BY i.quantity ASC""")
            return cursor.fetchall()

    def get_inventory_movements(self, item_id=None, limit=100):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            if item_id:
                cursor.execute("""SELECT im.*, i.name as item_name, u.username
                    FROM inventory_movements im JOIN items i ON im.item_id = i.id
                    LEFT JOIN users u ON im.user_id = u.id
                    WHERE im.item_id = %s ORDER BY im.created_at DESC LIMIT %s""",
                    (item_id, limit))
            else:
                cursor.execute("""SELECT im.*, i.name as item_name, u.username
                    FROM inventory_movements im JOIN items i ON im.item_id = i.id
                    LEFT JOIN users u ON im.user_id = u.id
                    ORDER BY im.created_at DESC LIMIT %s""", (limit,))
            return cursor.fetchall()

    def record_sale(self, item_id, quantity_sold, user_id=None, sale_price=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT quantity, price FROM items WHERE id = %s FOR UPDATE", (item_id,))
                result = cursor.fetchone()
                print(f"[DEBUG] record_sale item_id={item_id} qty_sold={quantity_sold} result={result}")
                if not result:
                    print(f"[DEBUG] Item {item_id} not found!")
                    conn.rollback()
                    return False
                current_quantity, default_price = result
                sale_price = sale_price or default_price
                print(f"[DEBUG] current_quantity={current_quantity} quantity_sold={quantity_sold}")
                if current_quantity < quantity_sold:
                    print(f"[DEBUG] Insufficient stock!")
                    conn.rollback()
                    return False
                new_quantity = current_quantity - quantity_sold
                cursor.execute("""INSERT INTO sales (item_id, quantity_sold, sale_price, user_id)
                    VALUES (%s, %s, %s, %s)""", (item_id, quantity_sold, sale_price, user_id))
                cursor.execute("""UPDATE items SET quantity = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s""", (new_quantity, item_id))
                cursor.execute("""INSERT INTO inventory_movements
                    (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (item_id, "SALE", quantity_sold, current_quantity, new_quantity,
                    f"Sold {quantity_sold} units at Php {sale_price}", user_id))
                conn.commit()
                print(f"[DEBUG] Sale recorded successfully!")
                return True
            except Exception as e:
                print(f"[ERROR] record_sale failed: {e}")
                conn.rollback()
                return False

    def get_sales_history(self, item_id=None, limit=100):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=self.extras.RealDictCursor)
            if item_id:
                cursor.execute("""SELECT s.*, i.name as item_name, u.username FROM sales s
                    JOIN items i ON s.item_id = i.id LEFT JOIN users u ON s.user_id = u.id
                    WHERE s.item_id = %s ORDER BY s.sale_date DESC LIMIT %s""",
                    (item_id, limit))
            else:
                cursor.execute("""SELECT s.*, i.name as item_name, u.username FROM sales s
                    JOIN items i ON s.item_id = i.id LEFT JOIN users u ON s.user_id = u.id
                    ORDER BY s.sale_date DESC LIMIT %s""", (limit,))
            return cursor.fetchall()

    def get_item_count_trend(self, days=7):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days*2)
            previous_end = datetime.now() - timedelta(days=days)
            cursor.execute("SELECT COUNT(*) FROM items WHERE created_at >= %s", (cutoff_date,))
            current_items = cursor.fetchone()[0]
            cursor.execute("""SELECT COUNT(*) FROM items WHERE created_at >= %s AND created_at < %s""",
                (previous_cutoff, previous_end))
            previous_items = cursor.fetchone()[0]
            if previous_items == 0:
                trend = 0 if current_items == 0 else 100
            else:
                trend = ((current_items - previous_items) / previous_items) * 100
            return trend

    def get_low_stock_status(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM items WHERE quantity <= low_stock_threshold")
            low_stock_count = cursor.fetchone()[0]
            cursor.execute("SELECT AVG(low_stock_threshold) FROM items")
            avg_threshold = cursor.fetchone()[0] or 10
            return low_stock_count, avg_threshold

    def get_sales_trend(self, days=7):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days*2)
            previous_end = datetime.now() - timedelta(days=days)
            cursor.execute("""SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
                WHERE sale_date >= %s""", (cutoff_date,))
            current_sales = cursor.fetchone()[0]
            cursor.execute("""SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
                WHERE sale_date >= %s AND sale_date < %s""", (previous_cutoff, previous_end))
            previous_sales = cursor.fetchone()[0]
            if previous_sales == 0:
                trend = 0 if current_sales == 0 else 100
            else:
                trend = ((current_sales - previous_sales) / previous_sales) * 100
            return trend

    def get_best_seller(self, days=7):
        """Get best selling item.
        Returns: (id, name, price, quantity, image_path, total_sold)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute("""SELECT i.id, i.name, i.price, i.quantity, i.image_path,
                SUM(s.quantity_sold) as total_sold
                FROM sales s JOIN items i ON s.item_id = i.id
                WHERE s.sale_date >= %s
                GROUP BY i.id, i.name, i.price, i.quantity, i.image_path
                ORDER BY total_sold DESC LIMIT 1""", (cutoff_date,))
            return cursor.fetchone()

    def get_dashboard_stats(self):
        """Get dashboard statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total items
            cursor.execute("SELECT COUNT(*) FROM items")
            total_items = cursor.fetchone()[0]
            
            # Get low stock items
            cursor.execute("SELECT COUNT(*) FROM items WHERE quantity <= low_stock_threshold")
            low_stock_items = cursor.fetchone()[0]
            
            # Get units sold today
            cursor.execute("""
                SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
                WHERE DATE(sale_date) = CURRENT_DATE
            """)
            units_sold_today = cursor.fetchone()[0]
            
            # Get total quantity in stock
            cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM items")
            total_quantity = cursor.fetchone()[0]
            
            # Get total inventory value
            cursor.execute("SELECT COALESCE(SUM(quantity * price), 0) FROM items")
            total_inventory_value = cursor.fetchone()[0]

            return {
                'total_items':            total_items,
                'low_stock_items':        low_stock_items,
                'low_stock_count':        low_stock_items,
                'units_sold_today':       units_sold_today,
                'total_quantity':         total_quantity,
                'total_inventory_value':  total_inventory_value,
            }

    def get_saleability_increase(self, days=7):
        """Get saleability increase trend for best seller."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            previous_cutoff = datetime.now() - timedelta(days=days*2)
            previous_end = datetime.now() - timedelta(days=days)
            
            # Get current period sales
            cursor.execute("""
                SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
                WHERE sale_date >= %s
            """, (cutoff_date,))
            current_sales = cursor.fetchone()[0]
            
            # Get previous period sales
            cursor.execute("""
                SELECT COALESCE(SUM(quantity_sold), 0) FROM sales
                WHERE sale_date >= %s AND sale_date < %s
            """, (previous_cutoff, previous_end))
            previous_sales = cursor.fetchone()[0]
            
            # Calculate trend
            if previous_sales == 0:
                trend = 0 if current_sales == 0 else 100
            else:
                trend = ((current_sales - previous_sales) / previous_sales) * 100
            
            return trend
        
    def get_items_added_per_day(self, days=7):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM items
                WHERE created_at >= %s AND created_at IS NOT NULL
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """, (cutoff_date,))
            rows = cursor.fetchall()
            return rows    
