# neon_database.py — PostgreSQLDatabase configured for Neon (cloud Postgres)
#
# Neon requires two things that a standard psycopg2 connection doesn't do by default:
#   1. sslmode=require   — all connections must be over TLS
#   2. connect_timeout   — Neon "cold starts" a compute node on first connect;
#                          give it up to 10 s before giving up
#
# This module is used by web_server.py when running on Render.
# The desktop app never talks to Neon directly — it talks to local SQLite,
# and the SyncEngine talks to the Render web server, which in turn talks to Neon.
#
# Usage (in web_server.py on Render):
#   from neon_database import NeonDatabase
#   db = NeonDatabase()            # reads DATABASE_URL from env automatically

import os
from database import PostgreSQLDatabase, DB_CONFIG

# Neon connection string format from their dashboard:
#   postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require
#
# If you copy it from Neon's dashboard it already has ?sslmode=require appended,
# but we enforce it here as a safety net.


def _neon_dsn() -> str:
    """
    Build the Neon DSN from DATABASE_URL env var.
    Appends sslmode=require if not already present.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise EnvironmentError(
            "DATABASE_URL is not set. "
            "Copy it from your Neon project dashboard → Connection Details → .env"
        )

    # Neon DSNs look like:  postgresql://...  or  postgres://...
    # psycopg2 accepts both, but needs sslmode=require for Neon.
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    return url


class NeonDatabase(PostgreSQLDatabase):
    """
    PostgreSQLDatabase subclass pre-configured for Neon.

    Differences from the base class:
    - Always uses DATABASE_URL (Neon connection string) from the environment.
    - Forces sslmode=require.
    - Sets connect_timeout=10 to handle Neon cold-start latency.
    - Increases the connection pool max to 5 (Neon free tier allows 10).
    """

    def __init__(self):
        # We bypass PostgreSQLDatabase.__init__ and call the grandparent,
        # then set up our own pool with the correct Neon parameters.
        import psycopg2
        from psycopg2 import pool, extras

        self.psycopg2 = psycopg2
        self.extras   = extras
        self.db_type  = "Neon (PostgreSQL)"

        dsn = _neon_dsn()

        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,           # Neon free tier: max 10 simultaneous connections
                dsn=dsn,
                connect_timeout=10,  # allow up to 10 s for Neon cold-start
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            print("[DB] Connected to Neon PostgreSQL ✓")
            self.init_db()
        except psycopg2.Error as e:
            print(f"[ERROR] Failed to connect to Neon: {e}")
            raise
