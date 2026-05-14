"""
analytics_db.py
───────────────
Shared AnalyticsDB helper used by all analytics pages.
"""

from datetime import datetime, timedelta
from database import InventoryDatabase


class AnalyticsDB:
    """Extra queries that go beyond what InventoryDatabase already exposes."""

    def __init__(self, db: InventoryDatabase):
        self.db = db

    def _q(self, sql, params=()):
        with self.db.get_connection() as conn:
            if hasattr(conn, 'cursor_factory'):
                import psycopg2.extras
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                exec_sql = sql
            else:
                cursor = conn.cursor()
                exec_sql = sql.replace("%s", "?")
            cursor.execute(exec_sql, params)
            rows = cursor.fetchall()
            if hasattr(conn, 'cursor_factory'):
                return rows
            return [dict(row) for row in rows]

    def _q1(self, sql, params=()):
        with self.db.get_connection() as conn:
            if hasattr(conn, 'cursor_factory'):
                import psycopg2.extras
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                exec_sql = sql
            else:
                cursor = conn.cursor()
                exec_sql = sql.replace("%s", "?")
            cursor.execute(exec_sql, params)
            row = cursor.fetchone()
            if hasattr(conn, 'cursor_factory'):
                return row
            return dict(row) if row else None

    # ── Revenue / sales ──────────────────────────────────────

    def revenue_by_day(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._q("""
            SELECT DATE(sale_date) as d,
                   COALESCE(SUM(quantity_sold*sale_price),0) as rev,
                   COALESCE(SUM(quantity_sold),0) as units
            FROM sales WHERE sale_date >= %s
            GROUP BY DATE(sale_date) ORDER BY d
        """, (cutoff,))
        date_map = {str(r["d"]): (r["rev"], r["units"]) for r in rows}
        dates, revs, units = [], [], []
        for i in range(days):
            d = (datetime.now() - timedelta(days=days-1-i)).strftime("%Y-%m-%d")
            dates.append(d[-5:])
            rv, un = date_map.get(d, (0, 0))
            revs.append(float(rv))
            units.append(float(un))
        return dates, revs, units

    def revenue_by_category(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT c.name,
                   COALESCE(SUM(s.quantity_sold*s.sale_price),0) as rev,
                   COALESCE(SUM(s.quantity_sold),0) as units
            FROM categories c
            JOIN items i ON i.category_id = c.id
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= %s
            GROUP BY c.name ORDER BY rev DESC
        """, (cutoff,))

    def top_items_by_revenue(self, days, limit=10):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT i.name, i.price, i.quantity,
                   COALESCE(SUM(s.quantity_sold),0) as units_sold,
                   COALESCE(SUM(s.quantity_sold*s.sale_price),0) as revenue
            FROM items i
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= %s
            GROUP BY i.id, i.name, i.price, i.quantity
            ORDER BY revenue DESC LIMIT %s
        """, (cutoff, limit))

    # ── Inventory health ─────────────────────────────────────

    def dead_stock(self, days=30):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT i.name, i.quantity, i.price,
                   COALESCE(c.name,'Uncategorised') as cat,
                   i.quantity * i.price as tied_value
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.quantity > 0
              AND i.id NOT IN (
                  SELECT DISTINCT item_id FROM sales WHERE sale_date >= %s
              )
            ORDER BY tied_value DESC
        """, (cutoff,))

    def sell_through_rate(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT i.name, i.quantity as stock,
                   COALESCE(SUM(s.quantity_sold),0) as sold,
                   COALESCE(c.name,'Uncategorised') as cat,
                   i.price
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= %s
            GROUP BY i.id, i.name, i.quantity, c.name, i.price
            HAVING (COALESCE(SUM(s.quantity_sold),0) + i.quantity) > 0
            ORDER BY (CAST(COALESCE(SUM(s.quantity_sold),0) AS REAL) /
                     (COALESCE(SUM(s.quantity_sold),0) + i.quantity)) DESC
        """, (cutoff,))

    def restock_forecast(self, days=30):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._q("""
            SELECT i.id, i.name, i.quantity, i.low_stock_threshold,
                   COALESCE(SUM(s.quantity_sold), 0) as total_sold
            FROM items i
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= %s
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
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT movement_type, COUNT(*) as cnt, SUM(quantity) as total_qty
            FROM inventory_movements
            WHERE created_at >= %s
            GROUP BY movement_type ORDER BY total_qty DESC
        """, (cutoff,))

    def price_vs_quantity(self):
        return self._q("""
            SELECT i.name, i.price, i.quantity,
                   COALESCE(c.name,'Uncategorised') as cat
            FROM items i LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.quantity > 0
        """)

    def avg_order_value(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        row = self._q1("""
            SELECT COALESCE(AVG(quantity_sold * sale_price), 0) as aov
            FROM sales WHERE sale_date >= %s
        """, (cutoff,))
        return row["aov"] if row else 0

    def total_transactions(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        row = self._q1("SELECT COUNT(*) as n FROM sales WHERE sale_date >= %s", (cutoff,))
        return row["n"] if row else 0

    def gross_margin_by_category(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT c.name,
                   COALESCE(SUM(s.quantity_sold * s.sale_price), 0) as revenue,
                   COALESCE(SUM(s.quantity_sold * i.price * 0.6), 0) as cost
            FROM categories c
            JOIN items i ON i.category_id = c.id
            LEFT JOIN sales s ON s.item_id = i.id AND s.sale_date >= %s
            GROUP BY c.name
            HAVING COALESCE(SUM(s.quantity_sold * s.sale_price), 0) > 0
            ORDER BY (COALESCE(SUM(s.quantity_sold * s.sale_price), 0) -
                      COALESCE(SUM(s.quantity_sold * i.price * 0.6), 0)) DESC
        """, (cutoff,))
