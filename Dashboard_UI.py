import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QPushButton, QGridLayout, QSpacerItem, 
    QSizePolicy, QStackedWidget, QLineEdit, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QFont

# --- REUSABLE COMPONENTS ---

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
        layout.setContentsMargins(20, 20, 20, 20)
        
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
    def __init__(self, icon, label, value, trend="+12%"):
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
        trend_lbl.setStyleSheet("color: #059669; font-size: 10px; font-weight: bold; background: #ecfdf5; padding: 2px 6px; border-radius: 10px;")
        header.addWidget(trend_lbl, 0, Qt.AlignRight)
        layout.addLayout(header)
        
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #111827;")
        layout.addWidget(val_lbl)
        
        txt_lbl = QLabel(label)
        txt_lbl.setStyleSheet("font-size: 12px; color: #6b7280; font-weight: 500;")
        layout.addWidget(txt_lbl)

class ItemCard(QFrame):
    """Product Card component based on the wireframe design"""
    def __init__(self, name, sku, stock):
        super().__init__()
        self.setFixedWidth(200)
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
            QFrame:hover { border: 1px solid #6366f1; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        img_placeholder = QFrame()
        img_placeholder.setFixedHeight(120)
        img_placeholder.setStyleSheet("background-color: #f3f4f6; border: 1px dashed #d1d5db; border-radius: 8px;")
        img_layout = QVBoxLayout(img_placeholder)
        img_lbl = QLabel("Product image")
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; border: none;")
        img_layout.addWidget(img_lbl)
        layout.addWidget(img_placeholder)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #111827; border: none;")
        layout.addWidget(name_lbl)
        
        sku_lbl = QLabel(f"SKU: {sku}")
        sku_lbl.setStyleSheet("font-size: 11px; color: #6b7280; border: none;")
        layout.addWidget(sku_lbl)

        stock_lbl = QLabel(f"Stock: {stock}")
        stock_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #059669; border: none;")
        layout.addWidget(stock_lbl)

        detail_btn = QPushButton("View detail")
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #f9fafb;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #f3f4f6; }
        """)
        layout.addWidget(detail_btn)

# --- MAIN DASHBOARD WINDOW ---

class InventoryDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProStock | Inventory Management")
        self.resize(1240, 820)
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
        
        brand = QLabel(" 📦 ProStock")
        brand.setStyleSheet("color: white; font-size: 20px; font-weight: 800; margin-bottom: 30px; padding-left: 20px;")
        sidebar_layout.addWidget(brand)

        self.nav_buttons = {}
        nav_links = [("📊 Dashboard", 0), ("📦 Item Info", 1), ("📈 Analytics", 2), ("⚙️ Settings", 3)]
        
        for text, index in nav_links:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left; padding: 12px 25px; font-size: 13px;
                    font-weight: 500; color: #9ca3af; border: none; background: transparent;
                }
                QPushButton:hover { background-color: #1f2937; color: #ffffff; }
            """)
            btn.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[index] = btn

        sidebar_layout.addStretch()

        # User Profile Mini
        user_box = QFrame()
        user_box.setStyleSheet("background: #1f2937; border-top: 1px solid #374151;")
        user_layout = QHBoxLayout(user_box)
        avatar = QLabel("JD")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background: #6366f1; color: white; border-radius: 16px; font-weight: bold; font-size: 10px;")
        user_layout.addWidget(avatar)
        user_info = QVBoxLayout(); user_info.addWidget(QLabel("John Doe")); user_info.addWidget(QLabel("Warehouse Mgr"))
        user_layout.addLayout(user_info)
        sidebar_layout.addWidget(user_box)

        self.outer_layout.addWidget(sidebar)

        # --- STACKED CONTENT AREA ---
        self.content_stack = QStackedWidget()
        
        # 1. Dashboard Page
        self.dashboard_page = QWidget()
        self._setup_dashboard_page()
        
        # 2. Item Info Page
        self.item_info_page = QWidget()
        self._setup_item_info_page()

        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.item_info_page)
        
        self.outer_layout.addWidget(self.content_stack)
        self.switch_page(0) # Start at Dashboard

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        for i, btn in self.nav_buttons.items():
            if i == index:
                btn.setStyleSheet("text-align: left; padding: 12px 25px; font-size: 13px; font-weight: 600; background-color: #1f2937; color: white; border-left: 4px solid #6366f1;")
            else:
                btn.setStyleSheet("text-align: left; padding: 12px 25px; font-size: 13px; font-weight: 500; color: #9ca3af; border: none; background: transparent;")

    def _setup_dashboard_page(self):
        layout = QVBoxLayout(self.dashboard_page)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(25)
        self.dashboard_page.setStyleSheet("background-color: #f9fafb;")

        # Header
        header = QHBoxLayout()
        title_v = QVBoxLayout()
        t = QLabel("Dashboard"); t.setStyleSheet("color: #111827; font-size: 30px; font-weight: 700; border: none;")
        s = QLabel("Welcome back, here is what's happening today."); s.setStyleSheet("color: #6b7280; font-size: 13px;")
        title_v.addWidget(t); title_v.addWidget(s)
        header.addLayout(title_v)
        layout.addLayout(header)

        # Stats
        stats = QHBoxLayout(); stats.setSpacing(20)
        stats.addWidget(StatMiniCard("📦", "Total Items", "1,284", "+2.5%"))
        stats.addWidget(StatMiniCard("⚠️", "Low Stock", "14 Items", "-5%"))
        stats.addWidget(StatMiniCard("🚚", "Incoming", "48 units", "+18%"))
        layout.addLayout(stats)

        # Chart Row
        mid = QHBoxLayout(); mid.setSpacing(20)
        chart = QFrame(); chart.setStyleSheet("background-color: white; border: 1px dashed #d1d5db; border-radius: 8px; min-height: 300px;")
        mid.addWidget(DashboardCard("Inventory Movements", chart), 2)
        
        act = DashboardCard("Quick Actions")
        act_l = QVBoxLayout()
        for a in ["Print Barcodes", "Generate Cycle Count", "Export CSV"]:
            b = QPushButton(a); b.setStyleSheet("text-align: left; padding: 10px; color: #374151; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 5px;")
            act_l.addWidget(b)
        act.layout().addLayout(act_l)
        mid.addWidget(act, 1)
        layout.addLayout(mid)

    def _setup_item_info_page(self):
        layout = QVBoxLayout(self.item_info_page)
        layout.setContentsMargins(35, 30, 35, 30)
        self.item_info_page.setStyleSheet("background-color: #f9fafb;")

        # Header Row (Title + Search/Filter)
        header = QHBoxLayout()
        title = QLabel("Item Information"); title.setStyleSheet("font-size: 28px; font-weight: 700; color: #111827;")
        header.addWidget(title)
        
        search_box = QHBoxLayout()
        search_input = QLineEdit(); search_input.setPlaceholderText("Search..."); search_input.setFixedWidth(200)
        search_input.setStyleSheet("padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; background: white;")
        sort_btn = QPushButton("Sort By ▽"); sort_btn.setStyleSheet("padding: 8px 15px; border: 1px solid #d1d5db; border-radius: 6px; background: white;")
        search_box.addWidget(search_input); search_box.addWidget(sort_btn)
        header.addLayout(search_box)
        layout.addLayout(header)
        layout.addSpacing(20)

        # Grid of Items in a Scroll Area
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("border: none; background: transparent;")
        grid_widget = QWidget(); grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(20)
        
        dummy_items = [("Wireless Mouse", "WM-01", "50"), ("Keyboard", "KB-02", "12"), ("Monitor", "MN-03", "5"), ("USB Hub", "UH-04", "100"), ("Webcam", "WC-05", "25")]
        for i, (n, s, st) in enumerate(dummy_items * 3): # Duplicate for scrolling
            grid_layout.addWidget(ItemCard(n, s, st), i // 4, i % 4)
            
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        # Bottom Bar
        bottom = QHBoxLayout()
        del_btn = QPushButton("🗑 Delete Item"); del_btn.setStyleSheet("color: #ef4444; font-weight: 600; border: none;")
        add_btn = QPushButton("+ Add item"); add_btn.setStyleSheet("background: #6366f1; color: white; padding: 10px 20px; border-radius: 8px; font-weight: 600;")
        bottom.addWidget(del_btn); bottom.addStretch(); bottom.addWidget(add_btn)
        layout.addLayout(bottom)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    window = InventoryDashboard()
    window.show()
    sys.exit(app.exec())
