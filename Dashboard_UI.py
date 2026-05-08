import sys
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QStackedWidget, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from Item_Info_UI import ItemInfoPage
from Analytics_UI import AnalyticsPage, SalesAnalysisStandalonePage, InventoryHealthStandalonePage
from StaffAccess_UI import StaffAccessPage
from database import InventoryDatabase

class DashboardCard(QFrame):
    def __init__(self, title, content_widget=None):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            QLabel { color: #111827; border: none; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #374151;")
        header.addWidget(title_lbl)

        detail_btn = QPushButton("Manage")
        detail_btn.setCursor(Qt.PointingHandCursor)
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #4b5563;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #d1d5db;
            }
            QPushButton:hover { background-color: #e5e7eb; color: #111827; }
        """)
        header.addWidget(detail_btn, 0, Qt.AlignRight)
        layout.addLayout(header)

        if content_widget:
            layout.addSpacing(10)
            layout.addWidget(content_widget)

class StatMiniCard(QFrame):
    def __init__(self, icon, label, value, trend="+12%", trend_color=None):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            QLabel { border: none; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18px; color: #6366f1;")
        header.addWidget(icon_lbl)

        trend_lbl = QLabel(trend)
        if trend_color is None:
            trend_color = "#059669"  # default green
        trend_lbl.setStyleSheet(f"color: white; font-size: 10px; font-weight: bold; background: {trend_color}; padding: 2px 6px; border-radius: 10px;")
        header.addWidget(trend_lbl, 0, Qt.AlignRight)
        layout.addLayout(header)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #111827;")
        layout.addWidget(val_lbl)

        txt_lbl = QLabel(label)
        txt_lbl.setStyleSheet("font-size: 12px; color: #6b7280; font-weight: 500;")
        layout.addWidget(txt_lbl)

class BestSellerWidget(QFrame):
    def __init__(self, best_seller_data=None, saleability_increase=0):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            QLabel { border: none; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        if best_seller_data:
            # Safe unpacking with defaults
            data = list(best_seller_data) + [None] * 6
            item_id = data[0]
            item_name = data[1]
            price = data[2] if len(data) > 2 else 0
            quantity = data[3] if len(data) > 3 else 0
            image_path = data[4] if len(data) > 4 else ""
            total_sold = data[5] if len(data) > 5 else 0       
        else:
            item_name = "No Data"
            price = 0
            quantity = 0
            image_path = None
            total_sold = 0

        # Header with title and saleability badge
        header = QHBoxLayout()
        title_lbl = QLabel("⭐ Best Seller")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #111827;")
        header.addWidget(title_lbl)

        increase_color = "#10b981" if saleability_increase >= 0 else "#ef4444"
        increase_sign = "+" if saleability_increase >= 0 else ""
        trend_lbl = QLabel(f"{increase_sign}{int(saleability_increase)}%")
        trend_lbl.setStyleSheet(f"color: white; font-size: 10px; font-weight: bold; background: {increase_color}; padding: 2px 6px; border-radius: 10px;")
        header.addWidget(trend_lbl, 0, Qt.AlignRight)
        layout.addLayout(header)

        # Image
        if image_path and Path(image_path).exists():
            img = QPixmap(image_path)
            img_label = QLabel()
            img_label.setPixmap(img.scaledToWidth(120, Qt.SmoothTransformation))
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)
        else:
            placeholder = QLabel("📦")
            placeholder.setStyleSheet("font-size: 40px; text-align: center;")
            placeholder.setAlignment(Qt.AlignCenter)
            layout.addWidget(placeholder)

        # Item Name
        name_lbl = QLabel(item_name)
        name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        # Price and Stock Row
        price_stock = QHBoxLayout()
        price_lbl = QLabel(f"Php {price:.2f}")
        price_lbl.setStyleSheet("font-size: 12px; color: #10b981; font-weight: 600;")
        price_stock.addWidget(price_lbl)
        price_stock.addStretch()

        stock_lbl = QLabel(f"Stock: {quantity}")
        stock_lbl.setStyleSheet("font-size: 11px; color: #6b7280;")
        price_stock.addWidget(stock_lbl)
        layout.addLayout(price_stock)

        layout.addStretch()

# --- MAIN DASHBOARD WINDOW ---

class InventoryDashboard(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self.db = db or InventoryDatabase()
        self.setWindowTitle("ProStock | Inventory Management")
        self.resize(1240, 820)
        self.chart_widget = None
        self.best_seller_widget = None
        self.alerts_layout = None
        self.stats_layout = None
        self.date_range_days = 7
        self.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #9ca3af;
                border-radius: 5px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background-color: #4f46e5;
                border-color: #4f46e5;
            }
            QCheckBox::indicator:hover {
                border-color: #4f46e5;
            }
            QCheckBox {
                spacing: 10px;
                color: #111827;
                font-size: 13px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        self.outer_layout = QHBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)

        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("QFrame { background-color: #111827; border: none; }")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 30, 0, 30)
        
        brand_logo = QLabel(" 📦 ")
        brand_logo.setStyleSheet("color: white; font-size: 35px; font-weight: 800; padding-left: 15px;")
        sidebar_layout.addWidget(brand_logo, 0, Qt.AlignCenter)

        brand_name = QLabel("INVENTORY")
        brand_name.setStyleSheet("color: white; font-size: 20px; font-weight: 800; margin-bottom: 50px;")
        sidebar_layout.addWidget(brand_name, 0, Qt.AlignCenter)

        self.nav_buttons = {}
        nav_links = [
            ("📊 Dashboard",        0),
            ("📦 Item Info",        1),
            ("💰 Sales Analysis",   2),
            ("🏥 Inventory Health", 3),
            ("📈 Restock Forecast", 4),
            ("🔑 Staff Access",     5),
            ("⚙️ Settings",         6),
        ]
        
        for text, index in nav_links:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)

            btn.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[index] = btn

        sidebar_layout.addStretch()
        self.outer_layout.addWidget(sidebar)

        # --- STACKED CONTENT AREA ---
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #f9fafb;")
        self.dashboard_page = QWidget()
        self._setup_dashboard_page()
        
        # 0: Dashboard
        self.content_stack.addWidget(self.dashboard_page)
        
        # 1: Item Info
        self.item_info_page = ItemInfoPage(self.db)
        self.item_info_page.item_changed.connect(self._refresh_all_stats)
        self.content_stack.addWidget(self.item_info_page)
        
        # 2: Sales Analysis
        self.sales_analysis_page = SalesAnalysisStandalonePage(self.db)
        self.content_stack.addWidget(self.sales_analysis_page)
        
        # 3: Inventory Health
        self.inventory_health_page = InventoryHealthStandalonePage(self.db)
        self.content_stack.addWidget(self.inventory_health_page)
        
        # 4: Restock Forecast
        self.analytics_page = AnalyticsPage(self.db)
        self.content_stack.addWidget(self.analytics_page)   
        
        # 5: Staff Access
        self.staff_access_page = StaffAccessPage()
        self.content_stack.addWidget(self.staff_access_page)
        
        # 6: Settings
        self.content_stack.addWidget(QLabel("Settings Page Placeholder"))
        
        self.outer_layout.addWidget(self.content_stack)

        self.switch_page(0)

    def _setup_dashboard_page(self):
        layout = QVBoxLayout(self.dashboard_page)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        self.dashboard_page.setStyleSheet("background-color: #f9fafb;")

        # Title
        title = QHBoxLayout()
        t = QLabel("Dashboard")
        t.setStyleSheet("color: #111827; font-size: 40px; font-weight: 700; border: none;")
        title.addWidget(t)
        title.addStretch()

        # Line Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #111827; max-height: 10px;")

        # Date sorter with label
        sorter_row = QHBoxLayout()
        sorter_row.addStretch()
        lbl = QLabel("Data retrieved for")
        lbl.setStyleSheet("color: #374151; font-size: 13px; font-weight: 500;")
        sorter_row.addWidget(lbl)
        sorter_row.addSpacing(10)
        sorter_row.addWidget(self.date_sorter())

        # Header
        header = QHBoxLayout()
        t = QLabel("Status:")
        t.setStyleSheet("color: #111827; font-size: 25px; font-weight: 700; border: none;")
        header.addWidget(t)
        header.addStretch()

        # Get stats from database
        db_stats = self.db.get_dashboard_stats()

        # Calculate dynamic trends
        item_count_trend = self.db.get_item_count_trend(self.date_range_days)
        low_stock_count, avg_threshold = self.db.get_low_stock_status()
        sales_trend = self.db.get_sales_trend(self.date_range_days)
        saleability_increase = self.db.get_saleability_increase(self.date_range_days)

        # Determine colors based on data
        item_trend_color = "#10b981" if item_count_trend >= 0 else "#ef4444"
        item_trend_sign = "+" if item_count_trend >= 0 else ""

        low_stock_color = "#ef4444" if low_stock_count > 0 else "#10b981"
        low_stock_trend = f"{low_stock_count} High" if low_stock_count > 0 else "Good"

        sales_trend_color = "#10b981" if sales_trend >= 0 else "#ef4444"
        sales_trend_sign = "+" if sales_trend >= 0 else ""

        # Stats Row (moved above graph) - with equal sizing
        stats = QHBoxLayout()
        stats.setSpacing(20)

        stat1 = StatMiniCard("📦", "Total Items",
                            str(db_stats['total_items']),
                            f"{item_trend_sign}{int(item_count_trend)}%",
                            item_trend_color)
        stat1.setMinimumWidth(200)
        stats.addWidget(stat1)

        stat2 = StatMiniCard("⚠️", "Low Stock",
                            f"{db_stats['low_stock_items']} Items",
                            low_stock_trend,
                            low_stock_color)
        stat2.setMinimumWidth(200)
        stats.addWidget(stat2)

        stat3 = StatMiniCard("🚚", "Sold Today",
                            f"{db_stats['units_sold_today']} units",
                            f"{sales_trend_sign}{int(sales_trend)}%",
                            sales_trend_color)
        stat3.setMinimumWidth(200)
        stats.addWidget(stat3)

        best_seller_data = self.db.get_best_seller(self.date_range_days)
        self.best_seller_widget = BestSellerWidget(best_seller_data, saleability_increase)
        self.best_seller_widget.setMinimumWidth(200)
        stats.addWidget(self.best_seller_widget)

        self.stats_layout = stats

        # Content Row (graph and quick actions)
        graph = QHBoxLayout()
        graph.setSpacing(20)
        self.chart_widget = self._create_chart_widget()
        graph.addWidget(DashboardCard("Items Added & Stock", self.chart_widget), 2)

        act = DashboardCard("Quick Actions")
        act_l = QVBoxLayout()
        for a in ["Print Barcodes", "Generate Cycle Count", "Export CSV"]:
            b = QPushButton(a)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("text-align: left; padding: 10px; color: #374151; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 5px;")
            act_l.addWidget(b)

        # Access the layout of the DashboardCard
        container = QWidget()
        container.setLayout(act_l)
        act.layout().addWidget(container)
        graph.addWidget(act, 1)

        # Layout of the Dashboard card
        layout.addLayout(title)
        layout.addWidget(line)
        layout.addLayout(sorter_row)
        layout.addLayout(header)
        layout.addSpacing(2)
        layout.addLayout(stats)
        layout.addSpacing(2)
        layout.addLayout(graph, 1)

    def date_sorter(self, default_text="Last 7 Days"):
        dateSorter_btn = QPushButton(default_text)
        dateSorter_btn.setCursor(Qt.PointingHandCursor)
        dateSorter_btn.setFixedWidth(160)
        dateSorter_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;                   
            } 
            QPushButton:hover { background-color: #f9fafb; border-color: #4f46e5; }
        """)   

        dateSorter_menu = QMenu(dateSorter_btn)
        dateSorter_menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #4f46e5;
                color: white;
                border-radius: 2px;
            }
        """)
        options = ["Today", "Last 7 Days", "Last 30 Days", "Custom Range..."]
        for opt in options:
            action = QAction(opt, self)
            action.triggered.connect(lambda checked=False, text=opt, b=dateSorter_btn: self._update_date_range(text, b))
            dateSorter_menu.addAction(action)

        dateSorter_btn.setMenu(dateSorter_menu)
        return dateSorter_btn

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        
        # Refresh the active page when switching to it
        if index == 0:
            self._refresh_all_stats()
        elif index == 2:
            self.sales_analysis_page.refresh()
        elif index == 3:
            self.inventory_health_page.refresh()
    
        for btn_index, btn in self.nav_buttons.items():
            if btn_index == index:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding: 12px 40px; font-size: 13px;
                        font-weight: 600; color: #ffffff; border: none; 
                        background-color: #1f2937;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding: 12px 25px; font-size: 13px;
                        font-weight: 500; color: #9ca3af; border: none; background: transparent;
                    }
                    QPushButton:hover { background-color: #1f2937; color: #ffffff; }
                """)

    def _update_date_range(self, text, button):
        button.setText(text)

        if text == "Today":
            self.date_range_days = 1
        elif text == "Last 7 Days":
            self.date_range_days = 7
        elif text == "Last 30 Days":
            self.date_range_days = 30
        else:
            self.date_range_days = 7

        self._update_chart()
        self._refresh_all_stats()

    def _create_chart_widget(self):
        figure = Figure(figsize=(6, 3), dpi=100, facecolor='white')
        canvas = FigureCanvas(figure)
        self._plot_inventory_chart(figure)
        return canvas

    def _update_chart(self):
        if self.chart_widget and isinstance(self.chart_widget, FigureCanvas):
            figure = self.chart_widget.figure
            figure.clear()
            self._plot_inventory_chart(figure)
            self.chart_widget.draw()

    def _update_alerts(self):
        if self.alerts_layout:
            while self.alerts_layout.count():
                item = self.alerts_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            saleability_increase = self.db.get_saleability_increase(self.date_range_days)
            increase_sign = "+" if saleability_increase >= 0 else ""
            self.alerts_layout.addWidget(StatMiniCard("📈", "Saleability Increase",
                                                       f"{abs(int(saleability_increase))}%",
                                                       f"{increase_sign}{int(saleability_increase)}%"))
            self.alerts_layout.addStretch()

        if self.stats_layout and self.best_seller_widget:
            self.best_seller_widget.deleteLater()
            self.best_seller_widget = None
            best_seller_data = self.db.get_best_seller(self.date_range_days)
            self.best_seller_widget = BestSellerWidget(best_seller_data)
            self.stats_layout.addWidget(self.best_seller_widget)

    def _refresh_all_stats(self):
        if not self.stats_layout:
            return

        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        db_stats = self.db.get_dashboard_stats()
        item_count_trend = self.db.get_item_count_trend(self.date_range_days)
        low_stock_count, avg_threshold = self.db.get_low_stock_status()
        sales_trend = self.db.get_sales_trend(self.date_range_days)
        saleability_increase = self.db.get_saleability_increase(self.date_range_days)

        item_trend_color = "#10b981" if item_count_trend >= 0 else "#ef4444"
        item_trend_sign = "+" if item_count_trend >= 0 else ""
        low_stock_color = "#ef4444" if low_stock_count > 0 else "#10b981"
        low_stock_trend = f"{low_stock_count} High" if low_stock_count > 0 else "Good"
        sales_trend_color = "#10b981" if sales_trend >= 0 else "#ef4444"
        sales_trend_sign = "+" if sales_trend >= 0 else ""

        stat1 = StatMiniCard("📦", "Total Items",
                            str(db_stats['total_items']),
                            f"{item_trend_sign}{int(item_count_trend)}%",
                            item_trend_color)
        stat1.setMinimumWidth(200)
        self.stats_layout.addWidget(stat1)

        stat2 = StatMiniCard("⚠️", "Low Stock",
                            f"{db_stats['low_stock_items']} Items",
                            low_stock_trend,
                            low_stock_color)
        stat2.setMinimumWidth(200)
        self.stats_layout.addWidget(stat2)

        stat3 = StatMiniCard("🚚", "Sold Today",
                            f"{db_stats['units_sold_today']} units",
                            f"{sales_trend_sign}{int(sales_trend)}%",
                            sales_trend_color)
        stat3.setMinimumWidth(200)
        self.stats_layout.addWidget(stat3)

        if self.best_seller_widget:
            self.best_seller_widget.deleteLater()
            self.best_seller_widget = None
        best_seller_data = self.db.get_best_seller(self.date_range_days)
        self.best_seller_widget = BestSellerWidget(best_seller_data, saleability_increase)
        self.best_seller_widget.setMinimumWidth(200)
        self.stats_layout.addWidget(self.best_seller_widget)

        self._update_chart()

    def _plot_inventory_chart(self, figure):
        ax = figure.add_subplot(111)

        # Get items added per day
        items_added = self.db.get_items_added_per_day(self.date_range_days)
        if not items_added:
            ax.text(0.5, 0.5, 'No items added in selected period',
                   ha='center', va='center', transform=ax.transAxes)
            return

        # Get total stock
        total_stock = self.db.get_dashboard_stats()['total_quantity']

        # Prepare data
        dates = [item[0] for item in items_added]  # DATE strings
        counts = [item[1] for item in items_added]  # counts

        x = range(len(dates))

        # Plot bars for items added
        ax.bar(x, counts, color='#4f46e5', alpha=0.7, label='Items Added')

        # Plot horizontal line for total stock
        ax.axhline(y=total_stock, color='#10b981', linestyle='--', linewidth=2, label=f'Total Stock: {total_stock}')

        ax.set_ylabel('Count', fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(['-'.join(d.split('-')[1:]) if len(d.split('-')) >= 3 else d for d in dates], rotation=45, ha='right', fontsize=7)  # MM-DD
        ax.legend(fontsize=7, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='y', labelsize=7)
        figure.tight_layout(pad=0.5)

# Initialize UI
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    window = InventoryDashboard()
    window.show()
    sys.exit(app.exec())
