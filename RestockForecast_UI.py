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
    QAbstractItemView, QComboBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont

from database import InventoryDatabase
from analytics_db import AnalyticsDB
from charts import HBarChart, KpiCard, SectionCard



class RestockPlanWorker(QThread):
    """Generates the Restock Plan Excel file in the background."""
    finished = Signal(str)
    error    = Signal(str)

    def __init__(self, path, days, adb):
        super().__init__()
        self.path = path
        self.days = days
        self.adb  = adb

    def run(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from datetime import datetime, timedelta

            wb = Workbook()

            # ── palette ───────────────────────────────────────────────────────
            PURPLE       = "4F46E5"
            PURPLE_LIGHT = "EDE9FE"
            GREEN        = "10B981"
            GREEN_LIGHT  = "D1FAE5"
            RED          = "EF4444"
            RED_LIGHT    = "FEE2E2"
            AMBER        = "F59E0B"
            AMBER_LIGHT  = "FEF3C7"
            WHITE        = "FFFFFF"
            DARK         = "111827"
            MID          = "6B7280"
            thin = Side(style="thin", color="E5E7EB")
            bdr  = Border(left=thin, right=thin, top=thin, bottom=thin)

            def hdr_font(sz=10, color=WHITE):
                return Font(name="Arial", size=sz, bold=True, color=color)
            def body_font(sz=10, bold=False, color=DARK):
                return Font(name="Arial", size=sz, bold=bold, color=color)
            def fill(color):
                return PatternFill("solid", fgColor=color)
            def center():
                return Alignment(horizontal="center", vertical="center", wrap_text=True)
            def left():
                return Alignment(horizontal="left", vertical="center", wrap_text=True)
            def right_al():
                return Alignment(horizontal="right", vertical="center")

            def banner(ws, text, ncols, fill_color=PURPLE):
                ws.merge_cells(start_row=1, start_column=1,
                               end_row=1, end_column=ncols)
                c = ws.cell(row=1, column=1, value=text)
                c.font = Font(name="Arial", size=14, bold=True, color=WHITE)
                c.fill = fill(fill_color); c.alignment = center()
                ws.row_dimensions[1].height = 32

            def subtitle(ws, text, ncols):
                ws.merge_cells(start_row=2, start_column=1,
                               end_row=2, end_column=ncols)
                c = ws.cell(row=2, column=1, value=text)
                c.font = Font(name="Arial", size=10, color=MID)
                c.fill = fill(PURPLE_LIGHT); c.alignment = center()
                ws.row_dimensions[2].height = 16

            def table_hdr(ws, row, headers, col_start=1):
                for i, h in enumerate(headers):
                    c = ws.cell(row=row, column=col_start+i, value=h)
                    c.font = hdr_font(); c.fill = fill(PURPLE)
                    c.alignment = center(); c.border = bdr
                ws.row_dimensions[row].height = 22

            def table_row(ws, row, values, col_start=1, alt=False,
                          row_fill=None):
                bg = row_fill or (fill("F9FAFB") if alt else fill(WHITE))
                for i, v in enumerate(values):
                    c = ws.cell(row=row, column=col_start+i, value=v)
                    c.font = body_font(); c.fill = bg; c.border = bdr
                    c.alignment = right_al() if isinstance(v,(int,float)) else left()
                ws.row_dimensions[row].height = 18

            now      = datetime.now()
            now_str  = now.strftime("%B %d, %Y %H:%M")
            forecast = self.adb.restock_forecast(self.days)

            # split by urgency
            critical = [f for f in forecast if f["days_left"] <  7]
            warning  = [f for f in forecast if 7  <= f["days_left"] < 14]
            healthy  = [f for f in forecast if f["days_left"] >= 14]

            # ══════════════════════════════════════════════════════════════════
            # SHEET 1 — Restock Action Plan  (the "what to order" sheet)
            # ══════════════════════════════════════════════════════════════════
            ws = wb.active
            ws.title = "Restock Action Plan"
            ws.sheet_view.showGridLines = False
            col_widths = [32, 16, 16, 16, 18, 20, 20]
            for i, w in enumerate(col_widths, 1):
                from openpyxl.utils import get_column_letter
                ws.column_dimensions[get_column_letter(i)].width = w

            banner(ws, "🛒  ProStock — Restock Action Plan", 7)
            subtitle(ws, f"Generated: {now_str}   |   Based on last {self.days} days sales velocity", 7)

            # instructions row
            ws.merge_cells("A3:G3")
            c = ws["A3"]
            c.value = ("Fill in the 'Order Qty' column (col G) with your actual "
                       "order quantities. Suggested quantities are pre-filled based on "
                       "30-day demand. Highlight rows in RED = order immediately.")
            c.font = Font(name="Arial", size=9, italic=True, color="4C1D95")
            c.fill = fill(PURPLE_LIGHT); c.alignment = left()
            ws.row_dimensions[3].height = 14

            headers = ["Item", "Current Stock", "Avg Daily Sales",
                       "Days Remaining", "Status",
                       "Suggested Order Qty", "Actual Order Qty ✏️"]
            table_hdr(ws, 4, headers)

            all_items = critical + warning + healthy
            for i, f in enumerate(all_items):
                row_n     = 5 + i
                days_left = f["days_left"]
                suggested = max(1, int(f["avg_daily"] * 30))

                if days_left < 7:
                    status   = "🔴 CRITICAL — Order Now"
                    row_fill = fill(RED_LIGHT)
                    st_color = RED
                elif days_left < 14:
                    status   = "🟡 WARNING — Order Soon"
                    row_fill = fill(AMBER_LIGHT)
                    st_color = AMBER
                else:
                    status   = "🟢 Healthy"
                    row_fill = None
                    st_color = GREEN

                vals = [
                    f["name"],
                    int(f["stock"]),
                    round(float(f["avg_daily"]), 2),
                    round(float(days_left), 1),
                    status,
                    suggested,
                    suggested,   # pre-fill actual = suggested; staff can edit
                ]
                table_row(ws, row_n, vals, alt=i%2==0, row_fill=row_fill)

                # colour status + days cells
                ws.cell(row=row_n, column=4).font = body_font(bold=True, color=st_color)
                ws.cell(row=row_n, column=5).font = body_font(bold=True, color=st_color)

                # make Actual Order Qty column stand out (editable intent)
                edit_cell = ws.cell(row=row_n, column=7)
                edit_cell.fill      = fill("FEFCE8")
                edit_cell.font      = body_font(bold=True, color="92400E")
                edit_cell.alignment = center()

            # Totals
            tr = 5 + len(all_items)
            ws.cell(row=tr, column=1, value="TOTALS")
            ws.cell(row=tr, column=2, value=f"=SUM(B5:B{tr-1})")
            ws.cell(row=tr, column=6, value=f"=SUM(F5:F{tr-1})")
            ws.cell(row=tr, column=7, value=f"=SUM(G5:G{tr-1})")
            for col in range(1, 8):
                c = ws.cell(row=tr, column=col)
                c.font = hdr_font(); c.fill = fill(PURPLE)
                c.border = bdr
                c.alignment = right_al() if col > 1 else left()
            ws.row_dimensions[tr].height = 20

            # ══════════════════════════════════════════════════════════════════
            # SHEET 2 — Critical Items  (red urgency)
            # ══════════════════════════════════════════════════════════════════
            ws2 = wb.create_sheet("🔴 Critical")
            ws2.sheet_view.showGridLines = False
            for i, w in enumerate([32,16,16,16,18], 1):
                from openpyxl.utils import get_column_letter
                ws2.column_dimensions[get_column_letter(i)].width = w

            banner(ws2, "🔴  CRITICAL — Must Restock Within 7 Days", 5, RED)
            subtitle(ws2, f"{len(critical)} items need immediate attention", 5)
            table_hdr(ws2, 3, ["Item","Current Stock","Avg Daily Sales",
                                "Days Remaining","Suggested Order Qty"])

            if critical:
                for i, f in enumerate(critical):
                    row_n     = 4 + i
                    suggested = max(1, int(f["avg_daily"] * 30))
                    table_row(ws2, row_n,
                              [f["name"], int(f["stock"]),
                               round(float(f["avg_daily"]),2),
                               round(float(f["days_left"]),1), suggested],
                              row_fill=fill(RED_LIGHT))
                    for col in [4]:
                        ws2.cell(row=row_n,column=col).font=body_font(bold=True,color=RED)
                tr2 = 4 + len(critical)
                ws2.cell(row=tr2,column=1,value="TOTAL")
                ws2.cell(row=tr2,column=5,value=f"=SUM(E4:E{tr2-1})")
                for col in range(1,6):
                    c=ws2.cell(row=tr2,column=col)
                    c.font=hdr_font(color=WHITE); c.fill=fill(RED)
                    c.border=bdr; c.alignment=right_al() if col>1 else left()
            else:
                ws2.merge_cells("A4:E4")
                c = ws2["A4"]
                c.value = "✅ No critical items — all stock levels are healthy!"
                c.font  = body_font(bold=True, color=GREEN)
                c.fill  = fill(GREEN_LIGHT); c.alignment = center()

            # ══════════════════════════════════════════════════════════════════
            # SHEET 3 — Warning Items
            # ══════════════════════════════════════════════════════════════════
            ws3 = wb.create_sheet("🟡 Warning")
            ws3.sheet_view.showGridLines = False
            for i, w in enumerate([32,16,16,16,18], 1):
                from openpyxl.utils import get_column_letter
                ws3.column_dimensions[get_column_letter(i)].width = w

            banner(ws3, "🟡  WARNING — Restock Within 7–14 Days", 5, AMBER)
            subtitle(ws3, f"{len(warning)} items need restocking soon", 5)
            table_hdr(ws3, 3, ["Item","Current Stock","Avg Daily Sales",
                                "Days Remaining","Suggested Order Qty"])

            if warning:
                for i, f in enumerate(warning):
                    row_n     = 4 + i
                    suggested = max(1, int(f["avg_daily"] * 30))
                    table_row(ws3, row_n,
                              [f["name"], int(f["stock"]),
                               round(float(f["avg_daily"]),2),
                               round(float(f["days_left"]),1), suggested],
                              row_fill=fill(AMBER_LIGHT))
                    ws3.cell(row=row_n,column=4).font=body_font(bold=True,color=AMBER)
                tr3 = 4 + len(warning)
                ws3.cell(row=tr3,column=1,value="TOTAL")
                ws3.cell(row=tr3,column=5,value=f"=SUM(E4:E{tr3-1})")
                for col in range(1,6):
                    c=ws3.cell(row=tr3,column=col)
                    c.font=hdr_font(color=WHITE); c.fill=fill(AMBER)
                    c.border=bdr; c.alignment=right_al() if col>1 else left()
            else:
                ws3.merge_cells("A4:E4")
                c = ws3["A4"]
                c.value = "✅ No warning items!"
                c.font  = body_font(bold=True, color=GREEN)
                c.fill  = fill(GREEN_LIGHT); c.alignment = center()

            # ══════════════════════════════════════════════════════════════════
            # SHEET 4 — Healthy Items
            # ══════════════════════════════════════════════════════════════════
            ws4 = wb.create_sheet("🟢 Healthy")
            ws4.sheet_view.showGridLines = False
            for i, w in enumerate([32,16,16,16,18], 1):
                from openpyxl.utils import get_column_letter
                ws4.column_dimensions[get_column_letter(i)].width = w

            banner(ws4, "🟢  HEALTHY — Stock Levels OK (14+ Days)", 5, GREEN)
            subtitle(ws4, f"{len(healthy)} items have sufficient stock", 5)
            table_hdr(ws4, 3, ["Item","Current Stock","Avg Daily Sales",
                                "Days Remaining","Suggested Order Qty"])

            for i, f in enumerate(healthy):
                row_n     = 4 + i
                suggested = max(1, int(f["avg_daily"] * 30))
                table_row(ws4, row_n,
                          [f["name"], int(f["stock"]),
                           round(float(f["avg_daily"]),2),
                           round(float(f["days_left"]),1), suggested],
                          alt=i%2==0)
                ws4.cell(row=row_n,column=4).font=body_font(bold=True,color=GREEN)

            wb.save(self.path)
            self.finished.emit(self.path)

        except Exception as ex:
            self.error.emit("Restock plan generation failed: " + str(ex))

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

        self.plan_btn = QPushButton("🛒  Generate Restock Plan")
        self.plan_btn.setCursor(Qt.PointingHandCursor)
        self.plan_btn.setFixedHeight(36)
        self.plan_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f59e0b, stop:1 #d97706);
                color: white; border-radius: 8px; padding: 0 16px;
                font-size: 13px; font-weight: 600; border: none;
            }
            QPushButton:hover { background: #b45309; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        self.plan_btn.clicked.connect(self._generate_plan)
        hdr_lay.addWidget(self.plan_btn)
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

    def _generate_plan(self):
        from datetime import datetime
        default_name = f"RestockPlan_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Restock Plan", default_name,
            "Excel Files (*.xlsx)"
        )
        if not path:
            return

        self.plan_btn.setEnabled(False)
        self.plan_btn.setText("⏳  Generating…")

        self._plan_worker = RestockPlanWorker(path, self.current_days, self.adb)
        self._plan_worker.finished.connect(self._on_plan_done)
        self._plan_worker.error.connect(self._on_plan_error)
        self._plan_worker.start()

    def _on_plan_done(self, path):
        self.plan_btn.setEnabled(True)
        self.plan_btn.setText("🛒  Generate Restock Plan")
        import subprocess, sys, os
        msg = QMessageBox(self)
        msg.setWindowTitle("Restock Plan Ready")
        msg.setText("✅ Restock plan saved successfully!")
        msg.setInformativeText(path)
        msg.setStandardButtons(QMessageBox.Open | QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Open)
        msg.setStyleSheet("QLabel { color: #111827; font-size: 13px; }")
        if msg.exec() == QMessageBox.Open:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])

    def _on_plan_error(self, msg):
        self.plan_btn.setEnabled(True)
        self.plan_btn.setText("🛒  Generate Restock Plan")
        err = QMessageBox(self)
        err.setWindowTitle("Plan Generation Error")
        err.setText("⚠️ " + msg)
        err.setStyleSheet("QLabel { color: #111827; font-size: 13px; }")
        err.exec()

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
