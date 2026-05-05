# PostgreSQL Server Setup Guide

This guide helps you set up a PostgreSQL server for the inventory management system on your local network.

## Step 1: Install PostgreSQL on Your Server Machine

### Windows
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer and follow the setup wizard
3. Remember the password you set for the `postgres` user
4. Install on the machine that will be your database server

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### macOS
```bash
brew install postgresql
brew services start postgresql
```

## Step 2: Create Database & User

Connect to PostgreSQL as admin and run these commands:

```sql
-- Create database
CREATE DATABASE inventory_db;

-- Create user
CREATE USER inventory_user WITH PASSWORD 'your_secure_password_here';

-- Grant permissions
ALTER ROLE inventory_user SET client_encoding TO 'utf8';
ALTER ROLE inventory_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE inventory_user SET default_transaction_deferrable TO on;
ALTER ROLE inventory_user SET default_transaction_read_only TO off;

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;
```

### How to connect to PostgreSQL:

**Windows Command Line:**
```
psql -U postgres
```

**Linux/Mac:**
```bash
sudo -u postgres psql
```

Then paste the SQL commands above.

## Step 3: Enable Remote Connections

PostgreSQL needs to listen on network interfaces.

### Find PostgreSQL configuration files:
- **Windows**: `C:\Program Files\PostgreSQL\<version>\data\postgresql.conf`
- **Linux**: `/etc/postgresql/<version>/main/postgresql.conf`
- **Mac**: `/usr/local/var/postgres/postgresql.conf`

### Edit `postgresql.conf`:
Find and change:
```
listen_addresses = '*'
```

Or allow specific IP:
```
listen_addresses = '192.168.1.100'  # Your server's IP
```

### Edit `pg_hba.conf` (same directory):
Add this line to allow network connections:
```
host    inventory_db    inventory_user    0.0.0.0/0    md5
```

Or be more restrictive (recommended):
```
host    inventory_db    inventory_user    192.168.1.0/24    md5
```

### Restart PostgreSQL:
- **Windows**: Restart the PostgreSQL service in Services
- **Linux**: `sudo systemctl restart postgresql`
- **Mac**: `brew services restart postgresql`

## Step 4: Find Your Server's IP Address

### Windows:
```
ipconfig
```
Look for IPv4 Address (e.g., 192.168.1.100)

### Linux/Mac:
```bash
ifconfig
```
or
```bash
hostname -I
```

## Step 5: Update Configuration in Your App

Edit `database_config.py`:

```python
DB_CONFIG = {
    'host': '192.168.1.100',  # Your PostgreSQL server IP
    'port': 5432,
    'database': 'inventory_db',
    'user': 'inventory_user',
    'password': 'your_secure_password_here',
}
```

## Step 6: Install Python Dependencies

On the machine running your app:

```bash
pip install psycopg2
```

Or if psycopg2 has issues:

```bash
pip install psycopg2-binary
```

## Step 7: Verify Connection

Run this test script:

```python
import psycopg2

DB_CONFIG = {
    'host': '192.168.1.100',
    'port': 5432,
    'database': 'inventory_db',
    'user': 'inventory_user',
    'password': 'your_secure_password_here',
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"✓ Connection successful: {db_version}")
    conn.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

## Step 8: Migrate Your Data

Once PostgreSQL is set up and tested:

```bash
python migrate_sqlite_to_pg.py
```

This transfers all your existing data from SQLite to PostgreSQL.

## Step 9: Update Your Application

### In `main.py`:
```python
# Change from:
from database import InventoryDatabase

# To:
from database_pg import InventoryDatabase
```

### In `web_server.py`:
```python
# Change from:
from database import InventoryDatabase

# To:
from database_pg import InventoryDatabase
```

### In `auth_service.py` (if it imports database):
```python
# Do the same import change
```

## Step 10: Test Everything

1. Start your desktop app - it should connect to PostgreSQL
2. Open the web portal - it should access the same data
3. Try adding items in one, should appear in the other immediately

## Troubleshooting

### "Connection refused"
- PostgreSQL server is not running
- Check firewall settings on the server
- Verify the host/port in database_config.py

### "Authentication failed"
- Wrong password in database_config.py
- User doesn't have correct permissions
- Run `GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;`

### "Network unreachable"
- Wrong IP address for the server
- Server's firewall is blocking port 5432
- Need to edit pg_hba.conf to allow connections

### Data not visible from other machines
- Check that `listen_addresses = '*'` in postgresql.conf
- Restart PostgreSQL after changes
- Firewall may be blocking port 5432

## Benefits of PostgreSQL

✓ **Multi-user access** - Many users can access simultaneously  
✓ **Better concurrency** - No database locks like SQLite  
✓ **Persistence** - Data survives server restarts  
✓ **Remote access** - Access from any machine on the network  
✓ **Scalability** - Handles much larger datasets  
✓ **Advanced features** - Transactions, triggers, stored procedures  

## Additional Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- psycopg2 Documentation: https://www.psycopg.org/
