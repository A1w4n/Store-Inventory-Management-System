import sys
from datetime import datetime, timedelta
from collections import defaultdict

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QSizePolicy, QGridLayout, QComboBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (QPainter, QColor, QPen, QFont,
                            QLinearGradient, QPainterPath, QBrush)

from database import InventoryDatabase


# ═══════════════════════════════════════════════════════════
#  CHART PRIMITIVES
# ═══════════════════════════════════════════════════════════

class LineChart(QWidget):
    """Smooth line chart with axis labels and optional dual series."""

    def __init__(self, series: dict = None, parent=None):
        """
        series = { "label": {"data": [...], "color": "#hex"} }
        """
        super().__init__(parent)
        self.series = series or {}
        self.x_labels: list[str] = []
        self.setMinimumHeight(160)

    def set_series(self, series: dict, x_labels: list[str] = None):
        self.series = series
        self.x_labels = x_labels or []
        self.update()

    def paintEvent(self, event):
        if not self.series:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 42, 16, 12, 28

        # Gather all values across all series for global scale
        all_vals = [v for s in self.series.values() for v in s["data"]]
        if not all_vals:
            return
        mn, mx = min(all_vals), max(all_vals)
        rng = mx - mn or 1

        n_pts = max(len(s["data"]) for s in self.series.values())
        if n_pts < 2:
            return

        def px(i):
            return pad_l + i * (w - pad_l - pad_r) / (n_pts - 1)

        def py(v):
            return pad_t + (1 - (v - mn) / rng) * (h - pad_t - pad_b)

        # Y-axis grid lines
        grid_pen = QPen(QColor("#f3f4f6"), 1)
        painter.setPen(grid_pen)
        font = QFont(); font.setPointSize(7)
        painter.setFont(font)
        for i in range(5):
            gy = pad_t + i * (h - pad_t - pad_b) / 4
            painter.setPen(grid_pen)
            painter.drawLine(int(pad_l), int(gy), int(w - pad_r), int(gy))
            val = mx - i * rng / 4
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.drawText(0, int(gy) - 7, int(pad_l) - 4, 16,
                             Qt.AlignRight | Qt.AlignVCenter,
                             f"{val:.0f}")

        # X-axis labels
        if self.x_labels and n_pts > 1:
            step = max(1, n_pts // 6)
            for i, lbl in enumerate(self.x_labels):
                if i % step == 0:
                    painter.setPen(QPen(QColor("#9ca3af")))
                    painter.drawText(int(px(i)) - 20, h - pad_b + 4, 40, 16,
                                     Qt.AlignCenter, lbl)

        # Series
        for s_data in self.series.values():
            data = s_data["data"]
            color = QColor(s_data["color"])
            if len(data) < 2:
                continue
            pts = [(px(i), py(v)) for i, v in enumerate(data)]

            # Fill
            path = QPainterPath()
            path.moveTo(pts[0][0], h - pad_b)
            for x, y in pts:
                path.lineTo(x, y)
            path.lineTo(pts[-1][0], h - pad_b)
            path.closeSubpath()
            grad = QLinearGradient(0, pad_t, 0, h - pad_b)
            c1 = QColor(color); c1.setAlpha(45)
            c2 = QColor(color); c2.setAlpha(0)
            grad.setColorAt(0, c1); grad.setColorAt(1, c2)
            painter.fillPath(path, QBrush(grad))

            # Line
            pen = QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            for i in range(len(pts) - 1):
                painter.drawLine(int(pts[i][0]), int(pts[i][1]),
                                 int(pts[i+1][0]), int(pts[i+1][1]))

            # Dots
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            for x, y in pts:
                painter.drawEllipse(int(x)-3, int(y)-3, 6, 6)


class HBarChart(QWidget):
    """Horizontal bar chart with value labels and optional color per bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels: list[str] = []
        self.values: list[float] = []
        self.colors: list[str] = []
        self.default_color = "#6366f1"
        self.setMinimumHeight(60)

    def set_data(self, labels, values, colors=None):
        self.labels = labels
        self.values = values
        self.colors = colors or [self.default_color] * len(labels)
        self.setMinimumHeight(max(60, len(labels) * 38))
        self.update()

    def paintEvent(self, event):
        if not self.values:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self.labels)
        row_h = h / n
        label_w = 140
        val_w = 52
        bar_max = w - label_w - val_w - 8
        mx = max(self.values) or 1
        font = QFont(); font.setPointSize(9)
        painter.setFont(font)

        for i, (label, val) in enumerate(zip(self.labels, self.values)):
            y = i * row_h
            bar_w = (val / mx) * bar_max
            color = QColor(self.colors[i] if i < len(self.colors) else self.default_color)

            # Label
            painter.setPen(QPen(QColor("#374151")))
            painter.drawText(0, int(y), int(label_w), int(row_h),
                             Qt.AlignVCenter | Qt.AlignLeft,
                             label[:20] + ("…" if len(label) > 20 else ""))

            # Track
            painter.setBrush(QBrush(QColor("#f3f4f6")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(label_w), int(y + row_h*0.28),
                                    int(bar_max), int(row_h*0.44), 4, 4)
            # Fill
            if bar_w > 0:
                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(int(label_w), int(y + row_h*0.28),
                                        int(bar_w), int(row_h*0.44), 4, 4)

            # Value
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(int(label_w + bar_max + 6), int(y), int(val_w), int(row_h),
                             Qt.AlignVCenter | Qt.AlignLeft,
                             f"{val:.1f}" if isinstance(val, float) and val % 1 else str(int(val)))


class MultiDonut(QWidget):
    """Multiple donut rings stacked — one per segment."""

    def __init__(self, segments: list[tuple[str,float,str]], parent=None):
        """segments = [(label, pct_0_100, color), ...]"""
        super().__init__(parent)
        self.segments = segments
        self.setFixedSize(140, 140)

    def set_segments(self, segments):
        self.segments = segments
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        ring_w = 10
        gap = 4
        n = len(self.segments)
        outer = min(w, h) - 8

        for i, (label, pct, color) in enumerate(self.segments):
            size = outer - i * (ring_w + gap) * 2
            if size < 10:
                break
            x = (w - size) // 2
            y = (h - size) // 2
            rect = QRectF(x, y, size, size)

            # Track
            pen = QPen(QColor("#e5e7eb"), ring_w, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawEllipse(rect)

            # Arc
            span = int(pct / 100 * 360 * 16)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -span)

        # Center label
        font = QFont(); font.setPointSize(8); font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#111827")))
        painter.drawText(0, 0, w, h, Qt.AlignCenter, "Stock\nMix")


class ScatterDot(QWidget):
    """Price vs Quantity scatter plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.points: list[tuple[float,float,str,str]] = []  # (x,y,label,color)
        self.setMinimumHeight(200)

    def set_points(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        if not self.points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 44, 16, 12, 28

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        xmn, xmx = min(xs), max(xs)
        ymn, ymx = min(ys), max(ys)
        xrng = xmx - xmn or 1
        yrng = ymx - ymn or 1

        def px(v): return pad_l + (v - xmn) / xrng * (w - pad_l - pad_r)
        def py(v): return pad_t + (1 - (v - ymn) / yrng) * (h - pad_t - pad_b)

        # Grid
        grid_pen = QPen(QColor("#f3f4f6"), 1)
        font = QFont(); font.setPointSize(7); painter.setFont(font)
        for i in range(5):
            gy = pad_t + i * (h - pad_t - pad_b) / 4
            painter.setPen(grid_pen)
            painter.drawLine(int(pad_l), int(gy), w - pad_r, int(gy))
            val = ymx - i * yrng / 4
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.drawText(0, int(gy)-7, pad_l-4, 16,
                             Qt.AlignRight|Qt.AlignVCenter, f"{val:.0f}")

        # Axis labels
        painter.setPen(QPen(QColor("#6b7280")))
        painter.drawText(0, h-pad_b+4, w, 20, Qt.AlignCenter, "Price (₱)")

        # Points
        for x, y, label, color in self.points:
            cx, cy = int(px(x)), int(py(y))
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor(color).darker(120), 1))
            painter.drawEllipse(cx-6, cy-6, 12, 12)
            painter.setPen(QPen(QColor("#374151")))
            font2 = QFont(); font2.setPointSize(7); painter.setFont(font2)
            painter.drawText(cx+8, cy-6, 80, 14, Qt.AlignLeft|Qt.AlignVCenter,
                             label[:12])


