# cloud_sync.py
import os
import psycopg2
from database import SQLiteDatabase, PostgreSQLDatabase

class CloudSync:
    """
    Syncs data from cloud Postgres (Supabase/Neon) into local SQLite.
    Ensures dashboard can run even if cloud connection fails.
    """

    def __init__(self, sqlite_path="inventory.db"):
        self.sqlite_db = SQLiteDatabase(sqlite_path)
        self.pg_url = os.getenv("DATABASE_URL")

    def _connect_postgres(self):
        return psycopg2.connect(self.pg_url, sslmode="require")

    def sync_table(self, table_name, columns):
        """
        Sync a single table from Postgres to SQLite.
        :param table_name: name of the table (e.g., 'items')
        :param columns: list of column names to copy
        """
        try:
            # Connect to Postgres
            pg_conn = self._connect_postgres()
            pg_cur = pg_conn.cursor()
            pg_cur.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
            cloud_rows = pg_cur.fetchall()

            # Ensure local table exists
            self.sqlite_db.create_table_if_not_exists(table_name, columns)

            # Clear old local data
            self.sqlite_db.clear_table(table_name)

            # Insert cloud data locally
            self.sqlite_db.bulk_insert(table_name, columns, cloud_rows)

            print(f"✅ Synced {len(cloud_rows)} rows from {table_name}.")

        except Exception as e:
            print(f"⚠️ Sync failed for {table_name}: {e}")
        finally:
            if 'pg_conn' in locals():
                pg_conn.close()

    def sync_all(self):
        """
        Sync all relevant tables. Extend this list as needed.
        """
        tables = {
            "items": ["id", "name", "quantity", "created_at"],
            "transactions": ["id", "item_id", "change", "timestamp"],
            "users": ["id", "username", "role", "created_at"]
        }
        for table, cols in tables.items():
            self.sync_table(table, cols)
