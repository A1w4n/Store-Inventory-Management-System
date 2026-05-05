"""
Setup script to initialize database with sample data
Run this once to populate the database
"""

from database import InventoryDatabase

def setup_database():
    print("🗄️  Initializing database...")
    db = InventoryDatabase("inventory.db")

    # Add default admin user
    print("👤 Adding default admin user...")
    user = db.get_user_by_username("admin")
    if not user:
        db.add_user("admin", "password123", "admin@inventory.com")
        print("   ✓ Admin user created (password123)")
    else:
        print("   ✓ Admin user already exists")

    # Add categories
    print("📂 Adding categories...")
    electronics_id = db.add_category("Electronics", "Electronic devices and gadgets")
    clothing_id = db.add_category("Clothing", "Apparel and accessories")
    furniture_id = db.add_category("Furniture", "Office and home furniture")
    print("   ✓ Categories added")

    # Add sample items
    print("📦 Adding sample items...")
    items_data = [
        ("Laptop",       "ELEC001", electronics_id, 1200.00, 8,  "High-performance laptop", 5),
        ("Wireless Mouse","ELEC002",electronics_id,  29.99, 45,  "Bluetooth mouse",         10),
        ("USB-C Cable",  "ELEC003", electronics_id,  12.99,  3,  "5-meter USB-C cable",     15),
        ("Monitor Stand","ELEC004", electronics_id,  49.99, 12,  "Adjustable monitor stand", 5),
        ("T-Shirt",      "CLOTH001",clothing_id,     19.99,  2,  "Cotton t-shirt",          20),
        ("Jeans",        "CLOTH002",clothing_id,     59.99, 15,  "Blue denim jeans",         5),
        ("Office Chair", "FURN001", furniture_id,   299.99,  4,  "Ergonomic office chair",   3),
        ("Desk Lamp",    "FURN002", furniture_id,    79.99, 10,  "LED desk lamp",            5),
        ("Keyboard",     "ELEC005", electronics_id,  89.99, 20,  "Mechanical keyboard",      5),
        ("Headphones",   "ELEC006", electronics_id, 149.99,  6,  "Noise-cancelling headphones", 5),
    ]

    for name, sku, category_id, price, quantity, description, threshold in items_data:
        item_id = db.add_item(
            name=name,
            sku=sku,
            category_id=category_id,
            price=price,
            quantity=quantity,
            description=description,
            low_stock_threshold=threshold
        )
        if item_id:
            print(f"   ✓ Added {name} (Stock: {quantity})")

    # Display dashboard stats
    print("\n📊 Dashboard Statistics:")
    stats = db.get_dashboard_stats()
    print(f"   Total Items: {stats.get('total_items', 'N/A')}")
    print(f"   Low Stock Items: {stats.get('low_stock_count', 'N/A')}")
    print(f"   Total Inventory Value: {stats.get('total_inventory_value', 'N/A')}")
    print(f"   Total Units in Stock: {stats.get('total_quantity', 'N/A')}")
    print("\n✅ Database setup complete!")
    print("📝 You can now run: python main.py")

if __name__ == "__main__":
    setup_database()
