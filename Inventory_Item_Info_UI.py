import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QGridLayout, QLineEdit, 
    QScrollArea, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# --- DASHBOARD-INSPIRED COMPONENTS ---

class InventoryHeader(QFrame):
    """Aligned with the Dashboard title style"""
    def __init__(self, title, subtitle):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #111827; font-size: 30px; font-weight: 700; border: none;")
        
        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")
        
        layout.addWidget(title_lbl)
        layout.addWidget(subtitle_lbl)

class SearchFilterBar(QFrame):
    """Dashboard-style search and sort controls"""
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search inventory...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 10px 15px;
                color: #111827;
            }
            QLineEdit:focus { border: 2px solid #6366f1; }
        """)
        
        self.sort_btn = QPushButton("Sort By ▽")
        self.sort_btn.setCursor(Qt.PointingHandCursor)
        self.sort_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 10px 20px;
                color: #374151;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #f9fafb; }
        """)
        
        layout.addWidget(self.search_input)
        layout.addWidget(self.sort_btn)
        layout.addStretch()

class ItemCard(QFrame):
    """Redesigned to match DashboardCard aesthetics"""
    def __init__(self, name, sku, stock):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
            QFrame:hover {
                border: 1px solid #6366f1;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Dashboard-style Image Placeholder
        self.img_placeholder = QFrame()
        self.img_placeholder.setFixedHeight(140)
        self.img_placeholder.setStyleSheet("""
            background-color: #f3f4f6;
            border: 1px dashed #d1d5db;
            border-radius: 8px;
        """)
        img_layout = QVBoxLayout(self.img_placeholder)
        img_lbl = QLabel("Product Image")
        img_lbl.setStyleSheet("color: #9ca3af; font-size: 11px; border: none;")
        img_layout.addWidget(img_lbl, 0, Qt.AlignCenter)
        layout.addWidget(self.img_placeholder)

        # Text Details
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #111827; border: none;")
        
        sku_lbl = QLabel(f"SKU: {sku}")
        sku_lbl.setStyleSheet("font-size: 11px; color: #6b7280; border: none;")
        
        stock_lbl = QLabel(f"Stock Level: {stock}")
        stock_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #059669; border: none;")

        layout.addWidget(name_lbl)
        layout.addWidget(sku_lbl)
        layout.addWidget(stock_lbl)

        # View Detail Button (Dashboard Style)
        detail_btn = QPushButton("Manage Item")
        detail_btn.setCursor(Qt.PointingHandCursor)
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #4b5563;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #d1d5db;
            }
            QPushButton:hover { background-color: #e5e7eb; color: #111827; }
        """)
        layout.addWidget(detail_btn)

class ItemInfoPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #f9fafb;")
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(20)

        # 1. Header (Title & Subtitle)
        self.header = InventoryHeader(
            "Item Information", 
            "Manage and track your warehouse stock levels"
        )
        main_layout.addWidget(self.header)

        # 2. Search and Filter Bar
        self.controls = SearchFilterBar()
        main_layout.addWidget(self.controls)

        # 3. Exclusive Feature: Scrollable Grid Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        grid_container = QWidget()
        grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(0, 5, 5, 5)

        # Sample Data
        items = [
            ("Wireless Mouse", "WM-001", "45"), ("Mechanical Keyboard", "KB-502", "12"),
            ("USB-C Hub", "UH-99", "120"), ("Monitor Stand", "MS-10", "8"),
            ("Webcam HD", "WC-202", "30"), ("Laptop Cooling Pad", "CP-05", "15")
        ]

        for i, (name, sku, stock) in enumerate(items * 2): # Duplicated for scroll testing
            card = ItemCard(name, sku, stock)
            self.grid_layout.addWidget(card, i // 4, i % 4)

        scroll.setWidget(grid_container)
        main_layout.addWidget(scroll)

        # 4. Bottom Action Bar
        bottom_bar = QHBoxLayout()
        
        del_btn = QPushButton("🗑 Delete Item")
        del_btn.setStyleSheet("color: #ef4444; font-weight: 600; border: none; background: transparent; font-size: 13px;")
        
        add_btn = QPushButton("+ Add New Item")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 12px 25px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)

        bottom_bar.addWidget(del_btn)
        bottom_bar.addStretch()
        bottom_bar.addWidget(add_btn)
        main_layout.addLayout(bottom_bar)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = ItemInfoPage()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec())