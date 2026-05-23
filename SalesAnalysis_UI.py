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
    QAbstractItemView, QComboBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMetaObject, Slot
from PySide6.QtGui import QFont

from database import InventoryDatabase
from analytics_db import AnalyticsDB
from charts import LineChart, HBarChart, KpiCard, SectionCard



class ReportWorker(QThread):
    """Background thread that generates the Excel report."""
    finished = Signal(str)   # emits saved file path
    error    = Signal(str)

    def __init__(self, path, days, adb):
        super().__init__()
        self.path = path
        self.days = days
        self.adb  = adb

    def run(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import (Font, PatternFill, Alignment,
                                          Border, Side, GradientFill)
            from openpyxl.utils import get_column_letter
            from datetime import datetime

            wb = Workbook()
            # ── colour palette ────────────────────────────────────────────────
            PURPLE      = "4F46E5"
            PURPLE_LIGHT= "EDE9FE"
            GREEN       = "10B981"
            GREEN_LIGHT = "D1FAE5"
            GREY_HDR    = "F3F4F6"
            WHITE       = "FFFFFF"
            DARK        = "111827"
            MID         = "6B7280"
            thin = Side(style="thin", color="E5E7EB")
            bdr  = Border(left=thin, right=thin, top=thin, bottom=thin)

            def hdr_font(sz=11, bold=True, color=WHITE):
                return Font(name="Arial", size=sz, bold=bold, color=color)
            def body_font(sz=10, bold=False, color=DARK):
                return Font(name="Arial", size=sz, bold=bold, color=color)
            def purple_fill():
                return PatternFill("solid", fgColor=PURPLE)
            def light_fill(color=GREY_HDR):
                return PatternFill("solid", fgColor=color)
            def center():
                return Alignment(horizontal="center", vertical="center", wrap_text=True)
            def left():
                return Alignment(horizontal="left",   vertical="center", wrap_text=True)
            def right_align():
                return Alignment(horizontal="right",  vertical="center")

            # ── helpers ───────────────────────────────────────────────────────
            def write_section_title(ws, row, col, title, ncols):
                ws.merge_cells(start_row=row, start_column=col,
                               end_row=row, end_column=col+ncols-1)
                c = ws.cell(row=row, column=col, value=title)
                c.font  = Font(name="Arial", size=12, bold=True, color=PURPLE)
                c.fill  = light_fill(PURPLE_LIGHT)
                c.alignment = left()
                ws.row_dimensions[row].height = 22

            def write_table_header(ws, row, headers, col_start=1):
                for i, h in enumerate(headers):
                    c = ws.cell(row=row, column=col_start+i, value=h)
                    c.font      = hdr_font(10, True, WHITE)
                    c.fill      = purple_fill()
                    c.alignment = center()
                    c.border    = bdr
                ws.row_dimensions[row].height = 20

            def write_row(ws, row, values, col_start=1, alt=False):
                fill = light_fill("F9FAFB") if alt else light_fill(WHITE)
                for i, v in enumerate(values):
                    c = ws.cell(row=row, column=col_start+i, value=v)
                    c.font      = body_font()
                    c.fill      = fill
                    c.border    = bdr
                    c.alignment = right_align() if isinstance(v, (int, float)) else left()
                ws.row_dimensions[row].height = 18

            # ══════════════════════════════════════════════════════════════════
            # SHEET 1 — Summary
            # ══════════════════════════════════════════════════════════════════
            ws = wb.active
            ws.title = "Summary"
            ws.sheet_view.showGridLines = False
            ws.column_dimensions["A"].width = 32
            ws.column_dimensions["B"].width = 22

            # Title banner
            ws.merge_cells("A1:B1")
            c = ws["A1"]
            c.value     = "ProStock — Sales Analysis Report"
            c.font      = Font(name="Arial", size=16, bold=True, color=WHITE)
            c.fill      = purple_fill()
            c.alignment = center()
            ws.row_dimensions[1].height = 36

            ws.merge_cells("A2:B2")
            c = ws["A2"]
            c.value     = f"Period: Last {self.days} days   |   Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}"
            c.font      = Font(name="Arial", size=10, color=MID)
            c.fill      = light_fill(PURPLE_LIGHT)
            c.alignment = center()
            ws.row_dimensions[2].height = 18

            # KPI data
            cat_rows   = self.adb.revenue_by_category(self.days)
            total_rev  = sum(r["rev"]   for r in cat_rows)
            total_units= sum(r["units"] for r in cat_rows)
            aov        = self.adb.avg_order_value(self.days)
            txns       = self.adb.total_transactions(self.days)

            ws["A4"] = "Metric";  ws["B4"] = "Value"
            write_table_header(ws, 4, ["Metric", "Value"])
            kpis = [
                ("Total Revenue",    f"₱{total_rev:,.2f}"),
                ("Units Sold",       int(total_units)),
                ("Transactions",     txns),
                ("Avg Order Value",  f"₱{aov:,.2f}"),
            ]
            for i, (k, v) in enumerate(kpis):
                write_row(ws, 5+i, [k, v], alt=i%2==0)

            # ══════════════════════════════════════════════════════════════════
            # SHEET 2 — Daily Revenue
            # ══════════════════════════════════════════════════════════════════
            ws2 = wb.create_sheet("Daily Revenue")
            ws2.sheet_view.showGridLines = False
            for col, w in zip("ABCD", [18, 18, 18, 18]):
                ws2.column_dimensions[col].width = w

            ws2.merge_cells("A1:D1")
            c = ws2["A1"]
            c.value = "Daily Revenue & Units Sold"
            c.font  = Font(name="Arial", size=14, bold=True, color=WHITE)
            c.fill  = purple_fill()
            c.alignment = center()
            ws2.row_dimensions[1].height = 32

            write_section_title(ws2, 2, 1, f"Last {self.days} days", 4)
            write_table_header(ws2, 3, ["Date", "Revenue (₱)", "Units Sold", "Cumulative Revenue (₱)"])

            dates, revs, units = self.adb.revenue_by_day(self.days)
            running = 0
            for i, (d, r, u) in enumerate(zip(dates, revs, units)):
                running += float(r)
                row_n = 4 + i
                ws2.cell(row=row_n, column=1, value=str(d))
                ws2.cell(row=row_n, column=2, value=f"=B{row_n}")   # self-ref for formatting
                ws2.cell(row=row_n, column=3, value=int(u))
                ws2.cell(row=row_n, column=4, value=f"=SUM(B$4:B{row_n})")
                # Apply values directly (formulas above are illustrative)
                ws2.cell(row=row_n, column=2).value = float(r)
                ws2.cell(row=row_n, column=4).value = running
                write_row(ws2, row_n, [], alt=i%2==0)
                for col in range(1, 5):
                    c = ws2.cell(row=row_n, column=col)
                    c.font   = body_font()
                    c.fill   = light_fill("F9FAFB") if i%2==0 else light_fill(WHITE)
                    c.border = bdr
                    c.alignment = right_align() if col > 1 else left()

            # Totals row
            tr = 4 + len(dates)
            ws2.cell(row=tr, column=1, value="TOTAL")
            ws2.cell(row=tr, column=2, value=f"=SUM(B4:B{tr-1})")
            ws2.cell(row=tr, column=3, value=f"=SUM(C4:C{tr-1})")
            ws2.cell(row=tr, column=4, value="")
            for col in range(1, 5):
                c = ws2.cell(row=tr, column=col)
                c.font   = hdr_font(10, True, WHITE)
                c.fill   = purple_fill()
                c.border = bdr
                c.alignment = right_align() if col > 1 else left()

            # ══════════════════════════════════════════════════════════════════
            # SHEET 3 — Category Revenue
            # ══════════════════════════════════════════════════════════════════
            ws3 = wb.create_sheet("Category Revenue")
            ws3.sheet_view.showGridLines = False
            for col, w in zip("ABCDE", [24, 18, 14, 18, 16]):
                ws3.column_dimensions[col].width = w

            ws3.merge_cells("A1:E1")
            c = ws3["A1"]
            c.value = "Revenue & Margin by Category"
            c.font  = Font(name="Arial", size=14, bold=True, color=WHITE)
            c.fill  = purple_fill()
            c.alignment = center()
            ws3.row_dimensions[1].height = 32

            write_table_header(ws3, 2, ["Category", "Revenue (₱)", "Units", "Gross Margin (₱)", "Margin %"])
            margin_rows = self.adb.gross_margin_by_category(self.days)
            margin_map  = {r["name"]: r for r in margin_rows}

            for i, r in enumerate(cat_rows):
                row_n  = 3 + i
                margin = margin_map.get(r["name"], {})
                rev    = float(r["rev"])
                cost   = float(margin.get("cost", rev * 0.6))
                gm     = rev - cost
                gm_pct = (gm / rev * 100) if rev else 0

                vals = [r["name"], rev, int(r["units"]), gm, round(gm_pct, 1)]
                write_row(ws3, row_n, vals, alt=i%2==0)

                # colour margin cell red/green
                mc = ws3.cell(row=row_n, column=4)
                mc.fill = light_fill(GREEN_LIGHT) if gm >= 0 else light_fill("FEE2E2")
                mc.font = body_font(color=GREEN if gm >= 0 else "EF4444")

            # ══════════════════════════════════════════════════════════════════
            # SHEET 4 — Top Items
            # ══════════════════════════════════════════════════════════════════
            ws4 = wb.create_sheet("Top Items")
            ws4.sheet_view.showGridLines = False
            for col, w in zip("ABCDE", [30, 16, 14, 18, 18]):
                ws4.column_dimensions[col].width = w

            ws4.merge_cells("A1:E1")
            c = ws4["A1"]
            c.value = "Top Items by Revenue"
            c.font  = Font(name="Arial", size=14, bold=True, color=WHITE)
            c.fill  = purple_fill()
            c.alignment = center()
            ws4.row_dimensions[1].height = 32

            write_table_header(ws4, 2, ["Item", "Price (₱)", "Units Sold", "Revenue (₱)", "Avg Sale Price (₱)"])
            top = self.adb.top_items_by_revenue(self.days)
            for i, row in enumerate(top):
                row_n  = 3 + i
                avg_sp = (row["revenue"] / row["units_sold"] if row["units_sold"] else 0)
                write_row(ws4, row_n,
                          [row["name"], float(row["price"]),
                           int(row["units_sold"]),
                           float(row["revenue"]), round(avg_sp, 2)],
                          alt=i%2==0)
                # highlight top item
                if i == 0:
                    for col in range(1, 6):
                        ws4.cell(row=row_n, column=col).fill = light_fill(GREEN_LIGHT)
                        ws4.cell(row=row_n, column=col).font = body_font(bold=True, color=GREEN)

            wb.save(self.path)
            self.finished.emit(self.path)

        except Exception as ex:
            self.error.emit("Report generation failed: " + str(ex))

class SalesAnalysisPage(QWidget):
    """Sales Analysis full sidebar page."""

    PERIOD_DAYS = {"7 Days": 7, "30 Days": 30, "90 Days": 90}

    def __init__(self, db: InventoryDatabase, parent=None):
        super().__init__(parent)
        self._db = db                     # keep reference so we can reconnect
        self.adb = AnalyticsDB(db)
        self.current_days = 7
        self.setStyleSheet("background: #f9fafb;")
        self._build_ui()
        self.refresh()

        # QTimer must be created on the main thread — safe here since __init__
        # is always called from the Qt main thread via Dashboard_UI.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(30_000)
        self._refresh_timer.timeout.connect(self._silent_refresh)
        self._refresh_timer.start()

        # Hook into web server sale events for immediate chart updates.
        # Uses QueuedConnection so Flask thread never touches Qt widgets directly.
        try:
            from web_server import register_sale_callback
            register_sale_callback(self._on_sale_from_portal)
        except Exception:
            pass  # Standalone mode — 30s timer fallback is enough

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

        self.status_label = QLabel("Updated: —")
        self.status_label.setStyleSheet(
            "font-size: 11px; color: #9ca3af; border: none;")
        hdr_lay.addWidget(self.status_label)
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

        self.refresh_btn = QPushButton("⟳  Refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #6366f1);
                color: white; border-radius: 8px; padding: 0 16px;
                font-size: 13px; font-weight: 600; border: none;
            }
            QPushButton:hover { background: #4338ca; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        self.refresh_btn.clicked.connect(self._manual_refresh)
        hdr_lay.addWidget(self.refresh_btn)

        self.report_btn = QPushButton("📊  Generate Report")
        self.report_btn.setCursor(Qt.PointingHandCursor)
        self.report_btn.setFixedHeight(36)
        self.report_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white; border-radius: 8px; padding: 0 16px;
                font-size: 13px; font-weight: 600; border: none;
            }
            QPushButton:hover { background: #047857; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        self.report_btn.clicked.connect(self._generate_report)
        hdr_lay.addWidget(self.report_btn)
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

    def _generate_report(self):
        """Ask user where to save, then generate Excel report in background."""
        from datetime import datetime
        default_name = f"SalesReport_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Sales Report", default_name,
            "Excel Files (*.xlsx)"
        )
        if not path:
            return

        self.report_btn.setEnabled(False)
        self.report_btn.setText("⏳  Generating…")

        self._report_worker = ReportWorker(path, self.current_days, self.adb)
        self._report_worker.finished.connect(self._on_report_done)
        self._report_worker.error.connect(self._on_report_error)
        self._report_worker.start()

    def _on_report_done(self, path):
        self.report_btn.setEnabled(True)
        self.report_btn.setText("📊  Generate Report")
        import subprocess, sys, os
        msg = QMessageBox(self)
        msg.setWindowTitle("Report Ready")
        msg.setText(f"✅ Report saved successfully!")
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

    def _on_report_error(self, msg):
        self.report_btn.setEnabled(True)
        self.report_btn.setText("📊  Generate Report")
        err = QMessageBox(self)
        err.setWindowTitle("Report Error")
        err.setText("⚠️ " + msg)
        err.setStyleSheet("QLabel { color: #111827; font-size: 13px; }")
        err.exec()

    def _on_sale_from_portal(self):
        """Called from Flask thread — safely dispatches to Qt main thread."""
        QMetaObject.invokeMethod(self, "_silent_refresh", Qt.QueuedConnection)

    @Slot()
    def _silent_refresh(self):
        """Called by timer or sale callback — reconnects AnalyticsDB and reloads charts."""
        self.adb = AnalyticsDB(self._db)
        self.refresh()

    def _manual_refresh(self):
        """Called by the Refresh button — gives visual feedback + forces fresh read."""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⟳  Refreshing…")
        self.adb = AnalyticsDB(self._db)   # reconnect so SQLite row_factory is fresh
        self.refresh()
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("⟳  Refresh")

    def refresh(self):
        from datetime import datetime as _dt
        days = self.current_days

        try:
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
            # Guard against all-zero data so max() doesn't crash
            max_rev   = max(revs)   if any(revs)   else 1
            max_units = max(units)  if any(units)  else 1
            scale     = max_rev / max_units
            self.rev_chart.set_series({
                "Revenue (₱)": {"data": revs, "color": "#6366f1"},
                "Units":       {"data": [u * scale for u in units], "color": "#10b981"},
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
                colors  = ["#10b981" if m >= 0 else "#ef4444" for m in margins]
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
                    cell = QTableWidgetItem(val)
                    cell.setTextAlignment(Qt.AlignVCenter |
                        (Qt.AlignLeft if col == 0 else Qt.AlignCenter))
                    self.top_table.setItem(r, col, cell)

            # ✅ Update status label so the user can see it worked
            now = _dt.now().strftime("%I:%M:%S %p")
            self.status_label.setText(f"Updated: {now}")
            self.status_label.setStyleSheet(
                "font-size: 11px; color: #10b981; border: none;")

        except Exception as e:
            # Show error in status label instead of silently failing
            self.status_label.setText(f"⚠ Refresh failed: {e}")
            self.status_label.setStyleSheet(
                "font-size: 11px; color: #ef4444; border: none;")


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
