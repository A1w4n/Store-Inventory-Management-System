import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QPushButton, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter

class DashboardCard(QFrame):
    """Reusable card component with defined outlines"""
    def __init__(self, title, content_widget=None):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background-color: white;
                border-radius: 0px;
                border: 2px solid #000000; 
            }
            QLabel { color: #1F2937; border: none; }
        """)
        
        layout = QVBoxLayout(self)
        # Reduced vertical margins for a tighter look
        layout.setContentsMargins(30, 12, 30, 12)
        
        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(title_lbl)
        
        detail_btn = QPushButton("View detail")
        detail_btn.setCursor(Qt.PointingHandCursor)
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #111827;
                color: white;
                border-radius: 0px;
                padding: 4px 10px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        header.addWidget(detail_btn, 0, Qt.AlignRight)
        layout.addLayout(header)
        
        if content_widget:
            content_widget.setStyleSheet("border: none; background: transparent;")
            layout.addWidget(content_widget)

class StatMiniCard(QFrame):
    """Small metric cards with outlines"""
    def __init__(self, icon, label):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border-radius: 0px;
                border: 2px solid #000000;
            }
            QLabel { border: none; font-size: 12px; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4) # Tighter internal spacing
        
        header = QHBoxLayout()
        header.addWidget(QLabel(label))
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("background-color: white; border-radius: 4px; padding: 2px; border: 1px solid #D1D5DB;")
        header.addWidget(icon_lbl, 0, Qt.AlignRight)
        layout.addLayout(header)
        
        bar1 = QFrame()
        bar1.setFixedHeight(4)
        bar1.setFixedWidth(40)
        bar1.setStyleSheet("background-color: #111827; border-radius: 2px; border: none;")
        layout.addWidget(bar1)
        
        bar2 = QFrame()
        bar2.setFixedHeight(4)
        bar2.setFixedWidth(60)
        bar2.setStyleSheet("background-color: #D1D5DB; border-radius: 2px; border: none;")
        layout.addWidget(bar2)

class InventoryDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Store Inventory Dashboard")
        self.resize(1100, 700) # Slightly reduced height
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Reduced Top Margin and general spacing to move content up
        main_layout.setContentsMargins(40, 10, 40, 20)
        main_layout.setSpacing(12) 

        # --- NAVBAR ---
        nav = QFrame()
        nav.setFixedHeight(60) # Reduced from 70
        nav.setStyleSheet("""
            QFrame {
                background-color: #059669; 
                border-radius: none; 
                border: 2px solid #111827;
            }
            QLabel, QPushButton { border: none; background: transparent; }
        """)
        nav_layout = QHBoxLayout(nav)
        
        logo = QLabel("ABC")
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background-color: grey; color: white; font-weight: bold; border-radius: 4px;")
        nav_layout.addWidget(logo)
        
        comp_name = QLabel("ABC Company")
        comp_name.setStyleSheet("font-weight: bold; color: #1F2937; font-size: 15px;")
        nav_layout.addWidget(comp_name)
        
        nav_layout.addStretch()
        
        links = ["Dashboard", "Item Info", "Analytics"]
        for link in links:
            btn = QPushButton(link)
            btn.setFlat(True)
            style = "color: #111827; font-weight: bold;" if link == "Dashboard" else "color: #e5e7eb;"
            btn.setStyleSheet(style + "font-size: 13px;")
            nav_layout.addWidget(btn)
        
        nav_layout.addStretch()
        avatar = QLabel("👤")
        avatar.setFixedSize(35, 35)
        avatar.setStyleSheet("background-color: #D1D5DB; border-radius: 17px;")
        avatar.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(avatar)
        
        main_layout.addWidget(nav)

        # --- TITLE SECTION ---
        title_row = QHBoxLayout()
        dash_lbl = QLabel("Dashboard")
        dash_lbl.setStyleSheet("color: white; font-size: 26px; font-weight: bold; border: none;")
        title_row.addWidget(dash_lbl)
        
        # Reduced height of the 7-day pill and tighter padding
        date_pill = QLabel("Last 7 days 📅")
        date_pill.setFixedHeight(24) 
        date_pill.setStyleSheet("""
            background-color: rgba(255, 255, 255, 230); 
            padding: 0px 8px; 
            border-radius: 4px; 
            color: #4B5563; 
            border: 1px solid #D1D5DB;
            font-size: 11px;
        """)
        title_row.addWidget(date_pill, 0, Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addLayout(title_row)

        # --- CONTENT GRIDS ---
        top_grid = QHBoxLayout()
        top_grid.setSpacing(15)

        chart_placeholder = QFrame()
        chart_placeholder.setStyleSheet("background-color: #F9FAFB; border: 2px dashed #D1D5DB; border-radius: 8px;")
        chart_placeholder.setMinimumHeight(180) # Reduced from 250 to pull everything up
        sales_card = DashboardCard("Sales", chart_placeholder)
        top_grid.addWidget(sales_card, 2)
        
        stats_container = QWidget()
        stats_grid = QGridLayout(stats_container)
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setSpacing(10) # Tighter grid spacing
        stats_grid.addWidget(StatMiniCard("📦", "Orders"), 0, 0)
        stats_grid.addWidget(StatMiniCard("👥", "Customers"), 0, 1)
        stats_grid.addWidget(StatMiniCard("📁", "Sections"), 1, 0)
        stats_grid.addWidget(StatMiniCard("🏷️", "Products"), 1, 1)
        top_grid.addWidget(stats_container, 1)
        
        main_layout.addLayout(top_grid)

        # Bottom row also tighter
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)
        bottom_row.addWidget(DashboardCard("Warehouse Details"))
        bottom_row.addWidget(DashboardCard("Best Seller"))
        main_layout.addLayout(bottom_row)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#aaa4a4")) 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = InventoryDashboard()
    window.show()
    sys.exit(app.exec())