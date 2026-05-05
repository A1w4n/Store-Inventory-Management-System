# ProStock Cloud Deployment Guide
## Stack: Supabase (PostgreSQL) + Railway (Flask API)

---

## Overview

```
Your Desktop App  ──────────────────────────────────┐
                                                     ▼
Staff Browsers  ──►  Railway (web_server.py)  ──►  Supabase PostgreSQL
                      https://your-app.railway.app    (free hosted DB)
```

Both your desktop app and the staff portal will read/write
the **same** Supabase database in real time.

---

## Step 1 — Create a Supabase Database (free)

1. Go to **https://supabase.com** → Sign up (free)
2. Click **New Project**
   - Name: `prostock`
   - Set a strong database password (save it!) = pogiako587896#
   - Region: pick closest to you (e.g. Southeast Asia)
3. Wait ~2 minutes for it to provision
4. Go to **Project Settings → Database**
5. Scroll to **Connection string → Python**
6. Copy the string — it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
   # postgresql://postgres:pogiako587896#@db.tnqiqitbvumghfuzrbpk.supabase.co:5432/postgres
   > ⚠️ Replace `[YOUR-PASSWORD]` with your actual password

---

## Step 2 — Migrate Your Local Data to Supabase

On your local machine (where `inventory.db` exists):

```bash
# Install psycopg2 if not already installed
pip install psycopg2-binary

# Set your Supabase connection string
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.YOURREF.supabase.co:5432/postgres"

# Run the migration
python migrate_to_cloud.py
```

You should see:
```
✓ Users:      1
✓ Categories: 3
✓ Items:      10
✓ Movements:  ...
✓ Sales:      ...
✅ Migration complete!
```

---

## Step 3 — Deploy to Railway (free tier)

### 3a. Push to GitHub

```bash
# Create a new GitHub repo (private is fine)
# Then from the cloud_deploy/ folder:

git init
git add .
git commit -m "ProStock staff portal"
git remote add origin https://github.com/YOUR_USERNAME/prostock-portal.git
git push -u origin main
```

> Make sure `staff_portal.html` is inside a `static/` subfolder
> (the web_server.py serves it from there).

### 3b. Create Railway Project

1. Go to **https://railway.app** → Sign up with GitHub (free)
2. Click **New Project → Deploy from GitHub repo**
3. Select your `prostock-portal` repo
4. Railway will auto-detect Python and start building

### 3c. Set Environment Variables in Railway

In your Railway project → **Variables** tab, add:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres` |
| `PYTHON_VERSION` | `3.11` |

Railway will automatically inject `PORT` — do not set it manually.

### 3d. Confirm Deployment

1. Go to **Deployments** tab — wait for the green ✓
2. Click **Settings → Networking → Generate Domain**
3. You'll get a URL like: `https://prostock-portal-production.up.railway.app`
4. Open it in any browser — the staff portal should load!

---

## Step 4 — Update Your Desktop App to Use Supabase

So the desktop app reads/writes the same cloud database:

```bash
# On Windows (add to your system environment variables or run before launching):
set DATABASE_URL=postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres

# On Mac/Linux:
export DATABASE_URL="postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres"
```

Or create a `.env` file next to `main.py`:
```
DATABASE_URL=postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres
```

And add this to the top of `main.py` (before any imports):
```python
from dotenv import load_dotenv
load_dotenv()
```

Install dotenv: `pip install python-dotenv`

---

## Step 5 — Update StaffAccess_UI.py

The QR code should now point to your Railway URL instead of local IP.
Open `StaffAccess_UI.py` and change `_get_url()`:

```python
def _get_url(self) -> str:
    # Return Railway URL if set, otherwise fall back to local
    cloud_url = os.environ.get("STAFF_PORTAL_URL", "")
    if cloud_url:
        return cloud_url
    return f"http://{_get_local_ip()}:{self.port}"
```

Then set in your environment:
```
STAFF_PORTAL_URL=https://prostock-portal-production.up.railway.app
```

---

## File Structure for Your GitHub Repo

```
prostock-portal/          ← what you push to GitHub
├── web_server.py
├── database.py
├── requirements.txt
├── Procfile
├── railway.json
├── migrate_to_cloud.py
└── static/
    └── staff_portal.html    ← move your HTML file here
```

> ⚠️ Do NOT push `inventory.db`, `.env`, or any file with passwords.
> Add a `.gitignore`:

```
inventory.db
.env
__pycache__/
*.pyc
```

---

## Free Tier Limits

| Service | Free Limit | Notes |
|---|---|---|
| Supabase | 500 MB DB, 50,000 rows | More than enough for inventory |
| Railway | $5 credit/month | ~500 hours of runtime — plenty |
| Both | No credit card required | Just email signup |

---

## Troubleshooting

**Portal shows blank page**
→ Check Railway logs. Usually means `staff_portal.html` isn't in `static/` folder.

**"could not connect to server"**
→ Your `DATABASE_URL` is wrong or missing. Check Railway → Variables tab.

**Desktop app still uses SQLite**
→ `DATABASE_URL` isn't set in your desktop environment. See Step 4.

**"SSL connection required"**
→ The `database.py` auto-appends `?sslmode=require` — this should not happen.
   If it does, manually add `?sslmode=require` to your `DATABASE_URL`.

**Migration fails with "sequence" error**
→ Re-run `migrate_to_cloud.py` — it skips existing rows and resets sequences safely.
