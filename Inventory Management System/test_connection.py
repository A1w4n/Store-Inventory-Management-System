import psycopg2

url = "postgresql://neondb_owner:npg_SL0dv4BDoCtg@ep-gentle-firefly-aom6jzpj.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

try:
    conn = psycopg2.connect(url)
    print("✅ Connected successfully!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:")
    print(e)
