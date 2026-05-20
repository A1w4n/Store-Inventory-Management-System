import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QLineEdit, QPushButton, QScrollArea, QFrame, QMenu, QStackedWidget, QGridLayout,
    QDialog, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QMessageBox,
    QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QThread
from PySide6.QtGui import QAction, QPixmap
import barcode
from barcode.writer import ImageWriter
import json
from PIL import Image
import io
from database import InventoryDatabase

class ItemRow(QFrame):
    # For List
    def __init__(self, item_data=None, on_select=None):
        super().__init__()
        self.setFixedHeight(60)
        self.item_data = item_data
        self.on_select = on_select
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame { background-color: transparent; border: none; }
            QFrame:hover { background-color: #f9fafb; border-radius: 8px; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)

        # Image placeholder
        # --- Actual Image Display ---
        img_label = QLabel()
        img_label.setFixedSize(60, 60)
        img_label.setAlignment(Qt.AlignCenter)
        
        # Safely convert data and get image path
        item_dict = dict(self.item_data) if self.item_data else {}
        image_path = item_dict.get('image_path')

        # Load image: supports Base64 data URIs (new) and file paths (legacy)
        pixmap = None
        if image_path:
            if image_path.startswith("data:"):
                import base64 as _b64
                header, data = image_path.split(",", 1)
                raw = _b64.b64decode(data)
                qpix = QPixmap()
                qpix.loadFromData(raw)
                pixmap = qpix if not qpix.isNull() else None
            else:
                p = Path(image_path)
                if p.exists():
                    pixmap = QPixmap(str(p))
        if pixmap:
            # Scale image smoothly to fit the box
            img_label.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            img_label.setStyleSheet("border: 1px solid #e5e7eb; border-radius: 6px;")
        else:
            # Fallback dashed box if no image is found
            img_label.setStyleSheet("background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 6px;")
            
        layout.addWidget(img_label)

        if item_data:
            # Product Name (weight 2)
            name = QLabel(str(item_data['name']))
            name.setStyleSheet("font-weight: bold; color: #000000; padding-left: 12px;")
            layout.addWidget(name, 2)

            # Price (weight 1)
            price_label = QLabel(f"Php {float(item_data['price']):.2f}")
            price_label.setStyleSheet("color: #000000; font-size: 12px;")
            layout.addWidget(price_label, 1)

            # Stock (weight 1)
            stock_label = QLabel(str(item_data['quantity']))
            stock_label.setStyleSheet("color: #000000; font-size: 12px;")
            layout.addWidget(stock_label, 1)

            # Category (weight 1)
            try:
                category_name = str(item_data['category_name']) if item_data['category_name'] else 'N/A'
            except (KeyError, TypeError, IndexError):
                category_name = 'N/A'
            category_label = QLabel(category_name)
            category_label.setStyleSheet("color: #000000; font-size: 12px;")
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

    def mousePressEvent(self, event):
        if self.item_data and self.on_select:
            self.on_select(self.item_data)
        super().mousePressEvent(event)

    def show_barcode(self):
        """Show Barcode dialog for this item."""
        if self.item_data:
            dialog = BarcodeDialog(self.item_data)
            dialog.exec()

class ItemCard(QFrame):
    # For Grid
    def __init__(self, item_data=None, on_select=None):
        super().__init__()
        self.setFixedSize(180, 220)
        self.item_data = item_data
        self.on_select = on_select
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame { background-color: transparent; border: none; }
            QFrame:hover { background-color: #f9fafb; border-radius: 8px; }
        """)
        layout = QVBoxLayout(self)

        
        # --- Actual Image Display ---
        img_label = QLabel()
        img_label.setFixedHeight(100) # Give it a nice height for the card
        img_label.setAlignment(Qt.AlignCenter)
        
        item_dict = dict(self.item_data) if self.item_data else {}
        image_path = item_dict.get('image_path')

        # Load image: supports Base64 data URIs (new) and file paths (legacy)
        pixmap = None
        if image_path:
            if image_path.startswith("data:"):
                import base64 as _b64
                header, data = image_path.split(",", 1)
                raw = _b64.b64decode(data)
                qpix = QPixmap()
                qpix.loadFromData(raw)
                pixmap = qpix if not qpix.isNull() else None
            else:
                p = Path(image_path)
                if p.exists():
                    pixmap = QPixmap(str(p))
        if pixmap:
            img_label.setPixmap(pixmap.scaled(150, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            img_label.setStyleSheet("border-radius: 8px;")
        else:
            img_label.setStyleSheet("background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 8px;")
            
        layout.addWidget(img_label, 3)

        if item_data:
            name = QLabel(item_data['name'])
            name.setStyleSheet("font-weight: bold; color: #000000; font-size: 13px;")
            price = QLabel(f"Php {float(item_data['price']):.2f}")
            price.setStyleSheet("color: #000000; font-size: 12px;")
            layout.addWidget(name)
            layout.addWidget(price)
        else:
            t = QFrame(); t.setFixedHeight(12); t.setStyleSheet("background-color: #f3f4f6; border-radius: 4px;")
            d = QFrame(); d.setFixedHeight(10); d.setStyleSheet("background-color: #f9fafb; border-radius: 4px;")
            layout.addWidget(t); layout.addWidget(d)

        btn = QPushButton("View Detail")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("background: #f3f4f6; color: #4b5563; font-size: 11px; font-weight: bold; padding: 5px; border-radius: 4px; border: none;")
        btn.clicked.connect(lambda: self.on_select(self.item_data) if self.item_data and self.on_select else None)
        layout.addWidget(btn)

    def mousePressEvent(self, event):
        if self.item_data and self.on_select:
            self.on_select(self.item_data)
        super().mousePressEvent(event)


class ToastNotification(QFrame):
    """A brief, self-dismissing notification that appears at the bottom of the parent."""
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border-radius: 10px;
                border: 1px solid #374151;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        icon = QLabel("✓")
        icon.setStyleSheet("""
            color: #10b981;
            font-size: 16px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(icon)

        msg = QLabel(message)
        msg.setStyleSheet("""
            color: #f9fafb;
            font-size: 13px;
            font-weight: 500;
            background: transparent;
            border: none;
        """)
        layout.addWidget(msg)
        self.adjustSize()

    def show_toast(self, duration_ms=2800):
        """Position near the bottom-centre of the parent and auto-dismiss."""
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            tw = max(self.sizeHint().width(), 280)
            self.setFixedWidth(tw)
            self.adjustSize()
            x = (pw - tw) // 2
            y = ph - self.height() - 28
            self.move(x, y)
        self.show()
        self.raise_()
        QTimer.singleShot(duration_ms, self.deleteLater)


class AddCategoryDialog(QDialog):
    """Small dialog to create a new category on the fly."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.new_category_id = None
        self.new_category_name = None
        self.setWindowTitle("New Category")
        self.setFixedSize(380, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel  { color: #111827; font-size: 13px; }
            QLineEdit, QTextEdit {
                background-color: #f9fafb;
                border: 1.5px solid #d1d5db;
                border-radius: 8px;
                color: #111827;
                padding: 8px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus { border-color: #4f46e5; background-color: #ffffff; }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        # Title row
        title_row = QHBoxLayout()
        icon = QLabel("🏷️")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background:#ede9fe; border-radius:8px; font-size:18px;")
        title_row.addWidget(icon)
        title_row.addSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(1)
        heading = QLabel("New Category")
        heading.setStyleSheet("font-size:15px; font-weight:700; color:#111827;")
        col.addWidget(heading)
        sub = QLabel("Add a category to organise your items.")
        sub.setStyleSheet("font-size:11px; color:#6b7280;")
        col.addWidget(sub)
        title_row.addLayout(col)
        title_row.addStretch()

        # Divider
        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color:#e5e7eb;")
        layout.addWidget(div)
        layout.addSpacing(16)

        # Category name field
        name_lbl = QLabel("Category Name *")
        name_lbl.setStyleSheet("color:#6b7280; font-size:12px; font-weight:600;")
        layout.addWidget(name_lbl)
        layout.addSpacing(4)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Electronics, Beverages…")
        self.name_input.setFixedHeight(38)
        self.name_input.returnPressed.connect(self.save_category)
        layout.addWidget(self.name_input)
        layout.addSpacing(20)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background:#f3f4f6; color:#374151;
                border:1.5px solid #d1d5db; border-radius:8px;
                font-size:13px; font-weight:600; padding:0 18px;
            }
            QPushButton:hover { background:#e5e7eb; color:#111827; }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Category")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4f46e5, stop:1 #6366f1);
                color:white; border:none; border-radius:8px;
                font-size:13px; font-weight:700; padding:0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4338ca, stop:1 #4f46e5);
            }
        """)
        save_btn.clicked.connect(self.save_category)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def save_category(self):
        name = self.name_input.text().strip()
        if not name:
            self.name_input.setStyleSheet("""
                QLineEdit {
                    background:#fff5f5; border:1.5px solid #ef4444;
                    border-radius:8px; color:#111827;
                    padding:8px 10px; font-size:13px;
                }
            """)
            self.name_input.setPlaceholderText("Category name is required!")
            return

        cat_id = self.db.add_category(name)
        if cat_id:
            self.new_category_id = cat_id
            self.new_category_name = name
            self.accept()
        else:
            self.name_input.setStyleSheet("""
                QLineEdit {
                    background:#fff5f5; border:1.5px solid #ef4444;
                    border-radius:8px; color:#111827;
                    padding:8px 10px; font-size:13px;
                }
            """)
            self.name_input.setText("")
            self.name_input.setPlaceholderText("That category already exists!")



class GeminiWorker(QThread):
    """Background thread that sends the image to Groq and returns parsed fields."""
    result_ready = Signal(object)
    error        = Signal(str)

    def __init__(self, image_bytes: bytes, mime: str, categories: list):
        super().__init__()
        self.image_bytes = image_bytes
        self.mime        = mime
        self.categories  = categories

    def run(self):
        try:
            import os, json, base64
            from io import BytesIO
            from dotenv import load_dotenv

            load_dotenv()
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                self.error.emit("GROQ_API_KEY not found in .env file. Get a free key at console.groq.com")
                return

            # Install groq SDK if missing
            try:
                from groq import Groq
            except ImportError:
                import subprocess, sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "groq", "-q"])
                from groq import Groq

            # Compress image
            try:
                from PIL import Image as PILImage
                img = PILImage.open(BytesIO(self.image_bytes)).convert("RGB")
                img.thumbnail((512, 512), PILImage.LANCZOS)
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=80)
                compressed = buf.getvalue()
            except ImportError:
                compressed = self.image_bytes

            b64_image = base64.b64encode(compressed).decode()
            cat_list = ", ".join(self.categories) if self.categories else "Electronics, Food, Clothing, Furniture, Other"

            prompt = (
                "You are a product catalog assistant for a Filipino inventory system. "
                "Prices must be in Philippine Peso (PHP). "
                "Look at this product image and return ONLY a valid JSON object "
                "with no markdown, no explanation, no extra text. "
                "Fields: name (title case string), price (number in PHP), "
                "category (best match from: " + cat_list + "), "
                "sku (short code like PIATTOS-CHZ), "
                "description (1-2 sentences)."
            )

            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/jpeg;base64," + b64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                max_tokens=512,
                temperature=0.2
            )

            text = response.choices[0].message.content.strip()

            # Strip markdown fences
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            parsed = json.loads(text)
            self.result_ready.emit(parsed)

        except Exception as ex:
            self.error.emit("Auto-fill failed: " + str(ex))


