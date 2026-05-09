"""
SalesAnalysis_UI.py
────────────────────
Sales Analysis standalone sidebar page.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from database import InventoryDatabase
from analytics_db import AnalyticsDB
from charts import LineChart, HBarChart, KpiCard, SectionCard


class SalesAnalysisPage(QWidget):
    """Sales Analysis full sidebar page."""

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

        title = QLabel("💰  Sales Analysis")
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

        # Revenue + Units chart
        self.rev_card = SectionCard("Revenue & Units Sold Over Time",
                                    "Revenue (₱) vs Units shipped per day")
        self.rev_chart = LineChart()
        self.rev_chart.setMinimumHeight(200)
        self.rev_card.add(self.rev_chart)
        self._lay.addWidget(self.rev_card)

        # Category revenue + gross margin
        row2 = QHBoxLayout()
        row2.setSpacing(16)

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

        cat_rows = self.adb.revenue_by_category(days)
        total_rev = sum(r["rev"] for r in cat_rows)
        total_units = sum(r["units"] for r in cat_rows)
        aov = self.adb.avg_order_value(days)
        txns = self.adb.total_transactions(days)

        for icon, title, val, sub, color in [
            ("💰", "Total Revenue",   f"₱{total_rev:,.2f}", f"Last {days} days", "#10b981"),
            ("📦", "Units Sold",      f"{int(total_units):,}", f"Last {days} days", "#6366f1"),
            ("🧾", "Transactions",    str(txns),             f"Last {days} days", "#3b82f6"),
            ("📊", "Avg Order Value", f"₱{aov:,.2f}",        "Per transaction",  "#f59e0b"),
        ]:
            self.kpi_row.addWidget(KpiCard(icon, title, val, sub, color))

        # Revenue chart
        dates, revs, units = self.adb.revenue_by_day(days)
        self.rev_chart.set_series({
            "Revenue (₱)": {"data": revs, "color": "#6366f1"},
            "Units": {"data": [u * (max(revs)/max(units) if max(units) else 1)
                               for u in units], "color": "#10b981"},
        }, x_labels=dates)

        # Category revenue bar
        if cat_rows:
            self.cat_rev_bar.set_data(
                [r["name"] for r in cat_rows],
                [float(r["rev"]) for r in cat_rows],
                ["#6366f1"] * len(cat_rows))

        # Gross margin
        margin_rows = self.adb.gross_margin_by_category(days)
        if margin_rows:
            margins = [float(r["revenue"] - r["cost"]) for r in margin_rows]
            colors = ["#10b981" if m >= 0 else "#ef4444" for m in margins]
            self.margin_bar.set_data(
                [r["name"] for r in margin_rows], margins, colors)

        # Top items table
        top = self.adb.top_items_by_revenue(days)
        self.top_table.setRowCount(0)
        for row in top:
            r = self.top_table.rowCount()
            self.top_table.insertRow(r)
            avg_sp = (row["revenue"] / row["units_sold"]
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


# ── Standalone runner ────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    db = InventoryDatabase()
    win = SalesAnalysisPage(db)
    win.setWindowTitle("ProStock | Sales Analysis")
    win.resize(1100, 780)
    win.show()
    sys.exit(app.exec())
