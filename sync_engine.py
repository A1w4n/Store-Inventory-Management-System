# sync_engine.py — Offline-First Sync Engine for ProStock
#
# Architecture:
#   - The desktop app ALWAYS reads from and writes to local SQLite first.
#   - Every mutating action (add/update/delete/sale/quantity change) is also
#     written to an "outbox" table as a queued operation.
#   - A background thread wakes up every SYNC_INTERVAL seconds, checks for
#     internet connectivity, and if online:
#       1. Pushes all pending outbox operations to the cloud (PostgreSQL via
#          the web server's REST API).
#       2. Pulls the latest data from the cloud and refreshes the local cache.
#   - The desktop app never waits for the network — it is always instant.
#
# Tables added to local SQLite:
#   sync_outbox   — queued writes waiting to reach the cloud
#   sync_meta     — tracks the last successful sync timestamp per table
#
# Usage:
#   from sync_engine import SyncEngine
#   engine = SyncEngine(local_db_path="inventory.db", cloud_url="https://your-railway-url")
#   engine.start()                 # starts background sync thread
#   engine.force_sync()            # manual sync trigger
#   engine.stop()                  # clean shutdown

import sqlite3
import json
import time
import threading
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

log = logging.getLogger("SyncEngine")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s %(message)s")

# ─────────────────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────────────────

SYNC_INTERVAL   = 30          # seconds between auto-sync attempts
REQUEST_TIMEOUT = 10          # seconds before giving up on a cloud request
MAX_RETRIES     = 3           # outbox retries before marking as failed


# ─────────────────────────────────────────────────────────────────────────────
#  Sync status constants  (used by UI status indicators)
# ─────────────────────────────────────────────────────────────────────────────

class SyncStatus:
    IDLE       = "idle"
    SYNCING    = "syncing"
    ONLINE     = "online"
    OFFLINE    = "offline"
    ERROR      = "error"


# ─────────────────────────────────────────────────────────────────────────────
#  SyncEngine
# ─────────────────────────────────────────────────────────────────────────────