class AddItemDialog(QDialog):
    """Dialog for adding a new item or updating an existing one."""
    def __init__(self, db, parent=None, item_data=None):
        super().__init__(parent)
        self.db = db
        self.item_data = item_data
        self.image_path = item_data.get('image_path') if item_data else None
        self.setWindowTitle("Update Item" if item_data else "Add New Item")
        self.setMinimumSize(820, 640)
        self.setStyleSheet("""
            QDialog {
                background-color: #f9fafb;
            }
            QLabel {
                color: #111827;
                font-size: 13px;
            }
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #ffffff;
                border: 1.5px solid #d1d5db;
                border-radius: 8px;
                color: #111827;
                padding: 8px 10px;
                font-size: 13px;
                selection-background-color: #4f46e5;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus,
            QDoubleSpinBox:focus, QComboBox:focus {
                border-color: #4f46e5;
                background-color: #ffffff;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #9ca3af;
            }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background-color: #e5e7eb;
                border: none;
                border-radius: 4px;
                width: 18px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #d1d5db;
            }
            QComboBox:hover {
                border-color: #6366f1;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #d1d5db;
                color: #374151;
                selection-background-color: #f3f4f6;
                selection-color: #4f46e5;
                outline: none;
            }
            QScrollBar:vertical {
                background: #f3f4f6;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #d1d5db;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4f46e5;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT PANEL: image drop zone ──────────────────────────────────────
        left_panel = QFrame()
        left_panel.setFixedWidth(260)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-right: 1px solid #e5e7eb;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 32, 24, 32)
        left_layout.setSpacing(16)

        # Heading
        panel_title = QLabel("Update Product" if self.item_data else "New Product")
        panel_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #111827; letter-spacing: 0.5px;")
        left_layout.addWidget(panel_title)

        sub_text = "Update the details of the\nexisting item." if self.item_data else "Fill in the form to add a\nnew item to your inventory."
        sub = QLabel(sub_text)
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #6b7280; font-size: 12px; line-height: 1.5;")
        left_layout.addWidget(sub)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #e5e7eb;")
        left_layout.addWidget(div)

        # Image preview box (click to browse)
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(210, 210)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setWordWrap(True)
        self.image_preview.setCursor(Qt.PointingHandCursor)
        
        # Support Base64 data URIs (new) and legacy file paths
        _preview_pixmap = None
        if self.image_path:
            if self.image_path.startswith("data:"):
                import base64 as _b64
                _, _b64data = self.image_path.split(",", 1)
                _raw = _b64.b64decode(_b64data)
                _qp  = QPixmap(); _qp.loadFromData(_raw)
                _preview_pixmap = _qp if not _qp.isNull() else None
            elif Path(self.image_path).exists():
                _preview_pixmap = QPixmap(self.image_path)
        if _preview_pixmap:
            self.image_preview.setPixmap(_preview_pixmap.scaled(210, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.image_preview.setStyleSheet("""
                QLabel {
                    background-color: #f9fafb;
                    border: 2px solid #4f46e5;
                    border-radius: 14px;
                    padding: 4px;
                }
            """)
        else:
            self.image_preview.setText("📷\n\nClick to upload\nproduct image")
            self.image_preview.setStyleSheet("""
                QLabel {
                    background-color: #f9fafb;
                    border: 2px dashed #d1d5db;
                    border-radius: 14px;
                    color: #9ca3af;
                    font-size: 13px;
                    padding: 10px;
                }
                QLabel:hover {
                    border-color: #4f46e5;
                    color: #4f46e5;
                }
            """)
        self.image_preview.mousePressEvent = lambda e: self.browse_image()
        left_layout.addWidget(self.image_preview, 0, Qt.AlignHCenter)

        # Change photo button
        browse_btn = QPushButton("📷  Change Photo")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #4f46e5;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 8px 0;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4f46e5;
                color: #ffffff;
                border-color: #4f46e5;
            }
        """)
        browse_btn.clicked.connect(self.browse_image)
        left_layout.addWidget(browse_btn)

        # AI Auto-fill button
        self.ai_btn = QPushButton("✨  Auto-fill with AI")
        self.ai_btn.setCursor(Qt.PointingHandCursor)
        self.ai_btn.setEnabled(False)   # enabled only after image is picked
        self.ai_btn.setToolTip("Pick an image first, then click to auto-fill fields using Gemini AI")
        self.ai_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #7c3aed, stop:1 #4f46e5);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 0;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover { opacity: 0.9; }
            QPushButton:disabled {
                background: #e5e7eb;
                color: #9ca3af;
            }
        """)
        self.ai_btn.clicked.connect(self.autofill_from_image)
        left_layout.addWidget(self.ai_btn)

        # Status label for AI feedback
        self.ai_status = QLabel("")
        self.ai_status.setWordWrap(True)
        self.ai_status.setAlignment(Qt.AlignCenter)
        self.ai_status.setStyleSheet("font-size: 11px; color: #6b7280;")
        left_layout.addWidget(self.ai_status)

        left_layout.addStretch()

        # Required note
        req_note = QLabel("* Required fields")
        req_note.setStyleSheet("color: #9ca3af; font-size: 11px;")
        left_layout.addWidget(req_note)

        root.addWidget(left_panel)

        # ── RIGHT PANEL: form ────────────────────────────────────────────────
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #f9fafb;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(32, 32, 32, 24)
        right_layout.setSpacing(0)

        # Header row
        hdr = QHBoxLayout()
        form_title = QLabel("Item Details")
        form_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")
        hdr.addWidget(form_title)
        hdr.addStretch()

        # Scrollable form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        form_container = QWidget()
        form_container.setStyleSheet("background: transparent;")
        form = QVBoxLayout(form_container)
        form.setSpacing(6)
        form.setContentsMargins(0, 0, 8, 0)

        # ── Section: Basic Info ──
        sec1 = self._section_header("Basic Information")
        form.addWidget(sec1)
        form.addSpacing(8)

        grid1 = QGridLayout()
        grid1.setSpacing(12)
        grid1.setColumnStretch(0, 1)
        grid1.setColumnStretch(1, 1)

        # Product Name
        grid1.addWidget(self._field_label("Product Name *"), 0, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Wireless Headphones")
        grid1.addWidget(self.name_input, 1, 0)

        # SKU
        grid1.addWidget(self._field_label("SKU / Barcode"), 0, 1)
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("e.g. SKU-00123 (optional)")
        grid1.addWidget(self.sku_input, 1, 1)

        # Category
        grid1.addWidget(self._field_label("Category"), 2, 0)
        cat_row = QHBoxLayout()
        cat_row.setSpacing(6)
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(38)
        self._refresh_category_combo()
        cat_row.addWidget(self.category_combo, 1)

        add_cat_btn = QPushButton("＋")
        add_cat_btn.setCursor(Qt.PointingHandCursor)
        add_cat_btn.setFixedSize(38, 38)
        add_cat_btn.setToolTip("Add a new category")
        add_cat_btn.setStyleSheet("""
            QPushButton {
                background: #ede9fe; color: #4f46e5;
                border: 1.5px solid #c4b5fd; border-radius: 8px;
                font-size: 18px; font-weight: 700;
            }
            QPushButton:hover { background: #4f46e5; color: white; border-color: #4f46e5; }
        """)
        add_cat_btn.clicked.connect(self._open_add_category)
        cat_row.addWidget(add_cat_btn)

        cat_widget = QWidget()
        cat_widget.setStyleSheet("background: transparent;")
        cat_widget.setLayout(cat_row)
        grid1.addWidget(cat_widget, 3, 0)

        # Price
        grid1.addWidget(self._field_label("Price (Php) *"), 2, 1)
        self.price_input = QDoubleSpinBox()
        self.price_input.setPrefix("₱ ")
        self.price_input.setMinimum(0.0)
        self.price_input.setMaximum(999999.99)
        self.price_input.setValue(0.0)
        self.price_input.setDecimals(2)
        self.price_input.setFixedHeight(38)
        grid1.addWidget(self.price_input, 3, 1)

        form.addLayout(grid1)
        form.addSpacing(20)

        # ── Section: Inventory ──
        sec2 = self._section_header("Inventory")
        form.addWidget(sec2)
        form.addSpacing(8)

        grid2 = QGridLayout()
        grid2.setSpacing(12)
        grid2.setColumnStretch(0, 1)
        grid2.setColumnStretch(1, 1)

        grid2.addWidget(self._field_label("Initial Quantity"), 0, 0)
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(0)
        self.quantity_input.setMaximum(99999)
        self.quantity_input.setValue(0)
        self.quantity_input.setFixedHeight(38)
        grid2.addWidget(self.quantity_input, 1, 0)

        grid2.addWidget(self._field_label("Low Stock Alert Threshold"), 0, 1)
        self.threshold_input = QSpinBox()
        self.threshold_input.setMinimum(0)
        self.threshold_input.setMaximum(99999)
        self.threshold_input.setValue(10)
        self.threshold_input.setFixedHeight(38)
        grid2.addWidget(self.threshold_input, 1, 1)

        form.addLayout(grid2)
        form.addSpacing(20)

        # ── Section: Description ──
        sec3 = self._section_header("Description")
        form.addWidget(sec3)
        form.addSpacing(8)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Write a short product description (optional)…")
        self.description_input.setFixedHeight(100)
        form.addWidget(self.description_input)

        form.addStretch()
        scroll.setWidget(form_container)
        right_layout.addWidget(scroll, 1)
        right_layout.addSpacing(20)

        # ── Action Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(42)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                border: 1.5px solid #d1d5db;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                color: #111827;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        # Pre-fill form if item_data is provided
        if self.item_data:
            self.name_input.setText(str(self.item_data.get('name', '')))
            self.sku_input.setText(str(self.item_data.get('sku', '') or ''))
            self.price_input.setValue(float(self.item_data.get('price', 0.0)))
            self.quantity_input.setValue(int(self.item_data.get('quantity', 0)))
            self.threshold_input.setValue(int(self.item_data.get('low_stock_threshold', 10)))
            self.description_input.setText(str(self.item_data.get('description', '') or ''))
            self._refresh_category_combo(select_id=self.item_data.get('category_id'))

        add_btn = QPushButton("  ✓  Save Changes" if self.item_data else "  ＋  Add Item")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setFixedHeight(42)
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #6366f1);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 32px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4338ca, stop:1 #4f46e5);
            }
            QPushButton:pressed {
                background: #3730a3;
            }
        """)
        add_btn.clicked.connect(self.add_item)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(add_btn)
        right_layout.addLayout(btn_row)

        root.addWidget(right_panel, 1)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _section_header(self, text):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet("""
            color: #4f46e5;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding-bottom: 4px;
            border-bottom: 1px solid #e5e7eb;
        """)
        return lbl

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #6b7280; font-size: 12px; font-weight: 600;")
        return lbl

    def _refresh_category_combo(self, select_id=None):
        """Reload categories from the DB; optionally auto-select a specific id."""
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("— No Category —", None)
        for cat in self.db.get_all_categories():
            self.category_combo.addItem(cat['name'], cat['id'])
            if select_id and cat['id'] == select_id:
                self.category_combo.setCurrentIndex(self.category_combo.count() - 1)
        self.category_combo.blockSignals(False)

    def _open_add_category(self):
        """Open the AddCategoryDialog and refresh the combo on success."""
        dlg = AddCategoryDialog(self.db, self)
        if dlg.exec() == QDialog.Accepted and dlg.new_category_id:
            self._refresh_category_combo(select_id=dlg.new_category_id)

    def browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Product Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            import base64, mimetypes
            mime, _ = mimetypes.guess_type(file_path)
            mime = mime or "image/png"
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            self.image_path  = f"data:{mime};base64,{b64}"
            self._image_raw  = raw_bytes   # kept for Gemini upload
            self._image_mime = mime
            # Enable AI button now that we have an image
            if hasattr(self, "ai_btn"):
                self.ai_btn.setEnabled(True)
                self.ai_status.setText("Image ready — click ✨ to auto-fill")
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.image_preview.setPixmap(pixmap.scaled(
                    self.image_preview.width(),
                    self.image_preview.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                self.image_preview.setStyleSheet("""
                    QLabel {
                        background-color: #f9fafb;
                        border: 2px solid #4f46e5;
                        border-radius: 14px;
                        padding: 4px;
                    }
                """)
            else:
                self.image_preview.setText("⚠️ Preview unavailable")
        else:
            self.image_path = None
            self.image_preview.setText("📷\n\nClick to upload\nproduct image")
            self.image_preview.setStyleSheet("""
                QLabel {
                    background-color: #f9fafb;
                    border: 2px dashed #d1d5db;
                    border-radius: 14px;
                    color: #9ca3af;
                    font-size: 13px;
                    padding: 10px;
                }
                QLabel:hover {
                    border-color: #4f46e5;
                    color: #4f46e5;
                }
            """)

    def autofill_from_image(self):
        """Send the selected image to Gemini and auto-fill the form fields."""
        if not hasattr(self, "_image_raw"):
            return

        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("⏳  Analyzing…")
        self.ai_status.setText("Sending image to Gemini AI…")

        categories = [self.category_combo.itemText(i)
                      for i in range(self.category_combo.count())
                      if self.category_combo.itemText(i) != "— No Category —"]

        self._worker = GeminiWorker(self._image_raw, self._image_mime, categories)
        self._worker.result_ready.connect(self._apply_autofill)
        self._worker.error.connect(self._autofill_error)
        self._worker.start()

    def _apply_autofill(self, data: dict):
        """Fill the form with Gemini's response."""
        if data.get("name"):
            self.name_input.setText(str(data["name"]))
        if data.get("price"):
            try:
                self.price_input.setValue(float(data["price"]))
            except (ValueError, TypeError):
                pass
        if data.get("sku"):
            self.sku_input.setText(str(data["sku"]))
        if data.get("description"):
            self.description_input.setText(str(data["description"]))
        if data.get("category"):
            suggested = str(data["category"]).strip().lower()
            matched = False
            for i in range(self.category_combo.count()):
                if self.category_combo.itemText(i).strip().lower() == suggested:
                    self.category_combo.setCurrentIndex(i)
                    matched = True
                    break
            if not matched:
                # Category doesn't exist yet — offer to create it
                self.ai_status.setText(
                    f'✨ Done! Suggested category "{data["category"]}" not in list — add it manually if needed.')
            else:
                self.ai_status.setText("✨ Fields auto-filled! Review and adjust before saving.")
        else:
            self.ai_status.setText("✨ Fields auto-filled! Review and adjust before saving.")

        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("✨  Auto-fill with AI")

    def _autofill_error(self, msg: str):
        """Show error and re-enable button."""
        self.ai_status.setText(f"⚠️ {msg}")
        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("✨  Auto-fill with AI")

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

        if self.item_data:
            success = self.db.update_item(
                self.item_data['id'],
                name=name,
                sku=sku,
                category_id=category_id,
                price=price,
                low_stock_threshold=threshold,
                description=description,
                image_path=self.image_path
            )
            
            # Update quantity if changed
            if success and int(self.item_data.get('quantity', 0)) != quantity:
                self.db.update_quantity(self.item_data['id'], quantity, "UPDATE", notes="Manual stock adjustment")
                
            if success:
                self.accept()
                parent = self.parent()
                if parent:
                    toast = ToastNotification(f"✓  '{name}' updated successfully", parent)
                    toast.show_toast()
            else:
                error_msg = "Failed to update item. This could be due to:\n"
                error_msg += "• SKU already exists (if changed)\n"
                error_msg += "• Invalid category selection\n"
                error_msg += "• Database connection issue\n\n"
                error_msg += "Check the console for more details."
                QMessageBox.critical(self, "Error Updating Item", error_msg)
        else:
            item_id = self.db.add_item(
                name=name,
                sku=sku,
                category_id=category_id,
                price=price,
                quantity=quantity,
                low_stock_threshold=threshold,
                description=description,
                image_path=self.image_path
            )

            if item_id:
                self.accept()
                parent = self.parent()
                if parent:
                    toast = ToastNotification(f"✓  '{name}' added to inventory", parent)
                    toast.show_toast()
            else:
                # Show better error message
                error_msg = "Failed to add item. This could be due to:\n"
                error_msg += "• SKU already exists (if provided)\n"
                error_msg += "• Invalid category selection\n"
                error_msg += "• Database connection issue\n\n"
                error_msg += "Check the console for more details."
                QMessageBox.critical(self, "Error Adding Item", error_msg)

class DeleteItemDialog(QDialog):
    """Dialog for confirming deletion of a specific item."""
    def __init__(self, db, item_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.item_data = item_data
        self.deleted_item = False
        self.setWindowTitle("Delete Item")
        self.setFixedSize(420, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                color: #111827;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 28)
        layout.setSpacing(0)

        # Icon + title row
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        icon_lbl = QLabel("🗑️")
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("""
            background-color: #fee2e2;
            border-radius: 10px;
            font-size: 20px;
        """)
        title_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        heading = QLabel("Delete Item")
        heading.setStyleSheet("font-size: 17px; font-weight: 700; color: #111827;")
        title_col.addWidget(heading)
        sub = QLabel("This action cannot be undone.")
        sub.setStyleSheet("font-size: 12px; color: #6b7280;")
        title_col.addWidget(sub)
        title_row.addLayout(title_col)
        title_row.addStretch()

        layout.addLayout(title_row)
        layout.addSpacing(20)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #e5e7eb;")
        layout.addWidget(div)
        layout.addSpacing(20)

        # Item summary card
        item_card = QFrame()
        item_card.setStyleSheet("""
            QFrame {
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 10px;
            }
        """)
        card_layout = QVBoxLayout(item_card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(4)

        item_name = QLabel(str(self.item_data.get('name', 'Unknown Item')))
        item_name.setStyleSheet("font-size: 14px; font-weight: 700; color: #991b1b;")
        card_layout.addWidget(item_name)

        price = float(self.item_data.get('price', 0))
        qty = self.item_data.get('quantity', 0)
        sku = self.item_data.get('sku') or 'N/A'
        details_lbl = QLabel(f"SKU: {sku}  ·  Price: Php {price:.2f}  ·  Stock: {qty}")
        details_lbl.setStyleSheet("font-size: 12px; color: #b91c1c;")
        card_layout.addWidget(details_lbl)

        layout.addWidget(item_card)
        layout.addSpacing(24)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                border: 1.5px solid #d1d5db;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover { background-color: #e5e7eb; color: #111827; }
        """)
        cancel_btn.clicked.connect(self.reject)

        delete_btn = QPushButton("Delete Item")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setFixedHeight(40)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc2626, stop:1 #ef4444);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #b91c1c, stop:1 #dc2626);
            }
            QPushButton:pressed { background: #991b1b; }
        """)
        delete_btn.clicked.connect(self.delete_item)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)

    def delete_item(self):
        """Delete the item from the database."""
        item_id = self.item_data.get('id')
        if item_id is None:
            return

        if self.db.delete_item(item_id):
            self.deleted_item = True
            self.accept()
            # Show toast on parent
            parent = self.parent()
            if parent:
                item_name = self.item_data.get('name', 'Item')
                toast = ToastNotification(f"🗑️  '{item_name}' deleted from inventory", parent)
                toast.show_toast()
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", "Failed to delete item.")


class BarcodeDialog(QDialog):
    """Dialog to display Barcode for an item."""
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.setWindowTitle(f"Barcode for {item_data['name']}")
        self.setGeometry(100, 100, 300, 200)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        item_data = dict(self.item_data)  # Convert from RowProxy to dict if needed

        # Title
        title = QLabel(f"Barcode for {self.item_data['name']}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Barcode image
        sku = self.item_data.get('sku')
        if not sku:
            sku = f"ID-{self.item_data['id']}"
        
        import io
        Code128 = barcode.get_barcode_class('code128')
        rv = io.BytesIO()
        Code128(sku, writer=ImageWriter()).write(rv)
        
        pixmap = QPixmap()
        pixmap.loadFromData(rv.getvalue())

        barcode_label = QLabel()
        barcode_label.setPixmap(pixmap.scaled(250, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        barcode_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(barcode_label)

        # Info text
        info = QLabel("Scan this barcode to quickly access item details.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(info)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ItemInfoPage(QWidget):
    item_changed = Signal()
    def __init__(self, db=None):
        super().__init__()
        self.db = db or InventoryDatabase()
        self.setStyleSheet("background-color: #f9fafb;")
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.current_mode = "list"
        self.search_term = ""
        self.current_item = None
        self.active_category_filter = "All"
        self.sort_key = "time_added"  # Track the currently selected/displayed item

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 0, 24, 24)
        main_layout.setSpacing(12)

        # 1. HEADER with Toggle Button
        header = QHBoxLayout()
        title = QLabel("Item Information")
        title.setStyleSheet("font-size: 38px; font-weight: bold; color: #111827;")
        header.addWidget(title)
        header.addStretch()

        # Add Item Button (Icon)
        self.add_btn_icon = QPushButton("➕")
        self.add_btn_icon.setCursor(Qt.PointingHandCursor)
        self.add_btn_icon.setFixedSize(40, 40)
        self.add_btn_icon.setStyleSheet("""
            QPushButton {
                background: #10b981; font-size: 20px; border-radius: 8px; border: none;
            }
            QPushButton:hover { background: #059669; }
        """)
        self.add_btn_icon.clicked.connect(self.show_add_dialog)
        header.addWidget(self.add_btn_icon)
        header.setSpacing(8)

        # Refresh Button (Icon)
        self.refresh_btn_icon = QPushButton("🔄")
        self.refresh_btn_icon.setCursor(Qt.PointingHandCursor)
        self.refresh_btn_icon.setFixedSize(40, 40)
        self.refresh_btn_icon.setStyleSheet("""
            QPushButton {
                background: #6b7280; font-size: 20px; border-radius: 8px; border: none;
            }
            QPushButton:hover { background: #4b5563; }
        """)
        self.refresh_btn_icon.clicked.connect(self.refresh_items)
        header.addWidget(self.refresh_btn_icon)
        header.setSpacing(10)

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

        # Category filter pill bar
        self.cat_filter_bar = QHBoxLayout()
        self.cat_filter_bar.setSpacing(8)
        self.cat_filter_bar.setAlignment(Qt.AlignLeft)
        self.cat_filter_scroll_widget = QWidget()
        self.cat_filter_scroll_widget.setLayout(self.cat_filter_bar)
        self.cat_filter_scroll_widget.setStyleSheet("background: transparent;")
        cat_filter_scroll = QScrollArea()
        cat_filter_scroll.setWidget(self.cat_filter_scroll_widget)
        cat_filter_scroll.setWidgetResizable(True)
        cat_filter_scroll.setFixedHeight(46)
        cat_filter_scroll.setFrameShape(QFrame.NoFrame)
        cat_filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_filter_scroll.setStyleSheet("background: transparent; border: none;")
        main_layout.addWidget(cat_filter_scroll)

        # 2. VIEW STACK (The area that changes)
        self.view_stack = QStackedWidget()
        self.view_stack.setStyleSheet("background-color: #f9fafb; border: none;")

        # List View
        list_view_page = QWidget()
        list_page_layout = QVBoxLayout(list_view_page)
        list_page_layout.setContentsMargins(0, 0, 0, 0)
        list_page_layout.setSpacing(0)

        # List Legend - styled as header in white card
        legend_panel = QFrame()
        legend_panel.setFixedHeight(45)
        legend_panel.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #e5e7eb; border-top-left-radius: 12px; border-top-right-radius: 12px; }
            QLabel { color: #6b7280; font-weight: bold; font-size: 11px; border: none; }
        """)
        legend_layout = QHBoxLayout(legend_panel)
        legend_layout.setContentsMargins(18, 0, 18, 0)
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
        list_scroll.setFrameShape(QFrame.NoFrame)
        list_scroll.setStyleSheet("border: none; background: #ffffff; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        list_container = QWidget()
        list_container.setStyleSheet("background: #ffffff;")
        self.list_layout = QVBoxLayout(list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(10)
        list_container.setStyleSheet("background-color: #ffffff; border: 1px solid #e5e7eb; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        list_scroll.setWidget(list_container)
        list_page_layout.addWidget(list_scroll)
        self.view_stack.addWidget(list_view_page)

        # Create Grid View
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setFrameShape(QFrame.NoFrame)
        grid_scroll.setStyleSheet("border: none; background: #ffffff; border-radius: 12px;")
        grid_container = QWidget()
        grid_container.setStyleSheet("background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;")
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(18, 16, 18, 16)
        grid_scroll.setWidget(grid_container)
        self.view_stack.addWidget(grid_scroll)

        # ── Category filter pill bar ──────────────────────────────────────
        self.cat_filter_bar = QHBoxLayout()
        self.cat_filter_bar.setSpacing(8)
        self.cat_filter_bar.setAlignment(Qt.AlignLeft)
        self.cat_filter_scroll_widget = QWidget()
        self.cat_filter_scroll_widget.setLayout(self.cat_filter_bar)
        self.cat_filter_scroll_widget.setStyleSheet("background: transparent;")
        self.cat_filter_scroll = QScrollArea()
        self.cat_filter_scroll.setWidget(self.cat_filter_scroll_widget)
        self.cat_filter_scroll.setWidgetResizable(True)
        self.cat_filter_scroll.setFixedHeight(42)
        self.cat_filter_scroll.setFrameShape(QFrame.NoFrame)
        self.cat_filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cat_filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cat_filter_scroll.setStyleSheet("background: transparent; border: none;")

        # Build detail panel (cat_filter_bar must exist before refresh_items)
        self.detail_panel = self._create_detail_panel()
        self.refresh_items()

        # Content row
        content_row = QHBoxLayout()
        content_row.setSpacing(20)
        content_row.addWidget(self.view_stack, 3)
        content_row.addWidget(self.detail_panel, 1)

        # ── Add to main layout in correct order ────────────────────────────
        main_layout.addLayout(header)            # title + buttons row
        main_layout.addWidget(self.cat_filter_scroll)  # category pills (below title)
        main_layout.addLayout(content_row, 1)    # list/grid + detail panel

    def _make_cat_pill(self, label, active):
        """Create a styled category filter pill button."""
        btn = QPushButton(label)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setFixedHeight(30)
        if active:
            btn.setStyleSheet("""
                QPushButton {
                    background: #4f46e5; color: #ffffff;
                    border: 1.5px solid #4f46e5; border-radius: 15px;
                    font-size: 12px; font-weight: 700; padding: 0 14px;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background: #ffffff; color: #6b7280;
                    border: 1.5px solid #d1d5db; border-radius: 15px;
                    font-size: 12px; font-weight: 600; padding: 0 14px;
                }
                QPushButton:hover {
                    border-color: #4f46e5; color: #4f46e5; background: #eef2ff;
                }
            """)
        btn.clicked.connect(lambda _, l=label: self._set_cat_filter(l))
        return btn

    def _set_cat_filter(self, label):
        self.active_category_filter = label
        self.refresh_items()

    def _make_cat_section_header(self, cat_name, count):
        """Return a QWidget used as a category section divider in list/grid."""
        row = QWidget()
        row.setFixedHeight(36)
        row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(4, 4, 4, 4)
        hl.setSpacing(10)
        lbl = QLabel(cat_name.upper())
        lbl.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #4f46e5; letter-spacing: 0.8px; background: transparent;"
        )
        hl.addWidget(lbl)
        cnt = QLabel(f"{count} item{'s' if count != 1 else ''}")
        cnt.setStyleSheet("font-size: 11px; color: #9ca3af; background: transparent;")
        hl.addWidget(cnt)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e5e7eb;")
        hl.addWidget(line, 1)
        return row

    def refresh_items(self):
        """Refresh item lists from database, grouped by category."""
        # ── Clear list layout ──────────────────────────────────────────────
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        # ── Clear grid layout ──────────────────────────────────────────────
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        # ── Fetch items ────────────────────────────────────────────────────
        if self.search_term:
            items = self.db.search_items(self.search_term)
        else:
            items = self.db.get_all_items()
        items = [dict(i) for i in items]

        # ── Sort ───────────────────────────────────────────────────────────
        sk = getattr(self, "sort_key", "time_added")
        if sk == "name":
            items.sort(key=lambda x: (x.get("name") or "").lower())
        elif sk == "price":
            items.sort(key=lambda x: float(x.get("price") or 0))
        elif sk == "quantity":
            items.sort(key=lambda x: int(x.get("quantity") or 0))
        elif sk == "saleability":
            items.sort(key=lambda x: int(x.get("total_sold") or 0), reverse=True)

        # ── Rebuild category filter pills ──────────────────────────────────
        # Remove old pills
        while self.cat_filter_bar.count():
            item = self.cat_filter_bar.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        all_cats = ["All"] + sorted({i.get("category_name") or "Uncategorized" for i in items})
        # If saved filter no longer exists, reset to All
        if self.active_category_filter not in all_cats:
            self.active_category_filter = "All"
        for cat in all_cats:
            self.cat_filter_bar.addWidget(
                self._make_cat_pill(cat, cat == self.active_category_filter)
            )
        self.cat_filter_scroll_widget.adjustSize()

        # ── Apply category filter ──────────────────────────────────────────
        if self.active_category_filter != "All":
            items = [i for i in items
                     if (i.get("category_name") or "Uncategorized") == self.active_category_filter]

        # ── Group by category ──────────────────────────────────────────────
        from collections import OrderedDict
        groups = OrderedDict()
        for item in items:
            cat = item.get("category_name") or "Uncategorized"
            groups.setdefault(cat, []).append(item)

        # ── Populate list view ─────────────────────────────────────────────
        for cat, cat_items in groups.items():
            self.list_layout.addWidget(self._make_cat_section_header(cat, len(cat_items)))
            for item in cat_items:
                self.list_layout.addWidget(ItemRow(item, on_select=self.display_item_details))

        # ── Populate grid view ─────────────────────────────────────────────
        grid_row = 0
        COLS = 4
        for cat, cat_items in groups.items():
            # Section header spans full width
            hdr = self._make_cat_section_header(cat, len(cat_items))
            self.grid_layout.addWidget(hdr, grid_row, 0, 1, COLS)
            grid_row += 1
            for col_idx, item in enumerate(cat_items):
                self.grid_layout.addWidget(
                    ItemCard(item, on_select=self.display_item_details),
                    grid_row + col_idx // COLS,
                    col_idx % COLS
                )
            grid_row += (len(cat_items) + COLS - 1) // COLS

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

    def _create_detail_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; }
            QLabel { color: #111827; }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 18)
        panel_layout.setSpacing(12)

        # Header with delete button icon
        header_layout = QHBoxLayout()
        heading = QLabel("Item Details")
        heading.setStyleSheet("font-size: 20px; font-weight: 700; color: #111827; border: none;")
        header_layout.addWidget(heading)
        header_layout.addStretch()
        
        self.update_icon_btn = QPushButton("✏️")
        self.update_icon_btn.setCursor(Qt.PointingHandCursor)
        self.update_icon_btn.setFixedSize(32, 32)
        self.update_icon_btn.setStyleSheet("""
            QPushButton {
                background: #e0e7ff; font-size: 16px; border-radius: 6px; border: none;
            }
            QPushButton:hover { background: #c7d2fe; }
        """)
        self.update_icon_btn.clicked.connect(self.show_update_dialog)
        self.update_icon_btn.setVisible(False)
        header_layout.addWidget(self.update_icon_btn)

        self.delete_icon_btn = QPushButton("🗑️")
        self.delete_icon_btn.setCursor(Qt.PointingHandCursor)
        self.delete_icon_btn.setFixedSize(32, 32)
        self.delete_icon_btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2; font-size: 16px; border-radius: 6px; border: none;
            }
            QPushButton:hover { background: #fecaca; }
        """)
        self.delete_icon_btn.clicked.connect(self.show_delete_dialog)
        self.delete_icon_btn.setVisible(False)
        header_layout.addWidget(self.delete_icon_btn)
        panel_layout.addLayout(header_layout)

        self.detail_image = QLabel("No item selected")
        self.detail_image.setFixedHeight(180)
        self.detail_image.setAlignment(Qt.AlignCenter)
        self.detail_image.setStyleSheet("background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 12px; color: #6b7280;")
        panel_layout.addWidget(self.detail_image)

        self.detail_name = QLabel("Select an item to view details")
        self.detail_name.setWordWrap(True)
        self.detail_name.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        panel_layout.addWidget(self.detail_name)

        self.detail_meta = QLabel("<i>SKU, category, price, and stock will appear here.</i>")
        self.detail_meta.setWordWrap(True)
        self.detail_meta.setStyleSheet("color: #4b5563; font-size: 13px;")
        panel_layout.addWidget(self.detail_meta)

        self.detail_description = QLabel("Select an item from the list or grid to see more information and the barcode.")
        self.detail_description.setWordWrap(True)
        self.detail_description.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.detail_description)

        self.detail_barcode = QLabel()
        self.detail_barcode.setFixedSize(220, 100)
        self.detail_barcode.setAlignment(Qt.AlignCenter)
        self.detail_barcode.setStyleSheet("background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;")
        panel_layout.addWidget(self.detail_barcode, 0, Qt.AlignHCenter)

        panel_layout.addStretch()
        return panel

    def _create_barcode_pixmap(self, item_data, width=200, height=80):
        item_data = dict(item_data)  # Convert from RowProxy to dict if needed
        sku = item_data.get('sku')
        if not sku:
            sku = f"ID-{item_data['id']}"
        
        import io
        Code128 = barcode.get_barcode_class('code128')
        rv = io.BytesIO()
        Code128(sku, writer=ImageWriter()).write(rv)
        
        pixmap = QPixmap()
        pixmap.loadFromData(rv.getvalue())
        return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def display_item_details(self, item_data):
        item_data = dict(item_data)  # Convert from RowProxy to dict if needed
        self.current_item = item_data  # Track currently displayed item
        self.update_icon_btn.setVisible(True) # Show update button
        self.delete_icon_btn.setVisible(True)  # Show delete button
        image_path = item_data.get('image_path')
        # Load image: supports Base64 data URIs (new) and file paths (legacy)
        pixmap = None
        if image_path:
            if image_path.startswith("data:"):
                import base64 as _b64
                header, data = image_path.split(",", 1)
                raw = _b64.b64decode(data)
                qpix = QPixmap()
                qpix.loadFromData(raw)
                pixmap = qpix if not qpix.isNull() else None
            else:
                p = Path(image_path)
                if p.exists():
                    pixmap = QPixmap(str(p))
        if pixmap:
            self.detail_image.setPixmap(pixmap.scaled(
                self.detail_image.width(), self.detail_image.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.detail_image.setPixmap(QPixmap())
            self.detail_image.setText("No image available")

        self.detail_name.setText(str(item_data.get('name', 'Unnamed Item')))
        sku = item_data.get('sku') or 'N/A'
        category = item_data.get('category_name') or 'N/A'
        price = float(item_data.get('price', 0.0))
        quantity = item_data.get('quantity', 0)
        threshold = item_data.get('low_stock_threshold', 'N/A')
        self.detail_meta.setText(
            f"<b>SKU:</b> {sku}<br>"
            f"<b>Category:</b> {category}<br>"
            f"<b>Price:</b> Php {price:.2f}<br>"
            f"<b>Stock:</b> {quantity}<br>"
            f"<b>Low stock threshold:</b> {threshold}"
        )
        description = item_data.get('description') or 'No description available.'
        self.detail_description.setText(description)
        self.detail_barcode.setPixmap(self._create_barcode_pixmap(item_data))

    def show_add_dialog(self):
        """Show dialog to add a new item."""
        dialog = AddItemDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            self.search_input.clear()  # Clear search
            self.item_changed.emit()  # Notify dashboard of change
            self.refresh_items()  # Refresh to show new item

    def show_update_dialog(self):
        """Show dialog to update the currently displayed item."""
        if not self.current_item:
            return
        dialog = AddItemDialog(self.db, self, item_data=self.current_item)
        if dialog.exec() == QDialog.Accepted:
            self.item_changed.emit()  # Notify dashboard of change
            self.refresh_items()  # Refresh to show updated item
            # Re-fetch the updated item to display it correctly
            updated_item = self.db.get_item(self.current_item['id'])
            if updated_item:
                items = self.db.search_items(updated_item['name'])
                for itm in items:
                    if itm['id'] == updated_item['id']:
                        self.display_item_details(itm)
                        break

    def show_delete_dialog(self):
        """Show dialog to delete the currently displayed item."""
        if not self.current_item:
            return
        dialog = DeleteItemDialog(self.db, self.current_item, self)
        if dialog.exec() == QDialog.Accepted and dialog.deleted_item:
            # Reset the detail panel to empty state
            self.current_item = None
            self.update_icon_btn.setVisible(False)
            self.delete_icon_btn.setVisible(False)
            self.detail_image.setPixmap(QPixmap())
            self.detail_image.setText("No item selected")
            self.detail_name.setText("Select an item to view details")
            self.detail_meta.setText("<i>SKU, category, price, and stock will appear here.</i>")
            self.detail_description.setText("Select an item from the list or grid to see more information and the barcode.")
            self.detail_barcode.setPixmap(QPixmap())
            self.search_input.clear()
            self.refresh_items()
            self.item_changed.emit()

    def item_sorter(self, default_text="Sort by..."):
        self.sorter_btn = QPushButton(default_text)
        self.sorter_btn.setCursor(Qt.PointingHandCursor)
        self.sorter_btn.setFixedWidth(150)
        self.sorter_btn.setStyleSheet("""
            QPushButton {
                background-color: white; color: #374151;
                border: 1px solid #d1d5db; border-radius: 6px;
                padding: 8px 15px; font-size: 12px; font-weight: 600;
                text-align: center;
            }
            QPushButton:hover { background-color: #f9fafb; border-color: #4f46e5; }
            QPushButton::menu-indicator { image: none; }
        """)
        itemSorter_menu = QMenu(self.sorter_btn)
        itemSorter_menu.setStyleSheet("""
            QMenu { background-color: #ffffff; color: #374151;
                border: 1px solid #d1d5db; border-radius: 4px; padding: 5px; }
            QMenu::item { padding: 8px 25px; background-color: transparent; }
            QMenu::item:selected { background-color: #4f46e5; color: white; border-radius: 2px; }
        """)
        options = [
            ("By name (Alphabetical)", "name"),
            ("By time added",          "time_added"),
            ("By Price",               "price"),
            ("By Quantity",            "quantity"),
            ("By Saleability",         "saleability"),
        ]
        for label, key in options:
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, lbl=label, k=key: self._apply_sort(lbl, k))
            itemSorter_menu.addAction(action)
        self.sorter_btn.setMenu(itemSorter_menu)
        return self.sorter_btn

    def _apply_sort(self, label, key):
        self.sort_key = key
        self.sorter_btn.setText(label)
        self.refresh_items()

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