# ═══════════════════════════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════════════════════════

CARD_STYLE = """
    QFrame {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
    }
    QLabel { background: transparent; border: none; }
"""

def _badge(text, bg, fg="#ffffff"):
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFixedHeight(22)
    lbl.setStyleSheet(f"""
        background-color: {bg};
        color: {fg};
        border-radius: 4px;
        padding: 0 8px;
        font-size: 10px;
        font-weight: 700;
    """)
    return lbl


class KpiCard(QFrame):
    def __init__(self, icon, title, value, sub, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_STYLE)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(110)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(3)

        top = QHBoxLayout()
        ico = QLabel(icon)
        ico.setStyleSheet(f"background:{color}22; border-radius:7px; font-size:16px; padding:3px 5px;")
        ico.setFixedSize(32, 32); ico.setAlignment(Qt.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet("color:#6b7280; font-size:11px; font-weight:600;")
        top.addWidget(ico); top.addWidget(t, 1)
        lay.addLayout(top)

        self.val_lbl = QLabel(str(value))
        self.val_lbl.setStyleSheet(f"color:#111827; font-size:22px; font-weight:800;")
        lay.addWidget(self.val_lbl)

        s = QLabel(str(sub))
        s.setStyleSheet("color:#9ca3af; font-size:11px;")
        lay.addWidget(s)

    def set_value(self, v): self.val_lbl.setText(str(v))


class SectionCard(QFrame):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_STYLE)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(18, 16, 18, 18)
        self._lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-size:14px; font-weight:700; color:#111827;")
        hdr.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet("font-size:11px; color:#9ca3af;")
            hdr.addWidget(s)
        hdr.addStretch()
        self._hdr = hdr
        self._lay.addLayout(hdr)

        self.body = QVBoxLayout()
        self.body.setSpacing(6)
        self._lay.addLayout(self.body)

    def add(self, w): self.body.addWidget(w)
    def add_layout(self, l): self.body.addLayout(l)
    def add_header_widget(self, w): self._hdr.addWidget(w)


