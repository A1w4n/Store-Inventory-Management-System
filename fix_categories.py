import psycopg2

conn = psycopg2.connect('postgresql://neondb_owner:npg_UAfxw7k9KFaP@ep-broad-water-aov46oze-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
conn.autocommit = True
cur = conn.cursor()

# Add missing categories
categories = [
    ('Food', 'Food and beverages'),
    ('Electronics', 'Electronic devices and gadgets'),
    ('Clothing', 'Apparel and accessories'),
    ('Furniture', 'Office and home furniture'),
]

for name, desc in categories:
    cur.execute("INSERT INTO categories (name, description) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING", (name, desc))
    print(f'Added/verified: {name}')

cur.execute('SELECT * FROM categories')
print('\nAll categories:')
for r in cur.fetchall():
    print(r)

conn.close()
print('Done!')