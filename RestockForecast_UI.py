"""
RestockForecast_UI.py
──────────────────────
Restock Forecast standalone sidebar page.
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
from charts import HBarChart, KpiCard, SectionCard


class RestockForecastPage(QWidget):
    """Restock Forecast full sidebar page."""

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

        title = QLabel("🔮  Restock Forecast")
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

        # Info banner
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame { background:#ede9fe; border:1px solid #c4b5fd;
                     border-radius:10px; }
            QLabel { background:transparent; border:none; }
        """)
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.addWidget(QLabel("🔮"))
        info = QLabel(
            "<b>Restock Forecast</b> — Based on average daily sales velocity "
            "over the selected period, this table predicts how many days of "
            "stock each item has remaining. Items highlighted in red need "
            "urgent attention.")
        info.setStyleSheet("color:#4c1d95; font-size:12px;")
        info.setWordWrap(True)
        bl.addWidget(info, 1)
        self._lay.addWidget(banner)

        # KPI row
        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(12)
        self._lay.addLayout(self.kpi_row)

        # Forecast table
        self.forecast_card = SectionCard(
            "Days Until Stockout — Sorted by Urgency")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Item", "Current Stock", "Avg Daily Sales",
            "Days Remaining", "Status", "Restock Qty Suggested"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
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

        forecast = self.adb.restock_forecast(days)
        critical = sum(1 for f in forecast if f["days_left"] < 7)
        warning = sum(1 for f in forecast if 7 <= f["days_left"] < 14)

        for icon, title, val, sub, color in [
            ("🔴", "Critical (< 7 days)", str(critical),
             "Need restock now",   "#ef4444"),
            ("🟡", "Warning (7–14 days)",  str(warning),
             "Plan restock soon",  "#f59e0b"),
            ("🟢", "Items Forecasted",     str(len(forecast)),
             "With sales data",    "#10b981"),
        ]:
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

            suggested = max(0, int(f["avg_daily"] * 30) - f["stock"])

            for col, val in enumerate([
                f["name"],
                str(f["stock"]),
                f"{f['avg_daily']:.2f}/day",
                f"{f['days_left']:.1f} days",
                status,
                str(suggested) if suggested > 0 else "—",
            ]):
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
            colors = []
            for f in forecast:
                if f["days_left"] < 7:    colors.append("#ef4444")
                elif f["days_left"] < 14: colors.append("#f59e0b")
                else:                      colors.append("#10b981")
            self.urgency_bar.set_data(
                [f["name"] for f in forecast],
                [f["days_left"] for f in forecast],
                colors)


# ── Standalone runner ────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    db = InventoryDatabase()
    win = RestockForecastPage(db)
    win.setWindowTitle("ProStock | Restock Forecast")
    win.resize(1100, 780)
    win.show()
    sys.exit(app.exec())
