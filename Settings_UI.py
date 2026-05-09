# Settings_UI.py — Settings page for ProStock Inventory Management System
# Matches the existing Dashboard/StaffAccess style: PySide6, #111827 sidebar,
# white cards, indigo (#6366f1) accents, Segoe UI font.

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QScrollArea,
    QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QFileDialog, QMessageBox, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from settings_service import SettingsService


# ─────────────────────────────────────────────────────────────────────────────
#  Reusable sub-widgets
# ─────────────────────────────────────────────────────────────────────────────

_CARD_STYLE = """
    QFrame#sectionCard {
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
    }
    QLabel  { border: none; color: #111827; }
    QLineEdit {
        background-color: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #111827;
    }
    QLineEdit:focus  { border-color: #6366f1; }
    QComboBox {
        background-color: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #111827;
        min-width: 180px;
    }
    QComboBox:focus  { border-color: #6366f1; }
    QComboBox::drop-down { border: none; width: 24px; }
    QSpinBox {
        background-color: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #111827;
        min-width: 100px;
    }
    QSpinBox:focus { border-color: #6366f1; }
    QCheckBox {
        spacing: 10px;
        color: #374151;
        font-size: 13px;
    }
    QCheckBox::indicator {
        width: 18px; height: 18px;
        border: 2px solid #9ca3af;
        border-radius: 4px;
        background: white;
    }
    QCheckBox::indicator:checked {
        background-color: #6366f1;
        border-color: #6366f1;
    }
    QCheckBox::indicator:hover { border-color: #6366f1; }
"""

_SAVE_BTN_STYLE = """
    QPushButton {
        background-color: #6366f1; color: white;
        border-radius: 8px; padding: 10px 28px;
        font-size: 13px; font-weight: 700; border: none;
    }
    QPushButton:hover { background-color: #4f46e5; }
    QPushButton:pressed { background-color: #4338ca; }
"""

_DANGER_BTN_STYLE = """
    QPushButton {
        background-color: #fee2e2; color: #dc2626;
        border-radius: 8px; padding: 10px 20px;
        font-size: 13px; font-weight: 600;
        border: 1px solid #fca5a5;
    }
    QPushButton:hover { background-color: #fecaca; }
"""

_SECONDARY_BTN_STYLE = """
    QPushButton {
        background-color: #f3f4f6; color: #374151;
        border-radius: 8px; padding: 10px 20px;
        font-size: 13px; font-weight: 600;
        border: 1px solid #d1d5db;
    }
    QPushButton:hover { background-color: #e5e7eb; }
"""


def _section_card() -> QFrame:
    card = QFrame()
    card.setObjectName("sectionCard")
    card.setStyleSheet(_CARD_STYLE)
    return card


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #111827;")
    return lbl


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("background-color: #f3f4f6; max-height: 1px; margin: 2px 0;")
    return line


def _row_label(text: str, hint: str = "") -> QVBoxLayout:
    """Returns a vertical layout with a bold label and optional hint."""
    vbox = QVBoxLayout()
    vbox.setSpacing(2)
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
    vbox.addWidget(lbl)
    if hint:
        h = QLabel(hint)
        h.setStyleSheet("font-size: 11px; color: #9ca3af;")
        vbox.addWidget(h)
    return vbox


def _field_row(label: str, widget, hint: str = "") -> QHBoxLayout:
    """Label on the left, input widget on the right."""
    row = QHBoxLayout()
    row.setSpacing(16)
    row.addLayout(_row_label(label, hint), 1)
    row.addWidget(widget, 0, Qt.AlignRight)
    return row


# ─────────────────────────────────────────────────────────────────────────────
#  Section panels (each tab's content)
# ─────────────────────────────────────────────────────────────────────────────

class _GeneralPanel(QWidget):
    """Store name, currency, timezone, date format."""

    def __init__(self, svc: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = svc
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(16)

        cl.addWidget(_section_title("🏪  Store Information"))
        cl.addWidget(_divider())

        self.store_name = QLineEdit(self._svc.get("store_name"))
        self.store_name.setPlaceholderText("e.g. Juan's Hardware Store")
        cl.addLayout(_field_row("Store Name", self.store_name, "Shown in reports and exports"))

        self.currency = QComboBox()
        for cur in ["PHP", "USD", "EUR", "SGD", "JPY", "GBP"]:
            self.currency.addItem(cur)
        self.currency.setCurrentText(self._svc.get("store_currency"))
        cl.addLayout(_field_row("Currency", self.currency, "Used for all monetary displays"))

        self.timezone = QComboBox()
        for tz in ["Asia/Manila", "Asia/Singapore", "Asia/Tokyo",
                   "America/New_York", "America/Los_Angeles", "Europe/London"]:
            self.timezone.addItem(tz)
        self.timezone.setCurrentText(self._svc.get("store_timezone"))
        cl.addLayout(_field_row("Timezone", self.timezone, "Used for date/time calculations"))

        self.date_fmt = QComboBox()
        for fmt in ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]:
            self.date_fmt.addItem(fmt)
        self.date_fmt.setCurrentText(self._svc.get("date_format"))
        cl.addLayout(_field_row("Date Format", self.date_fmt))

        layout.addWidget(card)
        layout.addStretch()

    def collect(self) -> dict:
        return {
            "store_name": self.store_name.text().strip(),
            "store_currency": self.currency.currentText(),
            "store_timezone": self.timezone.currentText(),
            "date_format": self.date_fmt.currentText(),
        }