def _divider():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("background:#f3f4f6; max-height:1px; border:none;")
    return f


# ═══════════════════════════════════════════════════════════
#  ANALYTICS DATABASE HELPERS  (all done inline — no changes to database.py)
# ═══════════════════════════════════════════════════════════

class AnalyticsDB:
    """Extra queries that go beyond what InventoryDatabase already exposes."""

    def __init__(self, db: InventoryDatabase):
        self.db = db

    def _q(self, sql, params=()):
        import psycopg2.extras
        sql = sql.replace("?", "%s")
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, params)
            return cursor.fetchall()

    def _q1(self, sql, params=()):
        import psycopg2.extras
        sql = sql.replace("?", "%s")
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, params)
            return cursor.fetchone()

    # ── Revenue / sales ──────────────────────────────────────

    def revenue_by_day(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._q("""
            SELECT DATE(sale_date) as d, COALESCE(SUM(quantity_sold*sale_price),0) as rev,
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
            revs.append(float(rv)); units.append(float(un))
        return dates, revs, units

    def revenue_by_category(self, days):
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return self._q("""
            SELECT c.name, COALESCE(SUM(s.quantity_sold*s.sale_price),0) as rev,
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
        """Items with zero sales in N days and quantity > 0."""
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
        """sell_through = units_sold / (units_sold + current_stock) * 100"""
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
        """
        For each item: avg daily sales → days until stockout.
        Returns items sorted by urgency (fewest days_left first).
        """
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
                    "name": r["name"],
                    "stock": r["quantity"],
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
        """All items: price, quantity, category for scatter."""
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
        """Assumes cost = 60% of price (placeholder — no cost field in schema)."""
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


# ═══════════════════════════════════════════════════════════
#  TAB PAGES
# ═══════════════════════════════════════════════════════════

class SalesAnalysisTab(QWidget):
    def __init__(self, adb: AnalyticsDB, parent=None):
        super().__init__(parent)
        self.adb = adb
        self.setStyleSheet("background:#f9fafb;")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#f9fafb;")
        inner = QWidget(); inner.setStyleSheet("background:#f9fafb;")
        self._lay = QVBoxLayout(inner)
        self._lay.setSpacing(16)
        self._lay.setContentsMargins(0,0,0,0)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # KPI row
        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(12)
        self._lay.addLayout(self.kpi_row)

        # Revenue + Units dual chart
        self.rev_card = SectionCard("Revenue & Units Sold Over Time",
                                    "Revenue (₱) vs Units shipped per day")
        self.rev_chart = LineChart()
        self.rev_chart.setMinimumHeight(200)
        self.rev_card.add(self.rev_chart)
        self._lay.addWidget(self.rev_card)

        # Revenue by category
        row2 = QHBoxLayout(); row2.setSpacing(16)

        self.cat_rev_card = SectionCard("Revenue by Category")
        self.cat_rev_bar = HBarChart()
        self.cat_rev_card.add(self.cat_rev_bar)
        row2.addWidget(self.cat_rev_card, 3)

        self.margin_card = SectionCard("Gross Margin by Category",
                                       "Est. margin (sale − 60% cost)")
        self.margin_bar = HBarChart()
        self.margin_card.add(self.margin_bar)
        row2.addWidget(self.margin_card, 3)

        self._lay.addLayout(row2)

        # Top items table
        self.top_card = SectionCard("Top Items by Revenue")
        self.top_table = self._make_table(
            ["Item", "Price", "Units Sold", "Revenue", "Avg Sale Price"])
        self.top_card.add(self.top_table)
        self._lay.addWidget(self.top_card)

        self._lay.addStretch()

    def _make_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(headers)):
            t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("""
            QTableWidget { border:1px solid #e5e7eb; border-radius:8px;
                           gridline-color:#f3f4f6; font-size:12px; }
            QTableWidget::item { padding:6px 10px; color:#111827; }
            QTableWidget::item:selected { background:#ede9fe; color:#111827; }
            QHeaderView::section { background:#f9fafb; color:#6b7280;
                font-weight:700; font-size:11px; padding:8px 10px;
                border:none; border-bottom:1px solid #e5e7eb; }
            QTableWidget { alternate-background-color: #fafafa; }
        """)
        t.setMinimumHeight(260)
        return t

    def refresh(self, days):
        # KPIs
        while self.kpi_row.count():
            item = self.kpi_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        revenue = sum(v for _, v, _ in
                      [(r["name"], r["rev"] if "rev" in r.keys() else 0, 0)
                       for r in self.adb.revenue_by_category(days)])
        # Re-fetch cleanly
        cat_rows = self.adb.revenue_by_category(days)
        total_rev = sum(r["rev"] for r in cat_rows)
        total_units = sum(r["units"] for r in cat_rows)
        aov = self.adb.avg_order_value(days)
        txns = self.adb.total_transactions(days)

        kpis = [
            ("💰", "Total Revenue", f"₱{total_rev:,.2f}", f"Last {days} days", "#10b981"),
            ("📦", "Units Sold",    f"{int(total_units):,}",  f"Last {days} days", "#6366f1"),
            ("🧾", "Transactions",  str(txns),              f"Last {days} days", "#3b82f6"),
            ("📊", "Avg Order Value", f"₱{aov:,.2f}",        "Per transaction",  "#f59e0b"),
        ]
        for icon, title, val, sub, color in kpis:
            self.kpi_row.addWidget(KpiCard(icon, title, val, sub, color))

        # Revenue chart
        dates, revs, units = self.adb.revenue_by_day(days)
        self.rev_chart.set_series({
            "Revenue (₱)": {"data": revs, "color": "#6366f1"},
            "Units":        {"data": [u * (max(revs)/max(units) if max(units) else 1)
                                       for u in units], "color": "#10b981"},
        }, x_labels=dates)

        # Category revenue bar
        if cat_rows:
            self.cat_rev_bar.set_data(
                [r["name"] for r in cat_rows],
                [float(r["rev"]) for r in cat_rows],
                ["#6366f1"]*len(cat_rows))
        
        # Gross margin
        margin_rows = self.adb.gross_margin_by_category(days)
        if margin_rows:
            margins = [float(r["revenue"]-r["cost"]) for r in margin_rows]
            colors  = ["#10b981" if m >= 0 else "#ef4444" for m in margins]
            self.margin_bar.set_data(
                [r["name"] for r in margin_rows], margins, colors)

        # Top items table
        top = self.adb.top_items_by_revenue(days)
        self.top_table.setRowCount(0)
        for row in top:
            r = self.top_table.rowCount()
            self.top_table.insertRow(r)
            avg_sp = (row["revenue"]/row["units_sold"]
                      if row["units_sold"] else 0)
            for col, val in enumerate([
                row["name"],
                f"₱{row['price']:.2f}",
                str(int(row["units_sold"])),
                f"₱{row['revenue']:,.2f}",
                f"₱{avg_sp:.2f}",
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter |
                    (Qt.AlignLeft if col == 0 else Qt.AlignCenter))
                self.top_table.setItem(r, col, item)


class InventoryHealthTab(QWidget):
    def __init__(self, adb: AnalyticsDB, parent=None):
        super().__init__(parent)
        self.adb = adb
        self.setStyleSheet("background:#f9fafb;")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#f9fafb;")
        inner = QWidget(); inner.setStyleSheet("background:#f9fafb;")
        self._lay = QVBoxLayout(inner)
        self._lay.setSpacing(16)
        self._lay.setContentsMargins(0,0,0,0)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # KPI row
        self.kpi_row = QHBoxLayout(); self.kpi_row.setSpacing(12)
        self._lay.addLayout(self.kpi_row)

        # Sell-through + dead stock side by side
        row1 = QHBoxLayout(); row1.setSpacing(16)

        self.st_card = SectionCard("Sell-Through Rate",
                                   "% of available stock that was sold")
        self.st_table = self._make_table(["Item", "Category",
                                          "Sold", "On Hand", "Sell-Through %"])
        self.st_card.add(self.st_table)
        row1.addWidget(self.st_card, 3)

        self.dead_card = SectionCard("⚠ Dead Stock",
                                     "Items with 0 sales — capital tied up")
        self.dead_table = self._make_table(["Item", "Category",
                                            "Qty", "Unit Price", "Value Tied"])
        self.dead_card.add(self.dead_table)
        row1.addWidget(self.dead_card, 3)

        self._lay.addLayout(row1)

        # Price vs Quantity scatter
        row2 = QHBoxLayout(); row2.setSpacing(16)
        self.scatter_card = SectionCard("Price vs Stock Quantity",
                                        "Each dot = one item")
        self.scatter = ScatterDot()
        self.scatter_card.add(self.scatter)
        row2.addWidget(self.scatter_card, 3)

        # Movement breakdown
        self.mv_card = SectionCard("Movement Type Breakdown")
        self.mv_bar = HBarChart()
        self.mv_card.add(self.mv_bar)
        row2.addWidget(self.mv_card, 2)

        self._lay.addLayout(row2)
        self._lay.addStretch()

    def _make_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(headers)):
            t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("""
            QTableWidget { border:1px solid #e5e7eb; border-radius:8px;
                           gridline-color:#f3f4f6; font-size:12px; }
            QTableWidget::item { padding:6px 10px; color:#111827; }
            QTableWidget::item:selected { background:#ede9fe; color:#111827; }
            QHeaderView::section { background:#f9fafb; color:#6b7280;
                font-weight:700; font-size:11px; padding:8px 10px;
                border:none; border-bottom:1px solid #e5e7eb; }
            QTableWidget { alternate-background-color: #fafafa; }
        """)
        t.setMinimumHeight(240)
        return t

    def refresh(self, days):
        # KPIs
        while self.kpi_row.count():
            item = self.kpi_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        dead = self.adb.dead_stock(days)
        dead_value = sum(r["tied_value"] for r in dead)
        st_rows = self.adb.sell_through_rate(days)
        avg_st = 0.0
        if st_rows:
            rates = [r["sold"]/(r["sold"]+r["stock"])*100 for r in st_rows]
            avg_st = sum(rates)/len(rates)

        kpis = [
            ("☠️", "Dead Stock Items",   str(len(dead)),
             f"₱{dead_value:,.0f} tied up",    "#ef4444"),
            ("🔄", "Avg Sell-Through",    f"{avg_st:.1f}%",
             f"Across {len(st_rows)} items",    "#10b981"),
            ("📦", "Items Tracked",       str(len(st_rows)),
             "With sales activity",             "#6366f1"),
            ("💸", "Dead Stock Value",    f"₱{dead_value:,.2f}",
             f"Over last {days} days",          "#f59e0b"),
        ]
        for icon, title, val, sub, color in kpis:
            self.kpi_row.addWidget(KpiCard(icon, title, val, sub, color))

        # Sell-through table
        self.st_table.setRowCount(0)
        for row in st_rows[:15]:
            r = self.st_table.rowCount()
            self.st_table.insertRow(r)
            rate = row["sold"]/(row["sold"]+row["stock"])*100
            color = ("#10b981" if rate >= 50 else
                     "#f59e0b" if rate >= 20 else "#ef4444")
            vals = [row["name"], row["cat"],
                    str(int(row["sold"])), str(int(row["stock"])),
                    f"{rate:.1f}%"]
            for col, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignVCenter |
                    (Qt.AlignLeft if col <= 1 else Qt.AlignCenter))
                if col == 4:
                    it.setForeground(QColor(color))
                    font = QFont(); font.setBold(True)
                    it.setFont(font)
                self.st_table.setItem(r, col, it)

        # Dead stock table
        self.dead_table.setRowCount(0)
        for row in dead[:15]:
            r = self.dead_table.rowCount()
            self.dead_table.insertRow(r)
            for col, val in enumerate([
                row["name"], row["cat"],
                str(int(row["quantity"])),
                f"₱{row['price']:.2f}",
                f"₱{row['tied_value']:,.2f}",
            ]):
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignVCenter |
                    (Qt.AlignLeft if col <= 1 else Qt.AlignCenter))
                if col == 4:
                    it.setForeground(QColor("#ef4444"))
                self.dead_table.setItem(r, col, it)

        # Scatter
        CAT_COLORS = ["#6366f1","#10b981","#f59e0b","#ef4444",
                      "#3b82f6","#8b5cf6","#ec4899","#14b8a6"]
        pts_rows = self.adb.price_vs_quantity()
        cats = list(dict.fromkeys(r["cat"] for r in pts_rows))
        cat_color = {c: CAT_COLORS[i % len(CAT_COLORS)]
                     for i, c in enumerate(cats)}
        self.scatter.set_points([
            (float(r["price"]), float(r["quantity"]),
             r["name"], cat_color.get(r["cat"], "#6b7280"))
            for r in pts_rows
        ])

        # Movement breakdown
        mv_rows = self.adb.movement_type_breakdown(days)
        if mv_rows:
            mv_colors = {"SALE":"#ef4444","RESTOCK":"#10b981",
                         "PURCHASE":"#10b981","ADJUSTMENT":"#f59e0b",
                         "REMOVE":"#ef4444"}
            labels = [r["movement_type"] for r in mv_rows]
            values = [float(r["total_qty"]) for r in mv_rows]
            colors = [mv_colors.get(l.upper(), "#6b7280") for l in labels]
            self.mv_bar.set_data(labels, values, colors)


