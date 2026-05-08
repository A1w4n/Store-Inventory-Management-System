import sys
import socket
import qrcode
from io import BytesIO
from PIL import Image as PILImage

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QScrollArea, QLineEdit
)
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QPixmap, QFont, QImage


WEB_PORT = 5000


def _get_local_ip() -> str:
    """Return the machine's LAN IP, fallback to 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _make_qr_pixmap(url: str, box_size: int = 8, border: int = 3) -> QPixmap:
    """Generate a QR code for *url* and return it as a QPixmap."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img: PILImage.Image = qr.make_image(fill_color="#111827", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    q_img = QImage.fromData(QByteArray(buf.read()), "PNG")
    return QPixmap.fromImage(q_img)


class _SectionCard(QFrame):
    """Reusable card container matching the dashboard card aesthetic."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self.setStyleSheet("""
            QFrame#sectionCard {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e5e7eb;
            }
            QLabel { border: none; color: #111827; }
        """)


class _InfoRow(QHBoxLayout):
    """Icon + bold label + value row used in the info grid."""

    def __init__(self, icon: str, label: str, value: str):
        super().__init__()
        self.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(28)
        icon_lbl.setStyleSheet("font-size: 18px;")

        key_lbl = QLabel(label)
        key_lbl.setFixedWidth(130)
        key_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size: 13px; color: #6b7280;")
        val_lbl.setWordWrap(True)

        self.addWidget(icon_lbl)
        self.addWidget(key_lbl)
        self.addWidget(val_lbl, 1)


class StaffAccessPage(QWidget):
    """
    'Staff Access' page — replaces the old 'About' placeholder.

    Displays:
      • A QR code pointing to the local staff web portal.
      • The full URL so staff can type it manually if needed.
      • Connection instructions & feature summary for the web portal.
      • A refresh button that regenerates the QR code / URL on demand.
    """

    def __init__(self, port: int = WEB_PORT, parent=None):
        super().__init__(parent)
        self.port = port
        self.setStyleSheet("background-color: #f9fafb;")
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(0)

        # ── Page header ───────────────────────────────────────────────
        header_row = QHBoxLayout()

        page_title = QLabel("Staff Access Portal")
        page_title.setStyleSheet(
            "font-size: 38px; font-weight: 700; color: #111827;"
        )
        header_row.addWidget(page_title)
        header_row.addStretch()

        self.refresh_btn = QPushButton("🔄  Refresh QR")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setFixedHeight(38)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border-radius: 8px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        self.refresh_btn.clicked.connect(self._refresh)
        header_row.addWidget(self.refresh_btn)

        root.addLayout(header_row)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e5e7eb; max-height: 1px; margin: 10px 0 18px 0;")
        root.addWidget(line)

        # ── Scroll area (keeps layout stable on small screens) ────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(20)

        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ── Top row: QR card + Info card ──────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        top_row.addWidget(self._build_qr_card(), 0)
        top_row.addWidget(self._build_info_card(), 1)

        inner_layout.addLayout(top_row)

        # ── Bottom row: Instructions card ─────────────────────────────
        inner_layout.addWidget(self._build_instructions_card())
        inner_layout.addStretch()

    # ------------------------------------------------------------------
    # Card builders
    # ------------------------------------------------------------------

    def _build_qr_card(self) -> QFrame:
        card = _SectionCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignHCenter)

        badge = QLabel("📱  Scan to Connect")
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("""
            font-size: 13px; font-weight: 700; color: #6366f1;
            background-color: #eef2ff;
            border-radius: 20px; padding: 4px 14px;
        """)
        layout.addWidget(badge, 0, Qt.AlignHCenter)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(240, 240)
        self._update_qr_pixmap()
        layout.addWidget(self.qr_label, 0, Qt.AlignHCenter)

        note = QLabel("Point your phone camera\nat the QR code above")
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("font-size: 12px; color: #9ca3af;")
        layout.addWidget(note, 0, Qt.AlignHCenter)

        return card

    def _build_info_card(self) -> QFrame:
        card = _SectionCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        # Title
        title = QLabel("Connection Details")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        layout.addWidget(title)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #f3f4f6; max-height: 1px;")
        layout.addWidget(divider)

        # URL row with copy button
        url_label = QLabel("Portal URL")
        url_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #6b7280; letter-spacing: 0.5px;")
        layout.addWidget(url_label)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)

        self.url_field = QLineEdit(self._get_url())
        self.url_field.setReadOnly(True)
        self.url_field.setFixedHeight(38)
        self.url_field.setStyleSheet("""
            QLineEdit {
                background-color: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 13px;
                color: #374151;
                font-family: monospace;
            }
        """)
        url_row.addWidget(self.url_field, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedHeight(38)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #111827;
                color: white;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { background-color: #1f2937; }
        """)
        copy_btn.clicked.connect(self._copy_url)
        url_row.addWidget(copy_btn)
        layout.addLayout(url_row)

        # Info grid
        layout.addSpacing(4)
        ip = _get_local_ip()

        rows = [
            ("🌐", "Host IP",      ip),
            ("🔌", "Port",         str(self.port)),
            ("🔒", "Access",       "Local network only"),
            ("🌍", "Browser",      "Any modern browser"),
            ("👤", "Login",        "Use your ProStock credentials"),
        ]
        for icon, label, value in rows:
            layout.addLayout(_InfoRow(icon, label, value))

        layout.addStretch()
        return card

    def _build_instructions_card(self) -> QFrame:
        card = _SectionCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)

        title = QLabel("How to Access the Staff Web Portal")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        layout.addWidget(title)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #f3f4f6; max-height: 1px;")
        layout.addWidget(divider)

        steps_row = QHBoxLayout()
        steps_row.setSpacing(16)

        steps = [
            ("1", "#6366f1", "Connect to the same\nWi-Fi network as\nthis computer."),
            ("2", "#0ea5e9", "Scan the QR code with\nyour phone camera\nor open the URL."),
            ("3", "#10b981", "Log in using your\nexisting ProStock\nusername & password."),
            ("4", "#f59e0b", "Use the portal to\ncheck stock, record\nsales, and browse items."),
        ]

        for num, color, text in steps:
            step_frame = QFrame()
            step_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #fafafa;
                    border-radius: 10px;
                    border: 1px solid #e5e7eb;
                }}
                QLabel {{ border: none; }}
            """)
            step_layout = QVBoxLayout(step_frame)
            step_layout.setContentsMargins(18, 18, 18, 18)
            step_layout.setSpacing(10)

            circle = QLabel(num)
            circle.setFixedSize(36, 36)
            circle.setAlignment(Qt.AlignCenter)
            circle.setStyleSheet(f"""
                background-color: {color};
                color: white;
                font-size: 16px;
                font-weight: 800;
                border-radius: 18px;
            """)
            step_layout.addWidget(circle)

            desc = QLabel(text)
            desc.setStyleSheet("font-size: 13px; color: #374151; line-height: 1.5;")
            desc.setWordWrap(True)
            step_layout.addWidget(desc)
            step_layout.addStretch()

            steps_row.addWidget(step_frame, 1)

        layout.addLayout(steps_row)

        # Feature bullets
        layout.addSpacing(6)

        feat_title = QLabel("What staff can do on the portal:")
        feat_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #374151;")
        layout.addWidget(feat_title)

        features_row = QHBoxLayout()
        features_row.setSpacing(10)

        features = [
            ("📋", "View inventory list & item details"),
            ("📉", "Check low-stock alerts in real time"),
            ("🛒", "Record sales transactions"),
            ("🔍", "Search & filter items by category"),
        ]
        for icon, text in features:
            pill = QLabel(f"{icon}  {text}")
            pill.setStyleSheet("""
                background-color: #eef2ff;
                color: #4338ca;
                font-size: 12px;
                font-weight: 600;
                border-radius: 20px;
                padding: 6px 14px;
            """)
            features_row.addWidget(pill)
        features_row.addStretch()
        layout.addLayout(features_row)

        return card

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_url(self) -> str:
        import os
        cloud_url = os.environ.get("STAFF_PORTAL_URL", "")
        if cloud_url:
            return cloud_url
        return f"http://{_get_local_ip()}:{self.port}"

    def _update_qr_pixmap(self):
        url = self._get_url()
        pixmap = _make_qr_pixmap(url, box_size=7, border=2)
        self.qr_label.setPixmap(
            pixmap.scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _refresh(self):
        """Regenerate QR and URL (useful if server IP changed)."""
        new_url = self._get_url()
        self._update_qr_pixmap()
        self.url_field.setText(new_url)

    def _copy_url(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.url_field.text())


# ------------------------------------------------------------------
# Standalone preview
# ------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    win = StaffAccessPage()
    win.setWindowTitle("ProStock | Staff Access Portal")
    win.resize(1000, 680)
    win.show()
    sys.exit(app.exec())
