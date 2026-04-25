import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QPushButton, QStackedWidget, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont

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
        
        brand_logo = QLabel(" 📦 ")
        brand_logo.setStyleSheet("color: white; font-size: 35px; font-weight: 800; padding-left: 15px;")
        sidebar_layout.addWidget(brand_logo, 0, Qt.AlignCenter)

        brand_name = QLabel("INVENTORY")
        brand_name.setStyleSheet("color: white; font-size: 20px; font-weight: 800; margin-bottom: 50px;")
        sidebar_layout.addWidget(brand_name, 0, Qt.AlignCenter)

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
        self.outer_layout.addWidget(sidebar)

        # --- STACKED CONTENT AREA ---
        self.content_stack = QStackedWidget()
        self.dashboard_page = QWidget()
        self._setup_dashboard_page()
        
        self.content_stack.addWidget(self.dashboard_page)
        # Adding placeholders for other pages to avoid index errors
        self.content_stack.addWidget(QLabel("Item Info Page Placeholder"))
        self.content_stack.addWidget(QLabel("Analytics Page Placeholder"))
        self.content_stack.addWidget(QLabel("Settings Page Placeholder"))
        
        self.outer_layout.addWidget(self.content_stack)

    def _setup_dashboard_page(self):
        layout = QVBoxLayout(self.dashboard_page)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(10)
        self.dashboard_page.setStyleSheet("background-color: #f9fafb;")

        header = QHBoxLayout()
        t = QLabel("Dashboard")
        t.setStyleSheet("color: #111827; font-size: 32px; font-weight: 700; border: none;")
        header.addWidget(t)
        header.addStretch()
        header.addWidget(self.date_sorter())

        # Line Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e5e7eb; max-height: 1px;")

        # Stats Row
        stats = QHBoxLayout()
        stats.setSpacing(20)
        stats.addWidget(StatMiniCard("📦", "Total Items", "1,284", "+2.5%"))
        stats.addWidget(StatMiniCard("⚠️", "Low Stock", "14 Items", "-5%"))
        stats.addWidget(StatMiniCard("🚚", "Incoming", "48 units", "+18%"))

        # Content Row
        mid = QHBoxLayout()
        mid.setSpacing(20)
        chart_placeholder = QFrame()
        chart_placeholder.setStyleSheet("background-color: white; border: 1px dashed #d1d5db; border-radius: 8px; min-height: 300px;")
        mid.addWidget(DashboardCard("Inventory Movements", chart_placeholder), 2)
        
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
        mid.addWidget(act, 1)

        layout.addLayout(header)
        layout.addWidget(line)
        layout.addSpacing(10)
        layout.addLayout(stats)
        layout.addLayout(mid)
        layout.addStretch(1)

    def date_sorter(self, default_text="Last 7 Days"):
        date_btn = QPushButton(default_text)
        date_btn.setCursor(Qt.PointingHandCursor)
        date_btn.setFixedWidth(160)
        date_btn.setStyleSheet("""
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

        date_menu = QMenu(self)
        options = ["Today", "Last 7 Days", "Last 30 Days", "Custom Range..."]
        for opt in options:
            action = QAction(opt, self)
            action.triggered.connect(lambda checked=False, text=opt, b=date_btn: self._update_date_range(text, b))
            date_menu.addAction(action)

        date_btn.setMenu(date_menu)
        return date_btn

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)

    def _update_date_range(self, text, button):
        button.setText(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    window = InventoryDashboard()
    window.show()
    sys.exit(app.exec())