class SyncEngine:
    """
    Manages offline-first data sync between local SQLite and the cloud.

    Parameters
    ----------
    local_db_path : str | Path
        Path to the local SQLite database file.
    cloud_url : str
        Base URL of the deployed web server (e.g. "https://prostock.up.railway.app").
        Must NOT have a trailing slash.
    on_status_change : Callable[[str], None] | None
        Optional callback fired whenever the sync status changes.
        Receives one of the SyncStatus constants.
    on_sync_complete : Callable[[dict], None] | None
        Optional callback fired after a successful sync cycle.
        Receives a summary dict: {"pushed": int, "pulled": int, "ts": str}
    """

    def __init__(
        self,
        local_db_path: str = "inventory.db",
        cloud_url: str = "",
        on_status_change: Optional[Callable] = None,
        on_sync_complete: Optional[Callable] = None,
    ):
        self.local_db_path     = Path(local_db_path)
        self.cloud_url         = cloud_url.rstrip("/")
        self._on_status_change = on_status_change
        self._on_sync_complete = on_sync_complete

        self._status           = SyncStatus.IDLE
        self._lock             = threading.Lock()
        self._stop_event       = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_sync_ts: Optional[str] = None
        self._pending_count    = 0

        self._init_sync_tables()
        log.info(f"SyncEngine ready — local={self.local_db_path}, cloud={self.cloud_url or '(none)'}")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Start the background sync thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SyncThread")
        self._thread.start()
        log.info("Background sync thread started.")

    def stop(self) -> None:
        """Signal the background thread to stop and wait for it."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        log.info("Background sync thread stopped.")

    def force_sync(self) -> dict:
        """
        Trigger an immediate sync cycle (blocking).
        Returns a summary dict.
        """
        return self._sync_cycle()

    @property
    def status(self) -> str:
        return self._status

    @property
    def last_sync_ts(self) -> Optional[str]:
        return self._last_sync_ts

    @property
    def pending_count(self) -> int:
        """Number of outbox operations not yet pushed to the cloud."""
        return self._pending_count

    def is_online(self) -> bool:
        """Quick connectivity check against the cloud health endpoint."""
        if not self.cloud_url:
            return False
        try:
            r = requests.get(f"{self.cloud_url}/health", timeout=REQUEST_TIMEOUT)
            return r.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Outbox — queue a local write for later cloud push                   #
    # ------------------------------------------------------------------ #

    def enqueue(self, table: str, operation: str, payload: dict) -> None:
        """
        Queue a mutating operation for cloud sync.

        Parameters
        ----------
        table     : "items" | "categories" | "sales" | "inventory_movements" | "users"
        operation : "INSERT" | "UPDATE" | "DELETE" | "SALE" | "QUANTITY"
        payload   : dict of values relevant to the operation
        """
        ts = datetime.now(timezone.utc).isoformat()
        with self._local_conn() as conn:
            conn.execute(
                """
                INSERT INTO sync_outbox (table_name, operation, payload, created_at, retries)
                VALUES (?, ?, ?, ?, 0)
                """,
                (table, operation, json.dumps(payload), ts),
            )
            conn.commit()
        self._refresh_pending_count()
        log.debug(f"Enqueued {operation} on {table}: {payload}")

    # ------------------------------------------------------------------ #
    #  Internal — SQLite helpers                                           #
    # ------------------------------------------------------------------ #

    def _local_conn(self):
        conn = sqlite3.connect(str(self.local_db_path), timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=15000;")
        return conn

    def _init_sync_tables(self) -> None:
        """Create the outbox and meta tables if they don't exist."""
        with self._local_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_outbox (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT    NOT NULL,
                    operation  TEXT    NOT NULL,
                    payload    TEXT    NOT NULL,
                    created_at TEXT    NOT NULL,
                    retries    INTEGER DEFAULT 0,
                    last_error TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
        self._refresh_pending_count()

    def _refresh_pending_count(self) -> None:
        with self._local_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sync_outbox WHERE retries < ?", (MAX_RETRIES,)
            ).fetchone()
            self._pending_count = row[0] if row else 0

    def _get_meta(self, key: str, default=None):
        with self._local_conn() as conn:
            row = conn.execute("SELECT value FROM sync_meta WHERE key = ?", (key,)).fetchone()
            return row[0] if row else default

    def _set_meta(self, key: str, value: str) -> None:
        with self._local_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)", (key, value)
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    #  Internal — sync cycle                                               #
    # ------------------------------------------------------------------ #

    def _loop(self) -> None:
        """Background thread main loop."""
        while not self._stop_event.is_set():
            self._sync_cycle()
            self._stop_event.wait(timeout=SYNC_INTERVAL)

    def _sync_cycle(self) -> dict:
        """One full push → pull cycle. Returns a summary dict."""
        summary = {"pushed": 0, "pulled": 0, "ts": "", "error": None}

        if not self.cloud_url:
            self._set_status(SyncStatus.OFFLINE)
            return summary

        self._set_status(SyncStatus.SYNCING)

        # ── 1. Check connectivity ─────────────────────────────────────────
        if not self.is_online():
            log.info("Offline — skipping sync cycle.")
            self._set_status(SyncStatus.OFFLINE)
            return summary

        # ── 2. Push pending outbox ops ────────────────────────────────────
        pushed = self._push_outbox()
        summary["pushed"] = pushed

        # ── 3. Pull fresh data from cloud ─────────────────────────────────
        pulled = self._pull_cloud()
        summary["pulled"] = pulled

        ts = datetime.now(timezone.utc).isoformat()
        self._last_sync_ts = ts
        self._set_meta("last_sync_ts", ts)
        summary["ts"] = ts

        self._set_status(SyncStatus.ONLINE)
        self._refresh_pending_count()

        log.info(f"Sync complete — pushed={pushed}, pulled={pulled}")
        if self._on_sync_complete:
            try:
                self._on_sync_complete(summary)
            except Exception as e:
                log.warning(f"on_sync_complete callback error: {e}")

        return summary

    # ── Push ─────────────────────────────────────────────────────────────

    def _push_outbox(self) -> int:
        """
        Send every pending outbox row to the cloud.
        Returns the number of successfully pushed operations.
        """
        with self._local_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sync_outbox WHERE retries < ? ORDER BY id ASC",
                (MAX_RETRIES,),
            ).fetchall()

        pushed = 0
        for row in rows:
            row = dict(row)
            ok, error = self._push_one(row)
            with self._local_conn() as conn:
                if ok:
                    conn.execute("DELETE FROM sync_outbox WHERE id = ?", (row["id"],))
                    pushed += 1
                else:
                    conn.execute(
                        "UPDATE sync_outbox SET retries = retries + 1, last_error = ? WHERE id = ?",
                        (error, row["id"]),
                    )
                conn.commit()

        return pushed

    def _push_one(self, row: dict) -> tuple[bool, Optional[str]]:
        """Push a single outbox row to the cloud. Returns (success, error_msg)."""
        table     = row["table_name"]
        operation = row["operation"]
        payload   = json.loads(row["payload"])

        endpoint_map = {
            # (table, operation) → (method, url_path)
            ("items",                "INSERT"):   ("POST",   "/api/sync/items"),
            ("items",                "UPDATE"):   ("PUT",    "/api/sync/items"),
            ("items",                "DELETE"):   ("DELETE", "/api/sync/items"),
            ("categories",           "INSERT"):   ("POST",   "/api/sync/categories"),
            ("categories",           "UPDATE"):   ("PUT",    "/api/sync/categories"),
            ("categories",           "DELETE"):   ("DELETE", "/api/sync/categories"),
            ("sales",                "SALE"):     ("POST",   "/api/sync/sales"),
            ("inventory_movements",  "QUANTITY"): ("POST",   "/api/sync/movements"),
            ("users",                "INSERT"):   ("POST",   "/api/sync/users"),
            ("users",                "UPDATE"):   ("PUT",    "/api/sync/users"),
        }

        key = (table, operation)
        if key not in endpoint_map:
            log.warning(f"No push mapping for {key} — skipping.")
            return True, None   # don't retry unmapped ops

        method, path = endpoint_map[key]
        url = f"{self.cloud_url}{path}"

        try:
            resp = requests.request(
                method, url,
                json={"operation": operation, "payload": payload},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code in (200, 201):
                return True, None
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.RequestException as e:
            return False, str(e)

    # ── Pull ─────────────────────────────────────────────────────────────

    def _pull_cloud(self) -> int:
        """
        Fetch latest data from the cloud and refresh the local SQLite cache.
        Returns the total number of rows upserted.
        """
        since = self._get_meta("last_sync_ts", "1970-01-01T00:00:00+00:00")
        total = 0

        pull_tasks = [
            ("/api/sync/pull/items",      self._upsert_items),
            ("/api/sync/pull/categories", self._upsert_categories),
            ("/api/sync/pull/sales",      self._upsert_sales),
            ("/api/sync/pull/movements",  self._upsert_movements),
            ("/api/sync/pull/users",      self._upsert_users),
        ]

        for path, handler in pull_tasks:
            try:
                resp = requests.get(
                    f"{self.cloud_url}{path}",
                    params={"since": since},
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code == 200:
                    rows = resp.json()
                    count = handler(rows)
                    total += count
                    log.debug(f"Pulled {count} rows from {path}")
                else:
                    log.warning(f"Pull {path} returned HTTP {resp.status_code}")
            except Exception as e:
                log.warning(f"Pull {path} failed: {e}")

        return total

    # ── Upsert handlers ───────────────────────────────────────────────────

    def _upsert_items(self, rows: list) -> int:
        if not rows:
            return 0
        with self._local_conn() as conn:
            for r in rows:
                conn.execute("""
                    INSERT INTO items
                        (id, name, sku, category_id, description, price,
                         quantity, low_stock_threshold, image_path,
                         created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name, sku=excluded.sku,
                        category_id=excluded.category_id,
                        description=excluded.description,
                        price=excluded.price, quantity=excluded.quantity,
                        low_stock_threshold=excluded.low_stock_threshold,
                        image_path=excluded.image_path,
                        updated_at=excluded.updated_at
                """, (
                    r.get("id"), r.get("name"), r.get("sku"),
                    r.get("category_id"), r.get("description"),
                    r.get("price"), r.get("quantity"),
                    r.get("low_stock_threshold", 10),
                    r.get("image_path"), r.get("created_at"), r.get("updated_at"),
                ))
            conn.commit()
        return len(rows)

    def _upsert_categories(self, rows: list) -> int:
        if not rows:
            return 0
        with self._local_conn() as conn:
            for r in rows:
                conn.execute("""
                    INSERT INTO categories (id, name, description, created_at)
                    VALUES (?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name, description=excluded.description
                """, (r.get("id"), r.get("name"), r.get("description"), r.get("created_at")))
            conn.commit()
        return len(rows)

    def _upsert_sales(self, rows: list) -> int:
        if not rows:
            return 0
        with self._local_conn() as conn:
            for r in rows:
                conn.execute("""
                    INSERT OR IGNORE INTO sales
                        (id, item_id, quantity_sold, sale_price, sale_date, user_id)
                    VALUES (?,?,?,?,?,?)
                """, (
                    r.get("id"), r.get("item_id"), r.get("quantity_sold"),
                    r.get("sale_price"), r.get("sale_date"), r.get("user_id"),
                ))
            conn.commit()
        return len(rows)

    def _upsert_movements(self, rows: list) -> int:
        if not rows:
            return 0
        with self._local_conn() as conn:
            for r in rows:
                conn.execute("""
                    INSERT OR IGNORE INTO inventory_movements
                        (id, item_id, movement_type, quantity,
                         previous_quantity, new_quantity, notes, user_id, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    r.get("id"), r.get("item_id"), r.get("movement_type"),
                    r.get("quantity"), r.get("previous_quantity"), r.get("new_quantity"),
                    r.get("notes"), r.get("user_id"), r.get("created_at"),
                ))
            conn.commit()
        return len(rows)

    def _upsert_users(self, rows: list) -> int:
        if not rows:
            return 0
        with self._local_conn() as conn:
            for r in rows:
                conn.execute("""
                    INSERT INTO users
                        (id, username, password_hash, email, created_at, is_active)
                    VALUES (?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        username=excluded.username,
                        password_hash=excluded.password_hash,
                        email=excluded.email,
                        is_active=excluded.is_active
                """, (
                    r.get("id"), r.get("username"), r.get("password_hash"),
                    r.get("email"), r.get("created_at"), r.get("is_active", 1),
                ))
            conn.commit()
        return len(rows)

    # ── Status helper ─────────────────────────────────────────────────────

    def _set_status(self, status: str) -> None:
        if self._status != status:
            self._status = status
            if self._on_status_change:
                try:
                    self._on_status_change(status)
                except Exception as e:
                    log.warning(f"on_status_change callback error: {e}")
