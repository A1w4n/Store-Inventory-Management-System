from dotenv import load_dotenv

import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QMetaObject, Qt

from auth_service import AuthService
from Login_UI import LoginWindow as UI_Base
from Dashboard_UI import InventoryDashboard
from web_server import start_server
from sync_engine import SyncEngine, SyncStatus
from synced_database import SyncedDatabase

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")   # Neon postgres connection string
CLOUD_URL    = os.getenv("CLOUD_URL", "")  # Render connection string
WEB_PORT     = 5000

engine = SyncEngine(
    local_db_path="inventory.db",
    cloud_url=CLOUD_URL,
    on_status_change=lambda status: print(f"[Sync] Status -> {status}"),
    on_sync_complete=lambda summary: print(
        f"[Sync] Done - pushed={summary['pushed']}, pulled={summary['pulled']}, at={summary['ts']}"
    ),
)

db = SyncedDatabase(engine, db_path="inventory.db")

engine.start()

backend = AuthService(db)


class LoginWindow(UI_Base):
    login_success_signal = Signal(str)

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.signin_btn.clicked.connect(self._handle_sign_in)

    def _handle_sign_in(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username:
            self._highlight_error(self.username_input)
            return
        if not password:
            self._highlight_error(self.password_input)
            return

        success, message = self.auth_service.validate_login(username, password)
        if success:
            self.login_success_signal.emit(username)
            self.close()
        else:
            self.error_label.setText("Unable to Login!")
            self.error_label.show()
            self._highlight_error(self.username_input)
            self._highlight_error(self.password_input)

    def _highlight_error(self, widget):
        widget.setStyleSheet(widget.styleSheet() + """
            QLineEdit {
                border: 2px solid #EF4444;
                background-color: #FEF2F2;
            }
        """)
        widget.setPlaceholderText("Information required!")
        widget.textChanged.connect(lambda: self._reset_input(widget))

    def _reset_input(self, widget):
        widget.setStyleSheet("""
            QLineEdit {
                background-color: #f9fafb;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                color: #111827;
            }
            QLineEdit:focus { border: 2px solid #6366f1; background-color: white; }
        """)


class AppController:
    def __init__(self, auth_service: AuthService, db: SyncedDatabase):
        self.auth_service    = auth_service
        self.db              = db
        self.login_window    = LoginWindow(auth_service)
        self.dashboard_window = InventoryDashboard(db)

        # ── KEY FIX ────────────────────────────────────────────────────────
        # The sync engine calls set_change_listener's callback from its
        # background thread. Calling QTimer.start() from that thread causes:
        #   "QObject::startTimer: Timers cannot be started from another thread"
        # Solution: wrap in QMetaObject.invokeMethod with QueuedConnection so
        # the actual on_data_changed() always runs on the Qt main thread.
        def _thread_safe_data_changed():
            QMetaObject.invokeMethod(
                self.dashboard_window,
                "on_data_changed",
                Qt.QueuedConnection
            )

        self.db.set_change_listener(_thread_safe_data_changed)
        # ───────────────────────────────────────────────────────────────────

        self.login_window.login_success_signal.connect(self.show_dashboard)
        self.dashboard_window.logout_requested.connect(self.show_login)
        self.login_window.show()

    def show_dashboard(self):
        self.dashboard_window.show()

    def show_login(self):
        self.login_window.show()
        self.dashboard_window.close()
        self.login_window.username_input.clear()
        self.login_window.password_input.clear()
        self.login_window.error_label.hide()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    start_server(host="0.0.0.0", port=WEB_PORT, db_path="inventory.db", db=db)
    print(f"[Staff Portal] Open http://localhost:{WEB_PORT} in any browser on this network")

    controller = AppController(backend, db)

    exit_code = app.exec()
    engine.stop()
    sys.exit(exit_code)