class RestockForecastTab(QWidget):
    def __init__(self, adb: AnalyticsDB, parent=None):
        super().__init__(parent)
        self.adb = adb
        self.setStyleSheet("background:#f9fafb;")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#f9fafb;")
        inner = QWidget(); inner.setStyleSheet("background:#f9fafb;")
        self._lay = QVBoxLayout(inner)
        self._lay.setSpacing(16)
        self._lay.setContentsMargins(0,0,0,0)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # Info banner
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame { background:#ede9fe; border:1px solid #c4b5fd;
                     border-radius:10px; }
            QLabel { background:transparent; border:none; }
        """)
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16,12,16,12)
        bl.addWidget(QLabel("🔮"))
        info = QLabel(
            "<b>Restock Forecast</b> — Based on average daily sales velocity over "
            "the selected period, this table predicts how many days of stock each "
            "item has remaining. Items highlighted in red need urgent attention.")
        info.setStyleSheet("color:#4c1d95; font-size:12px;")
        info.setWordWrap(True)
        bl.addWidget(info, 1)
        self._lay.addWidget(banner)

        # KPI row
        self.kpi_row = QHBoxLayout(); self.kpi_row.setSpacing(12)
        self._lay.addLayout(self.kpi_row)

        # Forecast table
        self.forecast_card = SectionCard("Days Until Stockout — Sorted by Urgency")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Item", "Current Stock", "Avg Daily Sales",
            "Days Remaining", "Status", "Restock Qty Suggested"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            self.table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { border:1px solid #e5e7eb; border-radius:8px;
                           gridline-color:#f3f4f6; font-size:12px; }
            QTableWidget::item { padding:8px 10px; color:#111827; }
            QTableWidget::item:selected { background:#ede9fe; color:#111827; }
            QHeaderView::section { background:#f9fafb; color:#6b7280;
                font-weight:700; font-size:11px; padding:8px 10px;
                border:none; border-bottom:1px solid #e5e7eb; }
            QTableWidget { alternate-background-color: #fafafa; }
        """)
        self.table.setMinimumHeight(360)
        self.forecast_card.add(self.table)
        self._lay.addWidget(self.forecast_card)

        # Urgency bar chart
        self.urgency_card = SectionCard("Days Remaining — Visual Overview")
        self.urgency_bar = HBarChart()
        self.urgency_card.add(self.urgency_bar)
        self._lay.addWidget(self.urgency_card)

        self._lay.addStretch()

    def refresh(self, days):
        while self.kpi_row.count():
            item = self.kpi_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        forecast = self.adb.restock_forecast(days)
        critical = sum(1 for f in forecast if f["days_left"] < 7)
        warning  = sum(1 for f in forecast if 7 <= f["days_left"] < 14)

        kpis = [
            ("🔴", "Critical (< 7 days)",  str(critical), "Need restock now",  "#ef4444"),
            ("🟡", "Warning (7–14 days)",   str(warning),  "Plan restock soon",  "#f59e0b"),
            ("🟢", "Items Forecasted",      str(len(forecast)), "With sales data", "#10b981"),
        ]
        for icon, title, val, sub, color in kpis:
            self.kpi_row.addWidget(KpiCard(icon, title, val, sub, color))

        # Table
        self.table.setRowCount(0)
        for f in forecast:
            r = self.table.rowCount()
            self.table.insertRow(r)

            if f["days_left"] < 7:
                status, s_color = "🔴 Critical", "#ef4444"
            elif f["days_left"] < 14:
                status, s_color = "🟡 Warning",  "#d97706"
            else:
                status, s_color = "🟢 Healthy",  "#059669"

            # Suggest restocking to 30-day supply
            suggested = max(0, int(f["avg_daily"] * 30) - f["stock"])

            vals = [
                f["name"],
                str(f["stock"]),
                f"{f['avg_daily']:.2f}/day",
                f"{f['days_left']:.1f} days",
                status,
                str(suggested) if suggested > 0 else "—",
            ]
            for col, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignVCenter |
                    (Qt.AlignLeft if col == 0 else Qt.AlignCenter))
                if col == 3:
                    it.setForeground(QColor(s_color))
                    font = QFont(); font.setBold(True); it.setFont(font)
                if col == 4:
                    it.setForeground(QColor(s_color))
                self.table.setItem(r, col, it)

        # Urgency bar
        if forecast:
            max_d = max(f["days_left"] for f in forecast)
            colors = []
            for f in forecast:
                if f["days_left"] < 7:   colors.append("#ef4444")
                elif f["days_left"] < 14: colors.append("#f59e0b")
                else:                     colors.append("#10b981")
            self.urgency_bar.set_data(
                [f["name"] for f in forecast],
                [f["days_left"] for f in forecast],
                colors)


