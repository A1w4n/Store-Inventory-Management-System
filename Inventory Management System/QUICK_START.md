# Quick Start Checklist - PostgreSQL Migration

## Pre-Flight Checklist

Complete this in order:

### ✓ Part 1: PostgreSQL Server Setup (30 min)
- [ ] Install PostgreSQL on your network server machine
  - Windows: https://www.postgresql.org/download/windows/
  - Linux: `sudo apt install postgresql`
  - macOS: `brew install postgresql`
  
- [ ] Start PostgreSQL service
  - Windows: Services → PostgreSQL
  - Linux: `sudo systemctl start postgresql`
  - macOS: `brew services start postgresql`

- [ ] Find your server's IP address
  - Windows: `ipconfig` (look for IPv4)
  - Linux/Mac: `hostname -I`
  - Example: `192.168.1.100`

- [ ] Create database and user
  ```bash
  psql -U postgres
  ```
  Then paste this (change password!):
  ```sql
  CREATE DATABASE inventory_db;
  CREATE USER inventory_user WITH PASSWORD 'SecurePassword123';
  GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;
  ```

- [ ] Test connection from your client machine
  ```bash
  pip install psycopg2
  psql -h 192.168.1.100 -U inventory_user -d inventory_db
  ```
  (Replace IP with your server IP)

### ✓ Part 2: Update Application Configuration (5 min)

- [ ] Edit `database_config.py` in your project folder
  ```python
  DB_CONFIG = {
      'host': '192.168.1.100',     # ← Your server IP
      'port': 5432,
      'database': 'inventory_db',
      'user': 'inventory_user',
      'password': 'SecurePassword123',  # ← Your password
  }
  
  USE_LOCAL_SQLITE = False  # ← Enable PostgreSQL
  ```

- [ ] Install Python PostgreSQL library
  ```bash
  pip install psycopg2
  ```

### ✓ Part 3: Migrate Existing Data (Optional - 10 min)
*Only if you have existing inventory data in SQLite*

- [ ] Place `inventory.db` in same folder as `migrate_sqlite_to_pg.py`

- [ ] Run migration
  ```bash
  python migrate_sqlite_to_pg.py
  ```

- [ ] Verify all data transferred
  - Check message shows items/users/sales count
  - Should say "MIGRATION COMPLETE!"

### ✓ Part 4: Update Python Imports (5 min)

In each file that imports database, change:

**File: `main.py` (Line ~8)**
```python
# FROM:
from database import InventoryDatabase

# TO:
from database_pg import InventoryDatabase
```

**File: `web_server.py` (Line ~11)**
```python
# FROM:
from database import InventoryDatabase

# TO:
from database_pg import InventoryDatabase
```

**File: `auth_service.py` (if it imports database)**
```python
# FROM:
from database import InventoryDatabase

# TO:
from database_pg import InventoryDatabase
```

### ✓ Part 5: Testing (10 min)

- [ ] Start desktop application
  ```bash
  python main.py
  ```
  Should see: `[DB] Connected to PostgreSQL at 192.168.1.100:5432`

- [ ] Try adding an item in desktop app

- [ ] Open web portal in browser
  ```
  http://localhost:5000
  ```

- [ ] Verify the item you added appears in web portal

- [ ] Try adding item in web portal

- [ ] Refresh desktop app, verify new item appears

### ✓ Part 6: Optimize (Optional)

- [ ] Edit `pg_hba.conf` for network access (POSTGRESQL_SETUP.md)
- [ ] Set up automated backups
- [ ] Add PostgreSQL to system startup

## Files Created for You

New files in your project:
```
database_config.py          ← Configuration (edit this!)
database_pg.py              ← PostgreSQL module (use this)
database_factory.py         ← Auto-selector (optional)
migrate_sqlite_to_pg.py     ← Data migration tool
POSTGRESQL_SETUP.md         ← Detailed setup guide
MIGRATION_GUIDE.md          ← Step-by-step guide
SERVER_DATABASE_OVERVIEW.md ← Architecture overview
requirements_pg.txt         ← Dependencies list
QUICK_START.md              ← This file
```

## Troubleshooting Quick Fixes

### "Connection refused"
1. Verify PostgreSQL is running on server
2. Verify correct IP in database_config.py
3. Check firewall allows port 5432

### "psycopg2 not found"
```bash
pip install psycopg2
```

### "Authentication failed"
1. Verify password in database_config.py matches database
2. Verify username/database name is correct
3. Try connecting manually first

### "Database does not exist"
Run these in PostgreSQL:
```sql
CREATE DATABASE inventory_db;
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;
```

## Important: Three Ways to Use

### Option 1: PostgreSQL Only (Recommended)
```python
from database_pg import InventoryDatabase
# Must have PostgreSQL running
# Best for production
```

### Option 2: SQLite Fallback
```python
from database_factory import InventoryDatabase
# Uses PostgreSQL if available, falls back to SQLite
# Best for flexibility
```

### Option 3: SQLite Only (Original)
```python
from database import InventoryDatabase
# Works without any server setup
# Best for testing/development
```

## Expected Results After Setup

✓ Desktop app and web portal share same data  
✓ No more database lock errors  
✓ Real-time data synchronization  
✓ Multiple users can work simultaneously  
✓ Data accessible from anywhere on network  

## Did It Work?

Test successful if:
1. Desktop app starts without connection errors
2. Web portal responds at http://localhost:5000
3. Data added in one appears in the other within seconds
4. Multiple users can access simultaneously

## Keep Your Original SQLite Database

Don't delete `inventory.db` - it's your backup:
- If PostgreSQL fails, set `USE_LOCAL_SQLITE = True` to rollback
- Use it for testing new features
- Archive old databases

## Need More Help?

Read these in order:
1. **POSTGRESQL_SETUP.md** - For server setup questions
2. **MIGRATION_GUIDE.md** - For migration questions
3. **SERVER_DATABASE_OVERVIEW.md** - For architecture questions

## Next Steps

```
1. Set up PostgreSQL server (30 min)
   ↓
2. Test connection (5 min)
   ↓
3. Update database_config.py (2 min)
   ↓
4. Run migration if needed (10 min)
   ↓
5. Update imports (5 min)
   ↓
6. Test application (10 min)
   ↓
DONE! ✓
```

**Total Time: ~1-2 hours** (mostly waiting for PostgreSQL install)

---

Print this checklist and check items off as you complete them!
