# PostgreSQL Migration Guide

## What Was Created

Your inventory system now supports **PostgreSQL** for server-based, multi-user database access. Here are the new files:

| File | Purpose |
|------|---------|
| `database_config.py` | Configuration for PostgreSQL connection details |
| `database_pg.py` | PostgreSQL-compatible database module (replaces SQLite) |
| `database_factory.py` | Automatically selects SQLite or PostgreSQL |
| `migrate_sqlite_to_pg.py` | Script to transfer data from SQLite to PostgreSQL |
| `POSTGRESQL_SETUP.md` | Detailed setup instructions |
| `requirements_pg.txt` | Python dependencies for PostgreSQL |

## Quick Start (5 Steps)

### 1. Set Up PostgreSQL Server
Follow the instructions in [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md)

```bash
# Minimum: Create database and user
CREATE DATABASE inventory_db;
CREATE USER inventory_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;
```

### 2. Install Dependencies
```bash
pip install psycopg2
# or if that fails:
pip install psycopg2-binary
```

### 3. Update Configuration
Edit `database_config.py`:
```python
DB_CONFIG = {
    'host': '192.168.1.100',  # Your PostgreSQL server IP
    'port': 5432,
    'database': 'inventory_db',
    'user': 'inventory_user',
    'password': 'your_secure_password_here',  # The password you created
}

USE_LOCAL_SQLITE = False  # Switch to PostgreSQL
```

### 4. Migrate Data (Optional)
If you have existing inventory data:
```bash
python migrate_sqlite_to_pg.py
```

### 5. Update Imports in Your App
Change imports in:
- `main.py` - Line 8
- `web_server.py` - Line 11  
- `auth_service.py` - If it imports database

From:
```python
from database import InventoryDatabase
```

To (option A - Manual):
```python
from database_pg import InventoryDatabase
```

Or (option B - Smart switching):
```python
from database_factory import InventoryDatabase
```

## How It Works

### Before (SQLite)
```
Desktop App → inventory.db (local file)
Web Portal → inventory.db (local file)
↑ Database lock conflicts ✗
```

### After (PostgreSQL)
```
PostgreSQL Server (192.168.1.100:5432)
         ↑                 ↑
   Desktop App      Web Portal
   ✓ No conflicts, shared real-time data
```

## Benefits

| Feature | SQLite | PostgreSQL |
|---------|--------|-----------|
| Multiple Users | ✗ (locks) | ✓ (true concurrency) |
| Network Access | ✗ | ✓ |
| Real-time Sync | ✗ | ✓ |
| Data Persistence | ✓ | ✓ |
| Scalability | ✗ | ✓ |
| Remote Access | ✗ | ✓ |

## Configuration Options

### Option 1: SQLite (Development/Testing)
```python
# database_config.py
USE_LOCAL_SQLITE = True
```
- Use: Quick testing, no server needed
- Downside: Database locks, no network access

### Option 2: PostgreSQL (Production)
```python
# database_config.py
USE_LOCAL_SQLITE = False
DB_CONFIG = {
    'host': 'your_server_ip',
    'port': 5432,
    'database': 'inventory_db',
    'user': 'inventory_user',
    'password': 'your_password',
}
```
- Use: Live system, multiple users
- Benefits: Shared access, real-time data

## Testing Your Setup

### Test Connection
```python
python
>>> from database_config import DB_CONFIG
>>> import psycopg2
>>> conn = psycopg2.connect(**DB_CONFIG)
>>> print("✓ Connected!")
```

### Test with Application
```bash
# In one terminal
python main.py

# In another terminal
python
>>> from database_factory import InventoryDatabase
>>> db = InventoryDatabase()
>>> items = db.get_all_items()
>>> print(f"Found {len(items)} items")
```

## Troubleshooting

### "psycopg2 not installed"
```bash
pip install psycopg2
# or
pip install psycopg2-binary
```

### "Connection refused"
- Is PostgreSQL running? `sudo systemctl status postgresql`
- Is the server IP correct in `database_config.py`?
- Check firewall on PostgreSQL server

### "Authentication failed"
- Check password in `database_config.py`
- Verify user exists in PostgreSQL
- Check `pg_hba.conf` allows connections from your IP

### "Database does not exist"
- Run setup commands in POSTGRESQL_SETUP.md
- Or run migration script

### Data not syncing between apps
- Make sure both use the same PostgreSQL server
- Check both have correct IP in `database_config.py`
- Restart apps if needed

## Migration Path

If you already have data in SQLite:

```bash
# Step 1: Set up PostgreSQL
# ... follow POSTGRESQL_SETUP.md ...

# Step 2: Run migration
python migrate_sqlite_to_pg.py

# Step 3: Update config
# Edit database_config.py, set USE_LOCAL_SQLITE = False

# Step 4: Update imports
# Change from database import to database_pg import

# Step 5: Test
python main.py
```

## Safe Rollback

If you need to go back to SQLite:

```python
# database_config.py
USE_LOCAL_SQLITE = True
```

Your original `inventory.db` file is still there (unless you deleted it).

## Advanced: Using Connection Pooling

The PostgreSQL implementation includes connection pooling automatically:

```python
# database_pg.py already handles this
# Min connections: 1
# Max connections: 10
# Automatically manages connection reuse
```

## Best Practices

1. **Secure your password** - Use environment variables in production:
   ```python
   import os
   DB_CONFIG['password'] = os.getenv('DB_PASSWORD')
   ```

2. **Regular backups** - PostgreSQL should be backed up regularly
   ```bash
   pg_dump -U inventory_user inventory_db > backup.sql
   ```

3. **Monitor performance** - Check slow queries
   ```sql
   SELECT query FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
   ```

4. **Plan for growth** - PostgreSQL can scale to millions of records

## Next Steps

1. ✓ Read [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md)
2. ✓ Install PostgreSQL on your server
3. ✓ Create database and user
4. ✓ Install psycopg2 on client machines
5. ✓ Update `database_config.py`
6. ✓ Run `migrate_sqlite_to_pg.py`
7. ✓ Update imports in Python files
8. ✓ Test both desktop and web app

## Support

For PostgreSQL issues: https://www.postgresql.org/docs/  
For psycopg2 issues: https://www.psycopg.org/docs/  