# ═══════════════════════════════════════════════════════════
#  MAIN ANALYTICS PAGE
# ═══════════════════════════════════════════════════════════

class AnalyticsPage(QWidget):
    PERIOD_DAYS = {"7 Days": 7, "30 Days": 30, "90 Days": 90}

    def __init__(self, db: InventoryDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.adb = AnalyticsDB(db)
        self.current_days = 7
        self.setStyleSheet("background: #f9fafb;")
        self._build_ui()
        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(60_000)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────
        hdr_widget = QWidget()
        hdr_widget.setStyleSheet("background: #f9fafb;")
        hdr_lay = QHBoxLayout(hdr_widget)
        hdr_lay.setContentsMargins(24, 20, 24, 14)
        hdr_lay.setSpacing(10)

        title = QLabel("🔮  Restock Forecast")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827; border: none;")
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self.period_combo = QComboBox()
        self.period_combo.addItems(list(self.PERIOD_DAYS.keys()))
        self.period_combo.setFixedWidth(130)
        self.period_combo.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1.5px solid #d1d5db;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                color: #111827;
                font-weight: 600;
            }
            QComboBox:hover { border-color: #4f46e5; }
            QComboBox::drop-down { border: none; padding-right: 6px; }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid #d1d5db;
                color: #374151;
                selection-background-color: #f3f4f6;
                selection-color: #4f46e5;
                outline: none;
            }
        """)
        self.period_combo.currentTextChanged.connect(self._on_period_change)
        hdr_lay.addWidget(self.period_combo)

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #6366f1);
                color: white;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { background: #4338ca; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        hdr_lay.addWidget(refresh_btn)
        root.addWidget(hdr_widget)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e5e7eb; max-height: 1px; border: none;")
        root.addWidget(line)

        # ── Content ──────────────────────────────────────────
        self.restock_tab = RestockForecastTab(self.adb)
        root.addWidget(self.restock_tab, 1)

    def _on_period_change(self, text):
        self.current_days = self.PERIOD_DAYS[text]
        self.refresh()

    def refresh(self):
        self.restock_tab.refresh(self.current_days)


# ═══════════════════════════════════════════════════════════
#  SALES ANALYSIS STANDALONE SIDEBAR PAGE
# ═══════════════════════════════════════════════════════════

class SalesAnalysisStandalonePage(QWidget):
    """Sales Analysis extracted as a full sidebar page."""
    PERIOD_DAYS = {"7 Days": 7, "30 Days": 30, "90 Days": 90}

    def __init__(self, db: InventoryDatabase, parent=None):
        super().__init__(parent)
        self.adb = AnalyticsDB(db)
        self.current_days = 7
        self.setStyleSheet("background: #f9fafb;")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────
        hdr_widget = QWidget()
        hdr_widget.setStyleSheet("background: #f9fafb;")
        hdr_lay = QHBoxLayout(hdr_widget)
        hdr_lay.setContentsMargins(24, 20, 24, 14)
        hdr_lay.setSpacing(10)

        title = QLabel("💰  Sales Analysis")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827; border: none;")
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self.period_combo = QComboBox()
        self.period_combo.addItems(list(self.PERIOD_DAYS.keys()))
        self.period_combo.setFixedWidth(130)
        self.period_combo.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1.5px solid #d1d5db;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                color: #111827;
                font-weight: 600;
            }
            QComboBox:hover { border-color: #4f46e5; }
            QComboBox::drop-down { border: none; padding-right: 6px; }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid #d1d5db;
                color: #374151;
                selection-background-color: #f3f4f6;
                selection-color: #4f46e5;
                outline: none;
            }
        """)
        self.period_combo.currentTextChanged.connect(self._on_period_change)
        hdr_lay.addWidget(self.period_combo)

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #6366f1);
                color: white;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { background: #4338ca; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        hdr_lay.addWidget(refresh_btn)
        root.addWidget(hdr_widget)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e5e7eb; max-height: 1px; border: none;")
        root.addWidget(line)

        # Sales tab (has its own scroll area + padding)
        self.sales_tab = SalesAnalysisTab(self.adb)
        root.addWidget(self.sales_tab, 1)

    def _on_period_change(self, text):
        self.current_days = self.PERIOD_DAYS[text]
        self.refresh()

    def refresh(self):
        self.sales_tab.refresh(self.current_days)


# ═══════════════════════════════════════════════════════════
#  INVENTORY HEALTH STANDALONE SIDEBAR PAGE
# ═══════════════════════════════════════════════════════════

class InventoryHealthStandalonePage(QWidget):
    """Inventory Health extracted as a full sidebar page."""
    PERIOD_DAYS = {"7 Days": 7, "30 Days": 30, "90 Days": 90}

    def __init__(self, db: InventoryDatabase, parent=None):
        super().__init__(parent)
        self.adb = AnalyticsDB(db)
        self.current_days = 7
        self.setStyleSheet("background: #f9fafb;")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────
        hdr_widget = QWidget()
        hdr_widget.setStyleSheet("background: #f9fafb;")
        hdr_lay = QHBoxLayout(hdr_widget)
        hdr_lay.setContentsMargins(24, 20, 24, 14)
        hdr_lay.setSpacing(10)

        title = QLabel("🏥  Inventory Health")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #111827; border: none;")
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self.period_combo = QComboBox()
        self.period_combo.addItems(list(self.PERIOD_DAYS.keys()))
        self.period_combo.setFixedWidth(130)
        self.period_combo.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: 1.5px solid #d1d5db;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                color: #111827;
                font-weight: 600;
            }
            QComboBox:hover { border-color: #4f46e5; }
            QComboBox::drop-down { border: none; padding-right: 6px; }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid #d1d5db;
                color: #374151;
                selection-background-color: #f3f4f6;
                selection-color: #4f46e5;
                outline: none;
            }
        """)
        self.period_combo.currentTextChanged.connect(self._on_period_change)
        hdr_lay.addWidget(self.period_combo)

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #6366f1);
                color: white;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { background: #4338ca; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        hdr_lay.addWidget(refresh_btn)
        root.addWidget(hdr_widget)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(
            "background-color: #e5e7eb; max-height: 1px; border: none;")
        root.addWidget(line)

        # Health tab (has its own scroll area + padding)
        self.health_tab = InventoryHealthTab(self.adb)
        root.addWidget(self.health_tab, 1)

    def _on_period_change(self, text):
        self.current_days = self.PERIOD_DAYS[text]
        self.refresh()

    def refresh(self):
        self.health_tab.refresh(self.current_days)


# ═══════════════════════════════════════════════════════════
#  STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    db = InventoryDatabase("inventory.db")
    window = AnalyticsPage(db)
    window.setWindowTitle("ProStock | Deep Analytics")
    window.resize(1240, 820)
    window.show()
    sys.exit(app.exec())
