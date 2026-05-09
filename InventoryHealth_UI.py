"""
InventoryHealth_UI.py
──────────────────────
Inventory Health standalone sidebar page.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from database import InventoryDatabase
from analytics_db import AnalyticsDB
from charts import HBarChart, ScatterDot, KpiCard, SectionCard


class InventoryHealthPage(QWidget):
    """Inventory Health full sidebar page."""

    PERIOD_DAYS = {"7 Days": 7, "30 Days": 30, "90 Days": 90}

    def __init__(self, db: InventoryDatabase, parent=None):
        super().__init__(parent)
        self.adb = AnalyticsDB(db)
        self.current_days = 7
        self.setStyleSheet("background: #f9fafb;")
        self._build_ui()
        self.refresh()

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
                background: #ffffff; border: 1.5px solid #d1d5db;
                border-radius: 8px; padding: 6px 12px;
                font-size: 12px; color: #111827; font-weight: 600;
            }
            QComboBox:hover { border-color: #4f46e5; }
            QComboBox::drop-down { border: none; padding-right: 6px; }
            QComboBox QAbstractItemView {
                background: #ffffff; border: 1px solid #d1d5db;
                color: #374151; selection-background-color: #f3f4f6;
                selection-color: #4f46e5; outline: none;
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
                color: white; border-radius: 8px; padding: 0 16px;
                font-size: 13px; font-weight: 600; border: none;
            }
            QPushButton:hover { background: #4338ca; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        hdr_lay.addWidget(refresh_btn)
        root.addWidget(hdr_widget)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(
            "background-color: #e5e7eb; max-height: 1px; border: none;")
        root.addWidget(line)

        # ── Scroll content ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#f9fafb;")
        inner = QWidget()
        inner.setStyleSheet("background:#f9fafb;")
        self._lay = QVBoxLayout(inner)
        self._lay.setSpacing(16)
        self._lay.setContentsMargins(24, 20, 24, 24)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # KPI row
        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(12)
        self._lay.addLayout(self.kpi_row)

        # Sell-through + dead stock
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        self.st_card = SectionCard("Sell-Through Rate",
                                   "% of available stock that was sold")
        self.st_table = self._make_table(
            ["Item", "Category", "Sold", "On Hand", "Sell-Through %"])
        self.st_card.add(self.st_table)
        row1.addWidget(self.st_card, 3)

        self.dead_card = SectionCard("⚠ Dead Stock",
                                     "Items with 0 sales — capital tied up")
        self.dead_table = self._make_table(
            ["Item", "Category", "Qty", "Unit Price", "Value Tied"])
        self.dead_card.add(self.dead_table)
        row1.addWidget(self.dead_card, 3)
        self._lay.addLayout(row1)

        # Scatter + movement breakdown
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        self.scatter_card = SectionCard("Price vs Stock Quantity",
                                        "Each dot = one item")
        self.scatter = ScatterDot()
        self.scatter_card.add(self.scatter)
        row2.addWidget(self.scatter_card, 3)

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

    def _on_period_change(self, text):
        self.current_days = self.PERIOD_DAYS[text]
        self.refresh()

    def refresh(self):
        days = self.current_days

        # KPIs
        while self.kpi_row.count():
            item = self.kpi_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        dead = self.adb.dead_stock(days)
        dead_value = sum(r["tied_value"] for r in dead)
        st_rows = self.adb.sell_through_rate(days)
        avg_st = 0.0
        if st_rows:
            rates = [r["sold"] / (r["sold"] + r["stock"]) * 100
                     for r in st_rows]
            avg_st = sum(rates) / len(rates)

        for icon, title, val, sub, color in [
            ("☠️", "Dead Stock Items",  str(len(dead)),
             f"₱{dead_value:,.0f} tied up",    "#ef4444"),
            ("🔄", "Avg Sell-Through",   f"{avg_st:.1f}%",
             f"Across {len(st_rows)} items",    "#10b981"),
            ("📦", "Items Tracked",      str(len(st_rows)),
             "With sales activity",             "#6366f1"),
            ("💸", "Dead Stock Value",   f"₱{dead_value:,.2f}",
             f"Over last {days} days",          "#f59e0b"),
        ]:
            self.kpi_row.addWidget(KpiCard(icon, title, val, sub, color))

        # Sell-through table
        self.st_table.setRowCount(0)
        for row in st_rows[:15]:
            r = self.st_table.rowCount()
            self.st_table.insertRow(r)
            rate = row["sold"] / (row["sold"] + row["stock"]) * 100
            color = ("#10b981" if rate >= 50 else
                     "#f59e0b" if rate >= 20 else "#ef4444")
            for col, val in enumerate([
                row["name"], row["cat"],
                str(int(row["sold"])), str(int(row["stock"])),
                f"{rate:.1f}%"
            ]):
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignVCenter |
                    (Qt.AlignLeft if col <= 1 else Qt.AlignCenter))
                if col == 4:
                    it.setForeground(QColor(color))
                    font = QFont(); font.setBold(True); it.setFont(font)
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
        CAT_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444",
                      "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6"]
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
            mv_colors = {"SALE": "#ef4444", "RESTOCK": "#10b981",
                         "PURCHASE": "#10b981", "ADJUSTMENT": "#f59e0b",
                         "REMOVE": "#ef4444"}
            self.mv_bar.set_data(
                [r["movement_type"] for r in mv_rows],
                [float(r["total_qty"]) for r in mv_rows],
                [mv_colors.get(r["movement_type"].upper(), "#6b7280")
                 for r in mv_rows])


# ── Standalone runner ────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    db = InventoryDatabase()
    win = InventoryHealthPage(db)
    win.setWindowTitle("ProStock | Inventory Health")
    win.resize(1100, 780)
    win.show()
    sys.exit(app.exec())
