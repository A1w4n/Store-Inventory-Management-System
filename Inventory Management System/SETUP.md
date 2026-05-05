# Database Configuration - Quick Reference

## What Was Done

✓ Merged 4 database files into 1 unified file  
✓ Cleaned up project structure  
✓ All existing imports continue to work  
✓ No changes needed in other files  

## Files Changed

| Action | File | Status |
|--------|------|--------|
| Merged into | `database.py` | ✓ Active |
| Removed | `database_config.py` | Merged |
| Removed | `database_pg.py` | Merged |
| Removed | `database_factory.py` | Merged |
| Created | `database_sqlite_backup.py` | Backup |

## How to Use

### Default (SQLite - Local Database)

Works out of the box, no configuration needed:

```python
from database import InventoryDatabase
db = InventoryDatabase()
```

### Switch to PostgreSQL (Remote Server)

1. Open `database.py`
2. Find line 24 and change:
   ```python
   USE_LOCAL_SQLITE = True   # ← Change to False
   ```

3. Update PostgreSQL settings (lines 26-32):
   ```python
   DB_CONFIG = {
       'host': '192.168.1.100',      # Your server IP
       'port': 5432,
       'database': 'inventory_db',
       'user': 'inventory_user',
       'password': 'your_password',   # Your password
   }
   ```

4. Install PostgreSQL driver:
   ```bash
   pip install psycopg2
   ```

5. Run your app - it will automatically use PostgreSQL!

## Key Points

🎯 **Single import for both backends**
```python
from database import InventoryDatabase
```

🎯 **Configuration in one place**
- Top of `database.py` (lines 24-32)
- Easy to find and modify

🎯 **No code changes needed**
- Same API for SQLite and PostgreSQL
- Drop-in compatible

🎯 **Easy testing**
- SQLite for development (default)
- PostgreSQL for production (change 1 flag + config)

## Configuration Reference

| Setting | Default | Purpose |
|---------|---------|---------|
| `USE_LOCAL_SQLITE` | `True` | Use SQLite (local) or PostgreSQL (remote) |
| `DB_CONFIG['host']` | `localhost` | PostgreSQL server IP/hostname |
| `DB_CONFIG['port']` | `5432` | PostgreSQL port (standard) |
| `DB_CONFIG['database']` | `inventory_db` | Database name on server |
| `DB_CONFIG['user']` | `inventory_user` | Database username |
| `DB_CONFIG['password']` | `your_password` | Database password |
| `DEBUG_SQL` | `False` | Enable SQL debug logging |

## Troubleshooting

**Q: Import error when using PostgreSQL?**
A: Install psycopg2: `pip install psycopg2`

**Q: Connection refused to PostgreSQL?**
A: Check host IP is correct, PostgreSQL is running, firewall allows port 5432

**Q: Want to go back to SQLite?**
A: Change `USE_LOCAL_SQLITE = True` in database.py

**Q: Lost the old files?**
A: `database_sqlite_backup.py` has the original SQLite code

## Maintenance

### Backing up your database

SQLite:
```bash
# Just copy the file
cp inventory.db inventory.db.backup
```

PostgreSQL:
```bash
pg_dump -U inventory_user inventory_db > backup.sql
```

### Switching between databases

Only needs 1 line change:
```python
# database.py, line 24
USE_LOCAL_SQLITE = True   # SQLite
USE_LOCAL_SQLITE = False  # PostgreSQL
```

## Next Steps

1. ✓ **Already done**: Database merged and tested
2. **Ready to use**: Start your application as normal
3. **For PostgreSQL**: Follow "Switch to PostgreSQL" instructions above when ready

## Files You Can Now Delete

- `database_config.py` - Already deleted ✓
- `database_pg.py` - Already deleted ✓
- `database_factory.py` - Already deleted ✓
- `POSTGRESQL_SETUP.md` - Optional (reference)
- `MIGRATION_GUIDE.md` - Optional (reference)
- `QUICK_START.md` - Optional (reference)

Keep `DATABASE_USAGE.md` for detailed reference.
