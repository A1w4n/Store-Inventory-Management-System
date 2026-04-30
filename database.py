import sqlite3
from datetime import datetime
from pathlib import Path
import hashlib

class InventoryDatabase:
    """Handles all database operations for the inventory management system."""

    def __init__(self, db_path="inventory.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = Path(db_path)
        self.connection = None
        self.init_db()

    def connect(self):
        """Create and return database connection."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        return self.connection

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def init_db(self):
        """Create all necessary tables."""
        conn = self.connect()
        cursor = conn.cursor()

        # Users table
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

        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Items/Products table
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

        # Inventory movements/transactions
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

        # Sales table (for tracking sold items)
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

    # USER OPERATIONS
    def add_user(self, username, password, email=None):
        """Add a new user to the database."""
        conn = self.connect()
        cursor = conn.cursor()
        password_hash = self._hash_password(password)

        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, email)
                VALUES (?, ?, ?)
            """, (username, password_hash, email))
            conn.commit()
            user_id = cursor.lastrowid
            self.disconnect()
            return user_id
        except sqlite3.IntegrityError:
            self.disconnect()
            return None

    def get_user_by_username(self, username):
        """Retrieve user by username."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        self.disconnect()
        return user

    def verify_password(self, stored_hash, password):
        """Verify if provided password matches stored hash."""
        return stored_hash == self._hash_password(password)

    @staticmethod
    def _hash_password(password):
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    # CATEGORY OPERATIONS
    def add_category(self, name, description=None):
        """Add a new category."""
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

    # ITEM OPERATIONS
    def add_item(self, name, price, category_id=None, sku=None, description=None,
                 quantity=0, low_stock_threshold=10, image_path=None):
        """Add a new item to inventory."""
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
        except sqlite3.IntegrityError:
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
        """Get all items with category names."""
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
        """Search items by name or SKU."""
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
        """Update item details."""
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
        """Delete an item."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        self.disconnect()
        return cursor.rowcount > 0

    # INVENTORY OPERATIONS
    def update_quantity(self, item_id, new_quantity, movement_type, user_id=None, notes=None):
        """Update item quantity and record movement."""
        conn = self.connect()
        cursor = conn.cursor()

        # Get current quantity
        cursor.execute("SELECT quantity FROM items WHERE id = ?", (item_id,))
        result = cursor.fetchone()
        if not result:
            self.disconnect()
            return False

        previous_quantity = result[0]

        # Update quantity
        cursor.execute("""
            UPDATE items SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_quantity, item_id))

        # Record movement
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
        """Get items below low stock threshold."""
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
        """Get inventory movement history."""
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

    # SALES OPERATIONS
    def record_sale(self, item_id, quantity_sold, user_id=None, sale_price=None):
        """Record a sale and update inventory."""
        conn = self.connect()
        cursor = conn.cursor()

        # Get current quantity
        cursor.execute("SELECT quantity, price FROM items WHERE id = ?", (item_id,))
        result = cursor.fetchone()
        if not result:
            self.disconnect()
            return False

        current_quantity, default_price = result
        sale_price = sale_price or default_price

        if current_quantity < quantity_sold:
            self.disconnect()
            return False

        new_quantity = current_quantity - quantity_sold

        # Record sale
        cursor.execute("""
            INSERT INTO sales (item_id, quantity_sold, sale_price, user_id)
            VALUES (?, ?, ?, ?)
        """, (item_id, quantity_sold, sale_price, user_id))

        # Update inventory via update_quantity
        self.update_quantity(item_id, new_quantity, "SALE", user_id,
                           f"Sold {quantity_sold} units at ${sale_price}")

        conn.commit()
        self.disconnect()
        return True

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

    # DASHBOARD STATISTICS
    def get_dashboard_stats(self):
        """Get statistics for dashboard."""
        conn = self.connect()
        cursor = conn.cursor()

        stats = {}

        # Total items count
        cursor.execute("SELECT COUNT(*) FROM items")
        stats['total_items'] = cursor.fetchone()[0]

        # Low stock items count
        cursor.execute("""
            SELECT COUNT(*) FROM items
            WHERE quantity <= low_stock_threshold
        """)
        stats['low_stock_items'] = cursor.fetchone()[0]

        # Total inventory value
        cursor.execute("""
            SELECT SUM(price * quantity) FROM items
        """)
        result = cursor.fetchone()[0]
        stats['total_inventory_value'] = result or 0.0

        # Total quantity
        cursor.execute("SELECT SUM(quantity) FROM items")
        result = cursor.fetchone()[0]
        stats['total_quantity'] = result or 0

        # Today's sales
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(quantity_sold), 0) FROM sales
            WHERE DATE(sale_date) = DATE('now')
        """)
        sales_today = cursor.fetchone()
        stats['sales_today_count'] = sales_today[0] or 0
        stats['units_sold_today'] = sales_today[1] or 0

        self.disconnect()
        return stats
