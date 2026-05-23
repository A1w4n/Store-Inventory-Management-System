"""
analytics_db.py
───────────────
Extra queries on top of InventoryDatabase.
Fixes:
  1. SQLite row_factory always set → dict-style access works reliably.
  2. PostgreSQL placeholder conversion (? → %s) preserved.
  3. get_connection() called correctly for both db types.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from database import InventoryDatabase


class AnalyticsDB:
    """Extra read-only queries for the Sales Analysis UI."""

    def __init__(self, db: InventoryDatabase):
        self.db = db

    # ──────────────────────────────────────────────────────────
    # Internal query helpers
    # ──────────────────────────────────────────────────────────

    def _is_postgres(self):
        return getattr(self.db, "db_type", "").lower() == "postgresql"

    def _q(self, sql, params=()):
        """Run a SELECT and return a list of dict-like rows."""
        if self._is_postgres():
            import psycopg2.extras
            sql = sql.replace("?", "%s")
            with self.db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(sql, params)
                return cursor.fetchall()

        # ── SQLite path ──────────────────────────────────────
        # Always open a fresh connection with row_factory set
        # so r["column"] access works reliably.
        conn = self.db.get_connection()
        try:
            conn.row_factory = sqlite3.Row   # ← THE KEY FIX
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return rows
        finally:
            conn.close()

    def _q1(self, sql, params=()):
        """Run a SELECT and return a single dict-like row (or None)."""
        if self._is_postgres():
            import psycopg2.extras
            sql = sql.replace("?", "%s")
            with self.db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(sql, params)
                return cursor.fetchone()

        conn = self.db.get_connection()
        try:
            conn.row_factory = sqlite3.Row   # ← THE KEY FIX
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────
    # Revenue / sales
    # ──────────────────────────────────────────────────────────

    def revenue_by_day(self, days):
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        rows = self._q("""
            SELECT DATE(sale_date) as d,
                   COALESCE(SUM(quantity_sold * sale_price), 0) as rev,
                   COALESCE(SUM(quantity_sold), 0) as units
            FROM sales
            WHERE sale_date >= ?
            GROUP BY DATE(sale_date)
            ORDER BY d
        """, (cutoff,))

        date_map = {r["d"]: (r["rev"], r["units"]) for r in rows}
        dates, revs, units = [], [], []
        for i in range(days):
            d = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            dates.append(d[-5:])
            rv, un = date_map.get(d, (0, 0))
            revs.append(float(rv))
            units.append(float(un))
        return dates, revs, units

    def revenue_by_category(self, days):
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT c.name,
                   COALESCE(SUM(s.quantity_sold * s.sale_price), 0) as rev,
                   COALESCE(SUM(s.quantity_sold), 0) as units
            FROM categories c
            JOIN items i ON i.category_id = c.id
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= ?
            GROUP BY c.id, c.name
            ORDER BY rev DESC
        """, (cutoff,))

    def top_items_by_revenue(self, days, limit=10):
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT i.name, i.price, i.quantity,
                   COALESCE(SUM(s.quantity_sold), 0) as units_sold,
                   COALESCE(SUM(s.quantity_sold * s.sale_price), 0) as revenue
            FROM items i
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= ?
            GROUP BY i.id, i.name, i.price, i.quantity
            ORDER BY revenue DESC
            LIMIT ?
        """, (cutoff, limit))

    def avg_order_value(self, days):
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        row = self._q1("""
            SELECT COALESCE(AVG(quantity_sold * sale_price), 0) as aov
            FROM sales WHERE sale_date >= ?
        """, (cutoff,))
        return row["aov"] if row else 0

    def total_transactions(self, days):
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        row = self._q1(
            "SELECT COUNT(*) as n FROM sales WHERE sale_date >= ?", (cutoff,))
        return row["n"] if row else 0

    def gross_margin_by_category(self, days):
        """Estimates cost as 60 % of sale_price (no cost column in schema)."""
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT c.name,
                   COALESCE(SUM(s.quantity_sold * s.sale_price), 0) as revenue,
                   COALESCE(SUM(s.quantity_sold * i.price * 0.6), 0) as cost
            FROM categories c
            JOIN items i ON i.category_id = c.id
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= ?
            GROUP BY c.id
            HAVING revenue > 0
            ORDER BY (revenue - cost) DESC
        """, (cutoff,))

    # ──────────────────────────────────────────────────────────
    # Inventory health
    # ──────────────────────────────────────────────────────────

    def dead_stock(self, days=30):
        """Items with zero sales in N days that still have stock."""
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT i.name, i.quantity, i.price,
                   COALESCE(c.name, 'Uncategorised') as cat,
                   i.quantity * i.price as tied_value
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.quantity > 0
              AND i.id NOT IN (
                  SELECT DISTINCT item_id FROM sales WHERE sale_date >= ?
              )
            ORDER BY tied_value DESC
        """, (cutoff,))

    def sell_through_rate(self, days):
        """sell_through = units_sold / (units_sold + current_stock) * 100."""
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT i.name, i.quantity as stock,
                   COALESCE(SUM(s.quantity_sold), 0) as sold,
                   COALESCE(c.name, 'Uncategorised') as cat,
                   i.price
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= ?
            GROUP BY i.id, i.name, i.quantity, c.name, i.price
            HAVING (sold + stock) > 0
            ORDER BY (CAST(sold AS REAL) / (sold + stock)) DESC
        """, (cutoff,))

    def restock_forecast(self, days=30):
        """Returns top-10 items sorted by urgency (fewest days_left first)."""
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        rows = self._q("""
            SELECT i.id, i.name, i.quantity, i.low_stock_threshold,
                   COALESCE(SUM(s.quantity_sold), 0) as total_sold
            FROM items i
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= ?
            WHERE i.quantity > 0
            GROUP BY i.id, i.name, i.quantity, i.low_stock_threshold
        """, (cutoff,))

        result = []
        for r in rows:
            avg_daily = r["total_sold"] / days if days else 0
            if avg_daily > 0:
                days_left = r["quantity"] / avg_daily
                result.append({
                    "name":      r["name"],
                    "stock":     r["quantity"],
                    "avg_daily": round(avg_daily, 2),
                    "days_left": round(days_left, 1),
                    "threshold": r["low_stock_threshold"],
                })
        result.sort(key=lambda x: x["days_left"])
        return result[:10]

    def movement_type_breakdown(self, days):
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT movement_type,
                   COUNT(*) as cnt,
                   SUM(quantity) as total_qty
            FROM inventory_movements
            WHERE created_at >= ?
            GROUP BY movement_type
            ORDER BY total_qty DESC
        """, (cutoff,))

    def price_vs_quantity(self):
        """All in-stock items: price, quantity, category for scatter plot."""
        return self._q("""
            SELECT i.name, i.price, i.quantity,
                   COALESCE(c.name, 'Uncategorised') as cat
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.quantity > 0
        """)