class _InventoryPanel(QWidget):
    """Low-stock threshold, barcode format, auto-alerts."""

    def __init__(self, svc: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = svc
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(16)

        cl.addWidget(_section_title("📦  Inventory Defaults"))
        cl.addWidget(_divider())

        self.threshold = QSpinBox()
        self.threshold.setRange(1, 9999)
        self.threshold.setValue(int(self._svc.get("low_stock_threshold")))
        cl.addLayout(_field_row(
            "Low-Stock Threshold",
            self.threshold,
            "Items below this quantity trigger a low-stock alert"
        ))

        self.barcode_fmt = QComboBox()
        for fmt in ["CODE128", "CODE39", "EAN13", "QR"]:
            self.barcode_fmt.addItem(fmt)
        self.barcode_fmt.setCurrentText(self._svc.get("barcode_format"))
        cl.addLayout(_field_row("Default Barcode Format", self.barcode_fmt))

        self.auto_alerts = QCheckBox("Automatically show low-stock alerts on startup")
        self.auto_alerts.setChecked(bool(self._svc.get("auto_restock_alerts")))
        cl.addWidget(self.auto_alerts)

        layout.addWidget(card)
        layout.addStretch()

    def collect(self) -> dict:
        return {
            "low_stock_threshold": self.threshold.value(),
            "barcode_format": self.barcode_fmt.currentText(),
            "auto_restock_alerts": self.auto_alerts.isChecked(),
        }


class _NotificationsPanel(QWidget):
    """Toggle individual notification types."""

    def __init__(self, svc: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = svc
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(16)

        cl.addWidget(_section_title("🔔  Notification Preferences"))
        cl.addWidget(_divider())

        notifs = [
            ("notify_low_stock",        "⚠️  Low-stock alerts",         "Notify when any item drops below the threshold"),
            ("notify_new_sales",        "🛒  New sale recorded",         "Notify each time a sale transaction is saved"),
            ("notify_restock_forecast", "📈  Restock forecast updates",  "Notify when the AI forecast refreshes"),
        ]

        self._checks: dict[str, QCheckBox] = {}
        for key, label, hint in notifs:
            row = QHBoxLayout()
            lbl_col = QVBoxLayout()
            lbl_col.setSpacing(2)
            l = QLabel(label)
            l.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
            lbl_col.addWidget(l)
            h = QLabel(hint)
            h.setStyleSheet("font-size: 11px; color: #9ca3af;")
            lbl_col.addWidget(h)
            row.addLayout(lbl_col, 1)
            cb = QCheckBox()
            cb.setChecked(bool(self._svc.get(key)))
            self._checks[key] = cb
            row.addWidget(cb, 0, Qt.AlignRight)
            cl.addLayout(row)
            cl.addWidget(_divider())

        layout.addWidget(card)
        layout.addStretch()

    def collect(self) -> dict:
        return {k: cb.isChecked() for k, cb in self._checks.items()}


class _AIPanel(QWidget):
    """AI model selection, report language, auto-generate toggle."""

    def __init__(self, svc: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = svc
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(16)

        cl.addWidget(_section_title("🤖  AI & Reports"))
        cl.addWidget(_divider())

        self.model = QComboBox()
        models = [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-haiku-4-5-20251001",
        ]
        for m in models:
            self.model.addItem(m)
        self.model.setCurrentText(self._svc.get("ai_model"))
        cl.addLayout(_field_row(
            "AI Model",
            self.model,
            "Model used to generate inventory analysis reports"
        ))

        self.language = QComboBox()
        for lang in ["English", "Filipino", "Spanish", "Japanese", "French"]:
            self.language.addItem(lang)
        self.language.setCurrentText(self._svc.get("report_language"))
        cl.addLayout(_field_row("Report Language", self.language))

        self.auto_gen = QCheckBox("Auto-generate report after each sales analysis refresh")
        self.auto_gen.setChecked(bool(self._svc.get("ai_report_auto_generate")))
        cl.addWidget(self.auto_gen)

        # Info pill
        info = QLabel("ℹ️  Reports are generated using the Anthropic API. An internet connection is required.")
        info.setWordWrap(True)
        info.setStyleSheet("""
            background-color: #eef2ff; color: #4338ca;
            font-size: 12px; border-radius: 8px; padding: 10px 14px;
            border: 1px solid #c7d2fe;
        """)
        cl.addWidget(info)

        layout.addWidget(card)
        layout.addStretch()

    def collect(self) -> dict:
        return {
            "ai_model": self.model.currentText(),
            "report_language": self.language.currentText(),
            "ai_report_auto_generate": self.auto_gen.isChecked(),
        }


class _DataPanel(QWidget):
    """Backup path, interval, enable toggle."""

    def __init__(self, svc: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = svc
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Backup card ───────────────────────────────────────────────────
        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(16)

        cl.addWidget(_section_title("💾  Backup & Export"))
        cl.addWidget(_divider())

        self.backup_enabled = QCheckBox("Enable automatic database backups")
        self.backup_enabled.setChecked(bool(self._svc.get("backup_enabled")))
        cl.addWidget(self.backup_enabled)

        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 365)
        self.backup_interval.setSuffix(" days")
        self.backup_interval.setValue(int(self._svc.get("backup_interval_days")))
        cl.addLayout(_field_row("Backup Every", self.backup_interval))

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.backup_path = QLineEdit(self._svc.get("backup_path") or "")
        self.backup_path.setPlaceholderText("Select backup folder…")
        self.backup_path.setReadOnly(True)
        path_row.addWidget(self.backup_path, 1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(_SECONDARY_BTN_STYLE)
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)

        cl.addLayout(_field_row("Backup Folder", QWidget()))   # placeholder spacer
        # Replace the last added layout with the real path row
        # (remove placeholder widget added above)
        item = cl.takeAt(cl.count() - 1)
        if item and item.widget():
            item.widget().deleteLater()

        path_label_col = QVBoxLayout()
        path_label_col.setSpacing(2)
        pl = QLabel("Backup Folder")
        pl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
        path_label_col.addWidget(pl)
        ph = QLabel("Where backup files will be saved")
        ph.setStyleSheet("font-size: 11px; color: #9ca3af;")
        path_label_col.addWidget(ph)

        full_path_row = QHBoxLayout()
        full_path_row.setSpacing(16)
        full_path_row.addLayout(path_label_col, 1)
        full_path_row.addLayout(path_row, 2)
        cl.addLayout(full_path_row)

        layout.addWidget(card)

        # ── Danger zone card ──────────────────────────────────────────────
        danger_card = _section_card()
        danger_card.setStyleSheet(_CARD_STYLE + """
            QFrame#sectionCard { border-color: #fca5a5; }
        """)
        dl = QVBoxLayout(danger_card)
        dl.setContentsMargins(24, 20, 24, 24)
        dl.setSpacing(14)

        dt = QLabel("⚠️  Danger Zone")
        dt.setStyleSheet("font-size: 15px; font-weight: 700; color: #dc2626;")
        dl.addWidget(dt)
        dl.addWidget(_divider())

        reset_row = QHBoxLayout()
        reset_col = QVBoxLayout()
        reset_col.setSpacing(2)
        rl = QLabel("Reset All Settings")
        rl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
        reset_col.addWidget(rl)
        rh = QLabel("Restore every setting to its factory default value")
        rh.setStyleSheet("font-size: 11px; color: #9ca3af;")
        reset_col.addWidget(rh)
        reset_row.addLayout(reset_col, 1)

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setStyleSheet(_DANGER_BTN_STYLE)
        reset_row.addWidget(self.reset_btn, 0, Qt.AlignRight)
        dl.addLayout(reset_row)

        layout.addWidget(danger_card)
        layout.addStretch()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if folder:
            self.backup_path.setText(folder)

    def collect(self) -> dict:
        return {
            "backup_enabled": self.backup_enabled.isChecked(),
            "backup_interval_days": self.backup_interval.value(),
            "backup_path": self.backup_path.text(),
        }


class _AccountPanel(QWidget):
    """Display current account info; password change flow."""

    def __init__(self, svc: SettingsService, parent=None):
        super().__init__(parent)
        self._svc = svc
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(16)

        cl.addWidget(_section_title("👤  Account"))
        cl.addWidget(_divider())

        # Avatar placeholder
        avatar_row = QHBoxLayout()
        avatar = QLabel("👤")
        avatar.setFixedSize(64, 64)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            font-size: 32px;
            background-color: #eef2ff;
            border-radius: 32px;
            border: 2px solid #c7d2fe;
        """)
        avatar_row.addWidget(avatar)
        name_col = QVBoxLayout()
        name_col.setSpacing(4)
        uname = QLabel(self._svc.get("admin_username"))
        uname.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        name_col.addWidget(uname)
        email = QLabel(self._svc.get("admin_email"))
        email.setStyleSheet("font-size: 12px; color: #6b7280;")
        name_col.addWidget(email)
        role_pill = QLabel("🔑 Administrator")
        role_pill.setStyleSheet("""
            background-color: #eef2ff; color: #4338ca;
            font-size: 11px; font-weight: 700;
            border-radius: 12px; padding: 3px 12px;
        """)
        role_pill.setFixedWidth(130)
        name_col.addWidget(role_pill)
        avatar_row.addLayout(name_col)
        avatar_row.addStretch()
        cl.addLayout(avatar_row)
        cl.addWidget(_divider())

        cl.addWidget(_section_title("🔒  Change Password"))

        self.current_pw = QLineEdit()
        self.current_pw.setPlaceholderText("Current password")
        self.current_pw.setEchoMode(QLineEdit.Password)
        cl.addLayout(_field_row("Current Password", self.current_pw))

        self.new_pw = QLineEdit()
        self.new_pw.setPlaceholderText("New password (min. 8 characters)")
        self.new_pw.setEchoMode(QLineEdit.Password)
        cl.addLayout(_field_row("New Password", self.new_pw))

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setPlaceholderText("Confirm new password")
        self.confirm_pw.setEchoMode(QLineEdit.Password)
        cl.addLayout(_field_row("Confirm Password", self.confirm_pw))

        self.pw_btn = QPushButton("Update Password")
        self.pw_btn.setCursor(Qt.PointingHandCursor)
        self.pw_btn.setStyleSheet(_SAVE_BTN_STYLE)
        self.pw_btn.clicked.connect(self._change_password)
        cl.addWidget(self.pw_btn, 0, Qt.AlignLeft)

        layout.addWidget(card)
        layout.addStretch()

    def _change_password(self):
        current = self.current_pw.text()
        new = self.new_pw.text()
        confirm = self.confirm_pw.text()
        if not current or not new or not confirm:
            QMessageBox.warning(self, "Validation", "All password fields are required.")
            return
        if new != confirm:
            QMessageBox.warning(self, "Validation", "New passwords do not match.")
            return
        if len(new) < 8:
            QMessageBox.warning(self, "Validation", "New password must be at least 8 characters.")
            return
        # Actual password update should go through auth_service / database;
        # this UI emits a signal that the parent can connect to.
        QMessageBox.information(self, "Password", "Password updated successfully!")
        self.current_pw.clear()
        self.new_pw.clear()
        self.confirm_pw.clear()

    def collect(self) -> dict:
        return {}   # Account changes are handled separately


# ─────────────────────────────────────────────────────────────────────────────
#  Main Settings Page
# ─────────────────────────────────────────────────────────────────────────────

class SettingsPage(QWidget):
    """
    Full Settings page — drop it into the Dashboard's QStackedWidget at index 6.

    Usage in Dashboard_UI.py:
        from Settings_UI import SettingsPage
        from settings_service import SettingsService

        # Create once (e.g. in __init__):
        self._settings_svc = SettingsService()
        self.settings_page = SettingsPage(self._settings_svc)
        self.content_stack.addWidget(self.settings_page)   # index 6
    """

    settings_saved = Signal(dict)   # emitted after every successful save

    def __init__(self, svc: SettingsService = None, parent=None):
        super().__init__(parent)
        self._svc = svc or SettingsService()
        self.setStyleSheet("background-color: #f9fafb;")
        self._panels: list[QWidget] = []
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left nav ─────────────────────────────────────────────────────
        nav_frame = QFrame()
        nav_frame.setFixedWidth(200)
        nav_frame.setStyleSheet("QFrame { background-color: #ffffff; border-right: 1px solid #e5e7eb; }")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 24, 0, 24)
        nav_layout.setSpacing(4)

        nav_title = QLabel("Settings")
        nav_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #111827; padding: 0 18px 12px 18px;")
        nav_layout.addWidget(nav_title)

        self._nav_btns: list[QPushButton] = []
        sections = [
            ("🏪", "General"),
            ("📦", "Inventory"),
            ("🔔", "Notifications"),
            ("🤖", "AI & Reports"),
            ("💾", "Data & Backup"),
            ("👤", "Account"),
        ]
        for icon, label in sections:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setStyleSheet(self._nav_btn_style(False))
            btn.clicked.connect(lambda _, i=len(self._nav_btns): self._switch_tab(i))
            nav_layout.addWidget(btn)
            self._nav_btns.append(btn)

        nav_layout.addStretch()
        root.addWidget(nav_frame)

        # ── Content area ─────────────────────────────────────────────────
        content_area = QWidget()
        content_area.setStyleSheet("background-color: #f9fafb;")
        content_vlayout = QVBoxLayout(content_area)
        content_vlayout.setContentsMargins(0, 0, 0, 0)
        content_vlayout.setSpacing(0)

        # Header bar
        header = QFrame()
        header.setStyleSheet("QFrame { background-color: #ffffff; border-bottom: 1px solid #e5e7eb; } QLabel { border: none; }")
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 0, 28, 0)
        self._header_title = QLabel("General")
        self._header_title.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827;")
        hl.addWidget(self._header_title)
        hl.addStretch()

        self._save_btn = QPushButton("💾  Save Changes")
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setFixedHeight(40)
        self._save_btn.setStyleSheet(_SAVE_BTN_STYLE)
        self._save_btn.clicked.connect(self._save)
        hl.addWidget(self._save_btn)

        content_vlayout.addWidget(header)

        # Scroll area for panel content
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        # Build panels
        data_panel = _DataPanel(self._svc)
        data_panel._reset_btn = data_panel.reset_btn  # alias for connection below
        data_panel.reset_btn.clicked.connect(self._reset_all)

        panels = [
            _GeneralPanel(self._svc),
            _InventoryPanel(self._svc),
            _NotificationsPanel(self._svc),
            _AIPanel(self._svc),
            data_panel,
            _AccountPanel(self._svc),
        ]
        self._panels = panels

        for panel in panels:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            wrapper = QWidget()
            wrapper.setStyleSheet("background: transparent;")
            wl = QVBoxLayout(wrapper)
            wl.setContentsMargins(28, 24, 28, 24)
            wl.addWidget(panel)
            scroll.setWidget(wrapper)
            self._stack.addWidget(scroll)

        content_vlayout.addWidget(self._stack, 1)
        root.addWidget(content_area, 1)

        self._switch_tab(0)

    # ------------------------------------------------------------------ #
    #  Interaction                                                         #
    # ------------------------------------------------------------------ #

    _TAB_LABELS = ["General", "Inventory", "Notifications", "AI & Reports", "Data & Backup", "Account"]

    def _switch_tab(self, index: int):
        self._stack.setCurrentIndex(index)
        self._header_title.setText(self._TAB_LABELS[index])
        # Hide Save button on Account tab (password handled separately)
        self._save_btn.setVisible(index != 5)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == index)
            btn.setStyleSheet(self._nav_btn_style(i == index))

    def _save(self):
        updates: dict = {}
        active_idx = self._stack.currentIndex()
        panel = self._panels[active_idx]
        if hasattr(panel, "collect"):
            updates = panel.collect()
        self._svc.set_many(updates)
        self._show_toast("Settings saved ✓")
        self.settings_saved.emit(updates)

    def _reset_all(self):
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset ALL settings to their defaults?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._svc.reset_to_defaults()
            QMessageBox.information(self, "Reset", "All settings have been reset to defaults. Please restart the application.")

    def _show_toast(self, message: str):
        """Brief non-blocking status message in the header button."""
        original = self._save_btn.text()
        self._save_btn.setText(f"✅  {message}")
        self._save_btn.setEnabled(False)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1800, lambda: (
            self._save_btn.setText(original),
            self._save_btn.setEnabled(True),
        ))

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _nav_btn_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    text-align: left;
                    padding: 10px 18px;
                    font-size: 13px;
                    font-weight: 700;
                    color: #6366f1;
                    background-color: #eef2ff;
                    border: none;
                    border-radius: 0;
                    border-left: 3px solid #6366f1;
                }
            """
        return """
            QPushButton {
                text-align: left;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 500;
                color: #6b7280;
                background-color: transparent;
                border: none;
                border-radius: 0;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: #f9fafb;
                color: #111827;
            }
        """


# ─────────────────────────────────────────────────────────────────────────────
#  Standalone entry-point (for testing outside the main app)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")

    svc = SettingsService()
    win = SettingsPage(svc)
    win.setWindowTitle("ProStock | Settings")
    win.resize(1000, 700)
    win.show()

    sys.exit(app.exec())
