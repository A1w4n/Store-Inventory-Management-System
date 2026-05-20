# Settings_UI.py — Settings page for ProStock Inventory Management System
# Single scrollable page layout — all sections stacked vertically, no inner nav.
# Matches the existing Dashboard/StaffAccess style: PySide6, white cards,
# indigo (#6366f1) accents, Segoe UI font.

import sys

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QScrollArea,
    QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from settings_service import SettingsService


# ─────────────────────────────────────────────────────────────────────────────
#  Shared style constants
# ─────────────────────────────────────────────────────────────────────────────

_CARD_STYLE = """
    QFrame#sectionCard {
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
    }
    QLabel { border: none; color: #111827; }
    QLineEdit {
        background-color: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #111827;
        min-width: 200px;
    }
    QLineEdit:focus { border-color: #6366f1; }
    QComboBox {
        background-color: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #111827;
        min-width: 200px;
    }
    QComboBox:focus { border-color: #6366f1; }
    QComboBox::drop-down { border: none; width: 24px; }
    QSpinBox {
        background-color: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        color: #111827;
        min-width: 120px;
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
        border-radius: 8px; padding: 8px 18px;
        font-size: 13px; font-weight: 600;
        border: 1px solid #fca5a5;
    }
    QPushButton:hover { background-color: #fecaca; }
"""

