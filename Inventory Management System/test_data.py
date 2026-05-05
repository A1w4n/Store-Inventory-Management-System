import sqlite3
from datetime import datetime, timedelta
import random

conn = sqlite3.connect("inventory.db")
cursor = conn.cursor()

# Add test categories
cursor.execute("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
               ("Electronics", "Electronic items"))
cursor.execute("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
               ("Office Supplies", "Office supplies"))
conn.commit()

# Get category IDs
cursor.execute("SELECT id FROM categories WHERE name = 'Electronics'")
cat1 = cursor.fetchone()[0]
cursor.execute("SELECT id FROM categories WHERE name = 'Office Supplies'")
cat2 = cursor.fetchone()[0]

# Add test items
cursor.execute("""INSERT OR IGNORE INTO items (name, sku, category_id, description, price, quantity, low_stock_threshold)
                  VALUES (?, ?, ?, ?, ?, ?, ?)""",
               ("Laptop", "SKU001", cat1, "High-performance laptop", 999.99, 50, 5))
cursor.execute("""INSERT OR IGNORE INTO items (name, sku, category_id, description, price, quantity, low_stock_threshold)
                  VALUES (?, ?, ?, ?, ?, ?, ?)""",
               ("Mouse", "SKU002", cat1, "Wireless mouse", 29.99, 150, 20))
cursor.execute("""INSERT OR IGNORE INTO items (name, sku, category_id, description, price, quantity, low_stock_threshold)
                  VALUES (?, ?, ?, ?, ?, ?, ?)""",
               ("Paper Ream", "SKU003", cat2, "500 sheets", 5.99, 200, 50))
conn.commit()

# Get item IDs
cursor.execute("SELECT id FROM items WHERE sku = 'SKU001'")
item1_id = cursor.fetchone()[0]
cursor.execute("SELECT id FROM items WHERE sku = 'SKU002'")
item2_id = cursor.fetchone()[0]
cursor.execute("SELECT id FROM items WHERE sku = 'SKU003'")
item3_id = cursor.fetchone()[0]

# Add inventory movements for the last 7 days
for i in range(7):
    date = (datetime.now() - timedelta(days=i)).isoformat()

    # Add inbound movements
    cursor.execute("""INSERT INTO inventory_movements (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (item1_id, "INBOUND", random.randint(5, 20), 40, 50, f"Restocking", date))
    cursor.execute("""INSERT INTO inventory_movements (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (item2_id, "INBOUND", random.randint(10, 30), 120, 150, f"Restocking", date))

    # Add outbound movements (sales)
    cursor.execute("""INSERT INTO inventory_movements (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (item1_id, "OUTBOUND", random.randint(1, 5), 50, 45, f"Sale", date))
    cursor.execute("""INSERT INTO inventory_movements (item_id, movement_type, quantity, previous_quantity, new_quantity, notes, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (item2_id, "OUTBOUND", random.randint(5, 10), 150, 140, f"Sale", date))

conn.commit()
conn.close()

print("[OK] Test data added successfully!")
