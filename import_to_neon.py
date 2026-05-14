import psycopg2

NEON_URL = 'postgresql://neondb_owner:npg_UAfxw7k9KFaP@ep-broad-water-aov46oze-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

local_conn = psycopg2.connect(
    host='localhost', port=5432,
    database='inventory', user='inventory_user', password='admin123'
)
neon_conn = psycopg2.connect(NEON_URL)
neon_cur = neon_conn.cursor()
local_cur = local_conn.cursor()

# Create tables first
neon_cur.execute("""
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
neon_conn.commit()
print("Tables created!")

# Import data
tables = ['users', 'categories', 'items', 'inventory_movements', 'sales']

for table in tables:
    local_cur.execute(f'SELECT * FROM {table}')
    rows = local_cur.fetchall()
    if not rows:
        print(f'  {table}: empty, skipping')
        continue
    local_cur.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position', (table,))
    cols = [r[0] for r in local_cur.fetchall()]
    placeholders = ','.join(['%s'] * len(cols))
    col_names = ','.join(cols)
    for row in rows:
        neon_cur.execute(f'INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING', row)
    neon_conn.commit()
    print(f'  {table}: {len(rows)} rows inserted')

print('Done!')
local_conn.close()
neon_conn.close()