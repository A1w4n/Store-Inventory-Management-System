import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QLineEdit, QPushButton, QScrollArea, QFrame, QMenu, QStackedWidget, QGridLayout,
    QDialog, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from database import InventoryDatabase

class ItemRow(QFrame):
    # For List
    def __init__(self, item_data=None):
        super().__init__()
        self.setFixedHeight(60)
        self.item_data = item_data
        self.setStyleSheet("""
            QFrame { background-color: transparent; border: none; }
            QFrame:hover { background-color: #f9fafb; border-radius: 8px; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)

        # Image placeholder
        img = QFrame()
        img.setFixedSize(60, 60)
        img.setStyleSheet("background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 6px;")
        layout.addWidget(img)

        if item_data:
            # Product Name (weight 2)
            name = QLabel(str(item_data['name']))
            name.setStyleSheet("font-weight: bold; color: #000000; padding-left: 12px;")
            layout.addWidget(name, 2)

            # Price (weight 1)
            price_label = QLabel(f"${float(item_data['price']):.2f}")
            price_label.setStyleSheet("font-weight: bold; color: #000000; font-size: 12px;")
            layout.addWidget(price_label, 1)

            # Stock (weight 1)
            stock_label = QLabel(str(item_data['quantity']))
            stock_label.setStyleSheet("font-weight: bold; color: #000000; font-size: 12px;")
            layout.addWidget(stock_label, 1)

            # Category (weight 1)
            try:
                category_name = str(item_data['category_name']) if item_data['category_name'] else 'N/A'
            except (KeyError, TypeError, IndexError):
                category_name = 'N/A'
            category_label = QLabel(category_name)
            category_label.setStyleSheet("font-weight: bold; color: #000000; font-size: 12px;")
            layout.addWidget(category_label, 1)
        else:
            # Placeholder loading state
            t = QFrame()
            t.setFixedSize(150, 12)
            t.setStyleSheet("background-color: #f3f4f6; border-radius: 4px; margin-left: 12px;")
            layout.addWidget(t, 2)

            d = QFrame()
            d.setFixedSize(80, 10)
            d.setStyleSheet("background-color: #f9fafb; border-radius: 4px;")
            layout.addWidget(d, 1)

        # Menu button
        layout.addSpacing(12)
        btn = QPushButton("⋮")
        btn.setFixedSize(30, 30)
        btn.setStyleSheet("border: none; font-size: 18px; color: #6b7280;")
        layout.addWidget(btn)

class ItemCard(QFrame):
    # For Grid
    def __init__(self, item_data=None):
        super().__init__()
        self.setFixedSize(180, 220)
        self.item_data = item_data
        self.setStyleSheet("""
            QFrame { background-color: transparent; border: none; }
            QFrame:hover { background-color: #f9fafb; border-radius: 8px; }
        """)
        layout = QVBoxLayout(self)
        img = QFrame(); img.setStyleSheet("background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 8px;")
        layout.addWidget(img, 3)

        if item_data:
            name = QLabel(item_data['name'])
            name.setStyleSheet("font-weight: bold; color: #000000; font-size: 13px;")
            price = QLabel(f"${item_data['price']:.2f}")
            price.setStyleSheet("color: #000000; font-size: 12px;")
            layout.addWidget(name)
            layout.addWidget(price)
        else:
            t = QFrame(); t.setFixedHeight(12); t.setStyleSheet("background-color: #f3f4f6; border-radius: 4px;")
            d = QFrame(); d.setFixedHeight(10); d.setStyleSheet("background-color: #f9fafb; border-radius: 4px;")
            layout.addWidget(t); layout.addWidget(d)

        btn = QPushButton("View Detail")
        btn.setStyleSheet("background: #f3f4f6; color: #4b5563; font-size: 11px; font-weight: bold; padding: 5px; border-radius: 4px; border: none;")
        layout.addWidget(btn)

class AddItemDialog(QDialog):
    """Dialog for adding a new item."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Add New Item")
        self.setGeometry(100, 100, 400, 400)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Name
        layout.addWidget(QLabel("Product Name *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter product name")
        layout.addWidget(self.name_input)

        # SKU
        layout.addWidget(QLabel("SKU"))
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("Enter SKU (optional)")
        layout.addWidget(self.sku_input)

        # Category
        layout.addWidget(QLabel("Category"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("No Category", None)
        for cat in self.db.get_all_categories():
            self.category_combo.addItem(cat['name'], cat['id'])
        layout.addWidget(self.category_combo)

        # Price
        layout.addWidget(QLabel("Price *"))
        self.price_input = QDoubleSpinBox()
        self.price_input.setMinimum(0.0)
        self.price_input.setMaximum(999999.99)
        self.price_input.setValue(0.0)
        self.price_input.setDecimals(2)
        layout.addWidget(self.price_input)

        # Quantity
        layout.addWidget(QLabel("Initial Quantity"))
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(0)
        self.quantity_input.setMaximum(99999)
        self.quantity_input.setValue(0)
        layout.addWidget(self.quantity_input)

        # Low Stock Threshold
        layout.addWidget(QLabel("Low Stock Threshold"))
        self.threshold_input = QSpinBox()
        self.threshold_input.setMinimum(0)
        self.threshold_input.setMaximum(99999)
        self.threshold_input.setValue(10)
        layout.addWidget(self.threshold_input)

        # Description
        layout.addWidget(QLabel("Description"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter product description (optional)")
        self.description_input.setFixedHeight(80)
        layout.addWidget(self.description_input)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Item")
        add_btn.setStyleSheet("background: #10b981; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none;")
        add_btn.clicked.connect(self.add_item)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background: #e5e7eb; color: #374151; font-weight: bold; padding: 10px; border-radius: 6px; border: none;")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(add_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def add_item(self):
        """Add item to database."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Product name is required!")
            return

        price = self.price_input.value()
        if price <= 0:
            QMessageBox.warning(self, "Validation Error", "Price must be greater than 0!")
            return

        sku = self.sku_input.text().strip() or None
        category_id = self.category_combo.currentData()
        quantity = self.quantity_input.value()
        threshold = self.threshold_input.value()
        description = self.description_input.toPlainText().strip() or None

        item_id = self.db.add_item(
            name=name,
            sku=sku,
            category_id=category_id,
            price=price,
            quantity=quantity,
            low_stock_threshold=threshold,
            description=description
        )

        if item_id:
            QMessageBox.information(self, "Success", f"Item '{name}' added successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to add item. SKU might already exist.")

class DeleteItemDialog(QDialog):
    """Dialog for deleting an item."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Delete Item")
        self.setGeometry(100, 100, 400, 300)
        self.deleted_item = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Select Item to Delete:"))
        self.item_combo = QComboBox()

        items = self.db.get_all_items()
        if not items:
            self.item_combo.addItem("No items available", None)
            self.item_combo.setEnabled(False)
        else:
            for item in items:
                display_text = f"{item['name']} - ${item['price']:.2f} (Stock: {item['quantity']})"
                self.item_combo.addItem(display_text, item['id'])

        layout.addWidget(self.item_combo)

        # Warning
        warning = QLabel("⚠️ Warning: This action cannot be undone!")
        warning.setStyleSheet("color: #ef4444; font-weight: bold;")
        layout.addWidget(warning)

        # Buttons
        button_layout = QHBoxLayout()
        delete_btn = QPushButton("Delete Item")
        delete_btn.setStyleSheet("background: #FF3737; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none;")
        delete_btn.clicked.connect(self.delete_item)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background: #e5e7eb; color: #374151; font-weight: bold; padding: 10px; border-radius: 6px; border: none;")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(delete_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def delete_item(self):
        """Delete selected item from database."""
        item_id = self.item_combo.currentData()
        if item_id is None:
            QMessageBox.warning(self, "Error", "No item selected!")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this item? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db.delete_item(item_id):
                QMessageBox.information(self, "Success", "Item deleted successfully!")
                self.deleted_item = True
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete item.")


class ItemInfoPage(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self.db = db or InventoryDatabase()
        self.setStyleSheet("background-color: #ffffff;")
        self.current_mode = "list"
        self.search_term = ""

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
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.setFixedWidth(200)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #d1d5db;
                background-color: white;
                color: #111827;
            }
            QLineEdit::placeholder {
                color: #9ca3af;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        header.addWidget(self.search_input)
        header.setSpacing(10)

        # Item Sorter button
        header.addWidget(self.item_sorter())

        # 2. VIEW STACK (The area that changes)
        self.view_stack = QStackedWidget()

        # List View
        list_view_page = QWidget()
        list_page_layout = QVBoxLayout(list_view_page)
        list_page_layout.setContentsMargins(0, 0, 0, 0)
        list_page_layout.setSpacing(0)

        # List Legend
        legend_panel = QFrame()
        legend_panel.setFixedHeight(40)
        legend_panel.setStyleSheet("""
            QFrame { background-color: #f8fafc; border-bottom: 1px solid #e5e7eb; }
            QLabel { color: #64748b; font-weight: bold; font-size: 11px; }
        """)
        legend_layout = QHBoxLayout(legend_panel)
        legend_layout.setContentsMargins(20, 0, 20, 0)
        legend_layout.addSpacing(60)
        legend_layout.addWidget(QLabel("PRODUCT NAME"), 2)
        legend_layout.addWidget(QLabel("PRICE"), 1)
        legend_layout.addWidget(QLabel("STOCK"), 1)
        legend_layout.addWidget(QLabel("CATEGORY"), 1)
        legend_layout.addSpacing(40)
        list_page_layout.addWidget(legend_panel)

        # 3. The Scroll Panel for List View
        list_scroll = QScrollArea()
        list_scroll.setWidgetResizable(True)
        list_scroll.setStyleSheet("border: none; background: transparent;")
        list_container = QWidget()
        self.list_layout = QVBoxLayout(list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(12)
        list_scroll.setWidget(list_container)
        list_page_layout.addWidget(list_scroll)
        self.view_stack.addWidget(list_view_page)

        # Create Grid View
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setStyleSheet("border: 1px; background: transparent;")
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setSpacing(20)
        grid_scroll.setWidget(grid_container)
        self.view_stack.addWidget(grid_scroll)

        # Load initial items
        self.refresh_items()

        # 3. FIXED FOOTER
        footer = QFrame()
        footer.setFixedHeight(70)
        footer.setStyleSheet("QFrame { background-color: white; border-radius: 12px; border: 1px solid #e5e7eb; }")
        footer_layout = QHBoxLayout(footer)
        del_btn = QPushButton("Delete Item")
        del_btn.setStyleSheet("color : #FF3737; font-weight: bold; padding: 10px 20px; border: none;")
        del_btn.clicked.connect(self.show_delete_dialog)
        add_btn = QPushButton("Add Item")
        add_btn.setStyleSheet("color: #10b981; font-weight: bold; padding: 10px 20px; border: none;")
        add_btn.clicked.connect(self.show_add_dialog)
        refresh_btn = QPushButton("Refresh Page")
        refresh_btn.setStyleSheet("color: grey; font-weight: bold; padding: 10px 20px; border: none;")
        refresh_btn.clicked.connect(self.refresh_items)

        # Layout
        main_layout.addLayout(header)
        main_layout.addWidget(self.view_stack)
        footer_layout.addWidget(del_btn)
        footer_layout.addWidget(add_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(refresh_btn)
        main_layout.addWidget(footer)

    def refresh_items(self):
        """Refresh item lists from database."""
        # Clear layouts
        while self.list_layout.count():
            self.list_layout.takeAt(0).widget().deleteLater()
        while self.grid_layout.count():
            self.grid_layout.takeAt(0).widget().deleteLater()

        # Get items from database
        if self.search_term:
            items = self.db.search_items(self.search_term)
        else:
            items = self.db.get_all_items()

        # Add to list view
        for item in items:
            self.list_layout.addWidget(ItemRow(item))

        # Add to grid view
        for i, item in enumerate(items):
            self.grid_layout.addWidget(ItemCard(item), i // 4, i % 4)

    def on_search_changed(self):
        """Handle search input changes."""
        self.search_term = self.search_input.text().strip()
        self.refresh_items()

    def switch_view(self):
        if self.current_mode == "list":
            self.view_stack.setCurrentIndex(1)
            self.toggle_btn.setText("List View")
            self.current_mode = "grid"
        else:
            self.view_stack.setCurrentIndex(0)
            self.toggle_btn.setText("Grid View")
            self.current_mode = "list"

    def show_add_dialog(self):
        """Show dialog to add a new item."""
        dialog = AddItemDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            self.search_input.clear()  # Clear search
            self.refresh_items()  # Refresh to show new item

    def show_delete_dialog(self):
        """Show dialog to delete an item."""
        dialog = DeleteItemDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted and dialog.deleted_item:
            self.search_input.clear()  # Clear search
            self.refresh_items()  # Refresh after deletion

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

    # Initialize database
    db = InventoryDatabase("inventory.db")

    # Create and show window
    window = ItemInfoPage(db)
    window.resize(1200, 700)
    window.show()

    sys.exit(app.exec())