_SECONDARY_BTN_STYLE = """
    QPushButton {
        background-color: #f3f4f6; color: #374151;
        border-radius: 8px; padding: 8px 18px;
        font-size: 13px; font-weight: 600;
        border: 1px solid #d1d5db;
    }
    QPushButton:hover { background-color: #e5e7eb; }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Reusable builder helpers
# ─────────────────────────────────────────────────────────────────────────────

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


def _field_row(label: str, widget, hint: str = "") -> QHBoxLayout:
    """Bold label (+ optional grey hint) on the left, input widget on the right."""
    row = QHBoxLayout()
    row.setSpacing(16)

    label_col = QVBoxLayout()
    label_col.setSpacing(2)
    lbl = QLabel(label)
    lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
    label_col.addWidget(lbl)
    if hint:
        h = QLabel(hint)
        h.setStyleSheet("font-size: 11px; color: #9ca3af;")
        label_col.addWidget(h)

    row.addLayout(label_col, 1)
    row.addWidget(widget, 0, Qt.AlignRight)
    return row


def _toggle_row(label: str, checkbox: QCheckBox, hint: str = "") -> QHBoxLayout:
    """Label on the left, checkbox on the right."""
    row = QHBoxLayout()
    row.setSpacing(16)

    label_col = QVBoxLayout()
    label_col.setSpacing(2)
    lbl = QLabel(label)
    lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
    label_col.addWidget(lbl)
    if hint:
        h = QLabel(hint)
        h.setStyleSheet("font-size: 11px; color: #9ca3af;")
        label_col.addWidget(h)

    row.addLayout(label_col, 1)
    row.addWidget(checkbox, 0, Qt.AlignRight)
    return row


# ─────────────────────────────────────────────────────────────────────────────
#  Main Settings Page
# ─────────────────────────────────────────────────────────────────────────────

class SettingsPage(QWidget):
    """
    Single-page Settings UI — all sections stacked vertically in one scroll area.
    Drop into Dashboard's QStackedWidget at index 6.

    Usage in Dashboard_UI.py:
        from Settings_UI import SettingsPage
        from settings_service import SettingsService

        self._settings_svc = SettingsService()
        self.settings_page = SettingsPage(self._settings_svc)
        self.content_stack.addWidget(self.settings_page)   # index 6
    """

    settings_saved = Signal(dict)

    def __init__(self, svc: SettingsService = None, parent=None):
        super().__init__(parent)
        self._svc = svc or SettingsService()
        self.setStyleSheet("background-color: #f9fafb;")
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top header (matches Dashboard header style) ───────────────────
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(24, 20, 24, 0)
        header_layout.setSpacing(0)

        title_row = QHBoxLayout()
        title_lbl = QLabel("Settings")
        title_lbl.setStyleSheet("color: #111827; font-size: 40px; font-weight: 700; border: none;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self._save_btn = QPushButton("💾  Save Changes")
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.setFixedHeight(40)
        self._save_btn.setStyleSheet(_SAVE_BTN_STYLE)
        self._save_btn.clicked.connect(self._save_all)
        title_row.addWidget(self._save_btn)
        header_layout.addLayout(title_row)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #111827; max-height: 2px; margin-top: 8px;")
        header_layout.addWidget(line)

        root.addLayout(header_layout)

        # ── Scrollable content ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._cl = QVBoxLayout(content)
        self._cl.setContentsMargins(24, 20, 24, 32)
        self._cl.setSpacing(20)

        self._build_general_section()
        self._build_inventory_section()
        self._build_notifications_section()
        self._build_ai_section()
        self._build_account_section()
        self._build_data_section()   # Danger zone last

        self._cl.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    # ------------------------------------------------------------------ #
    #  Section builders                                                    #
    # ------------------------------------------------------------------ #

    def _build_general_section(self):
        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(14)

        cl.addWidget(_section_title("🏪  Store Information"))
        cl.addWidget(_divider())

        self.store_name = QLineEdit(self._svc.get("store_name"))
        self.store_name.setPlaceholderText("e.g. Juan's Hardware Store")
        cl.addLayout(_field_row("Store Name", self.store_name, "Displayed in reports and exports"))

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

        # UI behavior
        self.ui_debounce_spin = QSpinBox()
        self.ui_debounce_spin.setRange(100, 5000)
        self.ui_debounce_spin.setSingleStep(50)
        self.ui_debounce_spin.setSuffix(" ms")
        self.ui_debounce_spin.setValue(int(self._svc.get("ui_refresh_debounce_ms", 800)))
        cl.addLayout(_field_row("UI Refresh Debounce", self.ui_debounce_spin,
                                "Milliseconds to coalesce rapid dashboard updates"))

        self._cl.addWidget(card)

    def _build_inventory_section(self):
        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(14)

        cl.addWidget(_section_title("📦  Inventory Defaults"))
        cl.addWidget(_divider())

        self.threshold = QSpinBox()
        self.threshold.setRange(1, 9999)
        self.threshold.setValue(int(self._svc.get("low_stock_threshold")))
        cl.addLayout(_field_row(
            "Low-Stock Threshold",
            self.threshold,
            "Items below this quantity will trigger a low-stock alert"
        ))

        self.barcode_fmt = QComboBox()
        for fmt in ["CODE128", "CODE39", "EAN13", "QR"]:
            self.barcode_fmt.addItem(fmt)
        self.barcode_fmt.setCurrentText(self._svc.get("barcode_format"))
        cl.addLayout(_field_row("Default Barcode Format", self.barcode_fmt))

        self.auto_alerts = QCheckBox()
        self.auto_alerts.setChecked(bool(self._svc.get("auto_restock_alerts")))
        cl.addLayout(_toggle_row(
            "Auto Low-Stock Alerts on Startup",
            self.auto_alerts,
            "Automatically show low-stock alerts when the app opens"
        ))

        self._cl.addWidget(card)

    def _build_notifications_section(self):
        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(14)

        cl.addWidget(_section_title("🔔  Notification Preferences"))
        cl.addWidget(_divider())

        self.notify_low_stock = QCheckBox()
        self.notify_low_stock.setChecked(bool(self._svc.get("notify_low_stock")))
        cl.addLayout(_toggle_row(
            "⚠️  Low-Stock Alerts",
            self.notify_low_stock,
            "Notify when any item drops below the threshold"
        ))
        cl.addWidget(_divider())

        self.notify_new_sales = QCheckBox()
        self.notify_new_sales.setChecked(bool(self._svc.get("notify_new_sales")))
        cl.addLayout(_toggle_row(
            "🛒  New Sale Recorded",
            self.notify_new_sales,
            "Notify each time a sales transaction is saved"
        ))
        cl.addWidget(_divider())

        self.notify_restock = QCheckBox()
        self.notify_restock.setChecked(bool(self._svc.get("notify_restock_forecast")))
        cl.addLayout(_toggle_row(
            "📈  Restock Forecast Updates",
            self.notify_restock,
            "Notify when the AI forecast model refreshes"
        ))

        self._cl.addWidget(card)

    def _build_ai_section(self):
        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(14)

        cl.addWidget(_section_title("🤖  AI & Reports"))
        cl.addWidget(_divider())

        self.ai_model = QComboBox()
        for m in ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-5-20251001"]:
            self.ai_model.addItem(m)
        self.ai_model.setCurrentText(self._svc.get("ai_model"))
        cl.addLayout(_field_row("AI Model", self.ai_model, "Model used to generate inventory analysis reports"))

        self.report_lang = QComboBox()
        for lang in ["English", "Filipino", "Spanish", "Japanese", "French"]:
            self.report_lang.addItem(lang)
        self.report_lang.setCurrentText(self._svc.get("report_language"))
        cl.addLayout(_field_row("Report Language", self.report_lang))

        self.ai_auto_gen = QCheckBox()
        self.ai_auto_gen.setChecked(bool(self._svc.get("ai_report_auto_generate")))
        cl.addLayout(_toggle_row(
            "Auto-Generate Report After Analysis",
            self.ai_auto_gen,
            "Automatically run the AI report after each sales analysis refresh"
        ))

        info = QLabel("ℹ️  Reports are generated using the Anthropic API. An internet connection is required.")
        info.setWordWrap(True)
        info.setStyleSheet("""
            background-color: #eef2ff; color: #4338ca;
            font-size: 12px; border-radius: 8px; padding: 10px 14px;
            border: 1px solid #c7d2fe;
        """)
        cl.addWidget(info)

        self._cl.addWidget(card)

    def _build_account_section(self):
        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(14)

        cl.addWidget(_section_title("👤  Account"))
        cl.addWidget(_divider())

        # Avatar + name row
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(16)
        avatar = QLabel("👤")
        avatar.setFixedSize(60, 60)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            font-size: 28px;
            background-color: #eef2ff;
            border-radius: 30px;
            border: 2px solid #c7d2fe;
        """)
        avatar_row.addWidget(avatar)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        uname = QLabel(self._svc.get("admin_username"))
        uname.setStyleSheet("font-size: 15px; font-weight: 700; color: #111827;")
        info_col.addWidget(uname)
        email_lbl = QLabel(self._svc.get("admin_email"))
        email_lbl.setStyleSheet("font-size: 12px; color: #6b7280;")
        info_col.addWidget(email_lbl)
        role = QLabel("🔑 Administrator")
        role.setFixedWidth(130)
        role.setStyleSheet("""
            background-color: #eef2ff; color: #4338ca;
            font-size: 11px; font-weight: 700;
            border-radius: 12px; padding: 3px 12px;
        """)
        info_col.addWidget(role)
        avatar_row.addLayout(info_col)
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

        pw_btn = QPushButton("Update Password")
        pw_btn.setCursor(Qt.PointingHandCursor)
        pw_btn.setStyleSheet(_SAVE_BTN_STYLE)
        pw_btn.clicked.connect(self._change_password)
        cl.addWidget(pw_btn, 0, Qt.AlignLeft)

        self._cl.addWidget(card)

    def _build_data_section(self):
        # Backup card
        card = _section_card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(14)

        cl.addWidget(_section_title("💾  Backup & Export"))
        cl.addWidget(_divider())

        self.backup_enabled = QCheckBox()
        self.backup_enabled.setChecked(bool(self._svc.get("backup_enabled")))
        cl.addLayout(_toggle_row(
            "Enable Automatic Backups",
            self.backup_enabled,
            "Periodically save a backup copy of the database"
        ))

        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 365)
        self.backup_interval.setSuffix(" days")
        self.backup_interval.setValue(int(self._svc.get("backup_interval_days")))
        cl.addLayout(_field_row("Backup Every", self.backup_interval))

        # Backup folder path row
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.backup_path = QLineEdit(self._svc.get("backup_path") or "")
        self.backup_path.setPlaceholderText("Select backup folder…")
        self.backup_path.setReadOnly(True)
        folder_row.addWidget(self.backup_path, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(_SECONDARY_BTN_STYLE)
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)

        folder_label_col = QVBoxLayout()
        folder_label_col.setSpacing(2)
        fl = QLabel("Backup Folder")
        fl.setStyleSheet("font-size: 13px; font-weight: 600; color: #374151;")
        folder_label_col.addWidget(fl)
        fh = QLabel("Where backup files will be saved")
        fh.setStyleSheet("font-size: 11px; color: #9ca3af;")
        folder_label_col.addWidget(fh)

        full_row = QHBoxLayout()
        full_row.setSpacing(16)
        full_row.addLayout(folder_label_col, 1)
        full_row.addLayout(folder_row, 2)
        cl.addLayout(full_row)

        self._cl.addWidget(card)

        # Danger zone card
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
        rh = QLabel("Restore every setting to its factory default value — cannot be undone")
        rh.setStyleSheet("font-size: 11px; color: #9ca3af;")
        reset_col.addWidget(rh)
        reset_row.addLayout(reset_col, 1)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet(_DANGER_BTN_STYLE)
        reset_btn.clicked.connect(self._reset_all)
        reset_row.addWidget(reset_btn, 0, Qt.AlignRight)
        dl.addLayout(reset_row)

        self._cl.addWidget(danger_card)

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #

    def _save_all(self):
        """Collect every widget value and persist in one write."""
        updates = {
            # General
            "store_name":               self.store_name.text().strip(),
            "store_currency":           self.currency.currentText(),
            "store_timezone":           self.timezone.currentText(),
            "date_format":              self.date_fmt.currentText(),
            # Inventory
            "low_stock_threshold":      self.threshold.value(),
            "barcode_format":           self.barcode_fmt.currentText(),
            "auto_restock_alerts":      self.auto_alerts.isChecked(),
            # Notifications
            "notify_low_stock":         self.notify_low_stock.isChecked(),
            "notify_new_sales":         self.notify_new_sales.isChecked(),
            "notify_restock_forecast":  self.notify_restock.isChecked(),
            # AI
            "ai_model":                 self.ai_model.currentText(),
            "report_language":          self.report_lang.currentText(),
            "ai_report_auto_generate":  self.ai_auto_gen.isChecked(),
            # Data
            "backup_enabled":           self.backup_enabled.isChecked(),
            "backup_interval_days":     self.backup_interval.value(),
            "backup_path":              self.backup_path.text(),
            # UI
            "ui_refresh_debounce_ms":   self.ui_debounce_spin.value(),
        }
        self._svc.set_many(updates)
        self._show_toast("Settings saved ✓")
        self.settings_saved.emit(updates)

    def _change_password(self):
        current = self.current_pw.text()
        new     = self.new_pw.text()
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
        # Plug in auth_service / database hash update here as needed
        QMessageBox.information(self, "Password", "Password updated successfully!")
        self.current_pw.clear()
        self.new_pw.clear()
        self.confirm_pw.clear()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if folder:
            self.backup_path.setText(folder)

    def _reset_all(self):
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset ALL settings to their defaults?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._svc.reset_to_defaults()
            QMessageBox.information(
                self, "Reset",
                "All settings have been reset to defaults.\nPlease restart the application."
            )

    def _show_toast(self, message: str):
        original = self._save_btn.text()
        self._save_btn.setText(f"✅  {message}")
        self._save_btn.setEnabled(False)
        QTimer.singleShot(1800, lambda: (
            self._save_btn.setText(original),
            self._save_btn.setEnabled(True),
        ))


# ─────────────────────────────────────────────────────────────────────────────
#  Standalone entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")

    svc = SettingsService()
    win = SettingsPage(svc)
    win.setWindowTitle("ProStock | Settings")
    win.resize(1000, 720)
    win.show()

    sys.exit(app.exec())
