import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,  
    QLineEdit, QPushButton, QScrollArea, QFrame, QMenu, QStackedWidget, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

class ItemRow(QFrame):
    # For List
    def __init__(self):
        super().__init__()
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QFrame { background-color: white; border-radius: 10px; border: 1px solid #e5e7eb; }
            QFrame:hover { border: 1px solid #10b981; }
        """)
        layout = QHBoxLayout(self)
        img = QFrame(); img.setFixedSize(60, 60)
        img.setStyleSheet("background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 6px;")
        layout.addWidget(img)
        
        info = QVBoxLayout()
        t = QFrame(); t.setFixedSize(150, 12); t.setStyleSheet("background-color: #f3f4f6; border-radius: 4px;")
        d = QFrame(); d.setFixedSize(100, 10); d.setStyleSheet("background-color: #f9fafb; border-radius: 4px;")
        info.addWidget(t); info.addWidget(d)
        layout.addLayout(info); layout.addStretch()
        
        btn = QPushButton("⋮")
        btn.setFixedSize(30, 30)
        btn.setStyleSheet("border: none; font-size: 18px; color: #6b7280;")
        layout.addWidget(btn)

class ItemCard(QFrame):
    # For Grid
    def __init__(self):
        super().__init__()
        self.setFixedSize(180, 220)
        self.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #e5e7eb; }
            QFrame:hover { border: 1px solid #10b981; }
        """)
        layout = QVBoxLayout(self)
        img = QFrame(); img.setStyleSheet("background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 8px;")
        layout.addWidget(img, 3)
        
        t = QFrame(); t.setFixedHeight(12); t.setStyleSheet("background-color: #f3f4f6; border-radius: 4px;")
        d = QFrame(); d.setFixedHeight(10); d.setStyleSheet("background-color: #f9fafb; border-radius: 4px;")
        layout.addWidget(t); layout.addWidget(d)
        
        btn = QPushButton("View Detail")
        btn.setStyleSheet("background: #f3f4f6; color: #4b5563; font-size: 11px; font-weight: bold; padding: 5px; border-radius: 4px; border: none;")
        layout.addWidget(btn)

class ItemInfoPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #ffffff;")
        self.current_mode = "list"
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(20)

        # 1. HEADER with Toggle Button
        header = QHBoxLayout()
        title = QLabel("Item Information")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e293b;")
        header.addWidget(title)
        header.addStretch()

        # Grid/List Switch
        self.toggle_btn = QPushButton("Grid View")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton { 
                background: #f3f4f6; padding: 8px 15px; border-radius: 6px; 
                font-weight: bold; color: #374151; border: 1px solid #d1d5db;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        self.toggle_btn.clicked.connect(self.switch_view)
        header.addWidget(self.toggle_btn)
        header.setSpacing(10)
        
        # Search pad
        search = QLineEdit()
        search.setPlaceholderText("Search items...")
        search.setFixedWidth(200)
        search.setStyleSheet("""
            QLineEdit {
                padding: 10px; 
                border-radius: 8px; 
                border: 1px solid #d1d5db;
                background-color: white;
                color: #111827; /* Sets the color of text you type */
            }
            QLineEdit::placeholder {
                color: #9ca3af; 
            }
        """)
        header.addWidget(search)
        header.setSpacing(10)

        # Item Sorter button
        header.addWidget(self.item_sorter())

        # 2. VIEW STACK (The area that changes)
        self.view_stack = QStackedWidget()

        # List Legend
        list_view_page = QWidget()
        list_page_layout = QVBoxLayout(list_view_page)
        list_page_layout.setContentsMargins(0, 0, 0, 0)
        list_page_layout.setSpacing(0) 
        legend_panel = QFrame()
        legend_panel.setFixedHeight(40) 
        legend_panel.setStyleSheet("""
            QFrame { background-color: #f8fafc; border-bottom: 1px solid #e5e7eb; }
            QLabel { color: #64748b; font-weight: bold; font-size: 11px; }
        """)
        legend_layout = QHBoxLayout(legend_panel)
        legend_layout.setContentsMargins(20, 0, 20, 0)
        legend_layout.addSpacing(60) # Accounts for the image in the row
        legend_layout.addWidget(QLabel("PRODUCT NAME"), 2)
        legend_layout.addWidget(QLabel("PRICE"), 1)
        legend_layout.addWidget(QLabel("STOCK"), 1)
        legend_layout.addWidget(QLabel("SOLD"), 1)
        legend_layout.addSpacing(40) 
        list_page_layout.addWidget(legend_panel)

        # 3. The Scroll Panel 
        list_scroll = QScrollArea()
        list_scroll.setWidgetResizable(True)
        list_scroll.setStyleSheet("border: none; background: transparent;")
        list_container = QWidget()
        self.list_layout = QVBoxLayout(list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(12)
        for _ in range(15): 
            self.list_layout.addWidget(ItemRow())
        list_scroll.setWidget(list_container)
        list_page_layout.addWidget(list_scroll)
        self.view_stack.addWidget(list_view_page)

        # Create List View
        list_scroll = QScrollArea()
        list_scroll.setWidgetResizable(True)
        list_scroll.setStyleSheet("border: none; background: transparent;")
        list_container = QWidget()
        self.list_layout = QVBoxLayout(list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(12)
        for _ in range(15): self.list_layout.addWidget(ItemRow())
        list_scroll.setWidget(list_container)
        
        # Create Grid View
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setStyleSheet("border: none; background: transparent;")
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setSpacing(20)
        for i in range(15): self.grid_layout.addWidget(ItemCard(), i // 4, i % 4)
        grid_scroll.setWidget(grid_container)

        # 3. FIXED FOOTER
        footer = QFrame()
        footer.setFixedHeight(70)
        footer.setStyleSheet("QFrame { background-color: white; border-radius: 12px; border: 1px solid #e5e7eb; }")
        footer_layout = QHBoxLayout(footer)
        del_btn = QPushButton("Delete Item")
        del_btn.setStyleSheet("color : #FF3737; font-weight: bold; padding: 10px 20px; border: none;")
        add_btn = QPushButton("Add Item")
        add_btn.setStyleSheet("color: #10b981; font-weight: bold; padding: 10px 20px; border: none;")
        refresh_btn = QPushButton("Refresh Page")
        refresh_btn.setStyleSheet("color: grey; font-weight: bold; padding: 10px 20px; border: none;")
        
        # Layout
        main_layout.addLayout(header)
        self.view_stack.addWidget(list_view_page) # Index 0
        self.view_stack.addWidget(grid_scroll) # Index 1
        main_layout.addWidget(self.view_stack)
        footer_layout.addWidget(del_btn)
        footer_layout.addWidget(add_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(refresh_btn)
        main_layout.addWidget(footer)

    def switch_view(self):
        if self.current_mode == "list":
            self.view_stack.setCurrentIndex(1)
            self.toggle_btn.setText("List View")
            self.current_mode = "grid"
        else:
            self.view_stack.setCurrentIndex(0)
            self.toggle_btn.setText("Grid View")
            self.current_mode = "list"

    def item_sorter(self, default_text="Sort by..."):
        itemSorter_btn = QPushButton(default_text)
        itemSorter_btn.setCursor(Qt.PointingHandCursor)
        itemSorter_btn.setFixedWidth(150)
        itemSorter_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: 600;                     
                text-align: center;                                       
            } 
            QPushButton:hover { background-color: #f9fafb; border-color: #4f46e5; }
            QPushButton::menu-indicator { image: none; }                         
        """)   

        itemSorter_menu = QMenu(itemSorter_btn)
        itemSorter_menu.setStyleSheet("""
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

        options = ["By name (Alphabetical)", "By time added", "By Price","By Quantity", "By Saleability"]
        for opt in options:
            action = QAction(opt, self)
            action.triggered.connect(lambda checked=False, text=opt, b=itemSorter_btn: self._update_date_range(text, b))
            itemSorter_menu.addAction(action)

        itemSorter_btn.setMenu(itemSorter_menu)
        return itemSorter_btn
    
    def _update_date_range(self, text, button):
        button.setText(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ItemInfoPage()
    window.show()
    sys.exit(app.exec())
