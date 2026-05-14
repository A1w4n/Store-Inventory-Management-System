from dotenv import load_dotenv
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal

from auth_service import AuthService
from Login_UI import LoginWindow as UI_Base
from Dashboard_UI import InventoryDashboard
from web_server import start_server

# ── NEW: offline-first sync ────────────────────────────────────────────────
from sync_engine import SyncEngine, SyncStatus
from synced_database import SyncedDatabase
# ──────────────────────────────────────────────────────────────────────────

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")        # Neon postgres connection string
CLOUD_URL    = os.getenv("CLOUD_URL", "")       # e.g. https://your-app.onrender.com
WEB_PORT     = 5000

# ── 1. Create the sync engine ──────────────────────────────────────────────
#    It manages the local SQLite cache AND background push/pull to the cloud.
#    CLOUD_URL  → your Render web service URL
#    DATABASE_URL → your Neon PostgreSQL connection string (used by web_server
#                   on Render; the desktop never connects to Neon directly)
engine = SyncEngine(
    local_db_path="inventory.db",
    cloud_url=CLOUD_URL,
    on_status_change=lambda status: print(f"[Sync] Status → {status}"),
    on_sync_complete=lambda summary: print(
        f"[Sync] Done — pushed={summary['pushed']}, pulled={summary['pulled']}, at={summary['ts']}"
    ),
)

# ── 2. Create the database (offline-first, wraps SQLite + queues writes) ───
#    Drop-in replacement for PostgreSQLDatabase() — same API, works offline.
db = SyncedDatabase(engine, db_path="inventory.db")

# ── 3. Start the engine AFTER the db is ready ──────────────────────────────
#    This kicks off the 30-second background sync loop.
#    First sync happens immediately: pushes any queued offline writes, then
#    pulls the latest cloud data into local SQLite.
engine.start()

# ── 4. Auth service uses the same db (unchanged) ──────────────────────────
backend = AuthService(db)


# ─────────────────────────────────────────────────────────────────────────────
#  LoginWindow — unchanged from your original
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
#  AppController — unchanged from your original
# ─────────────────────────────────────────────────────────────────────────────

class AppController:
    def __init__(self, auth_service: AuthService, db: SyncedDatabase):
        self.auth_service = auth_service
        self.db = db
        self.login_window     = LoginWindow(auth_service)
        self.dashboard_window = InventoryDashboard(db)

        self.login_window.login_success_signal.connect(self.show_dashboard)
        self.login_window.show()

    def show_dashboard(self):
        self.dashboard_window.show()

    def show_login(self):
        self.login_window.show()
        self.dashboard_window.close()


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Start the staff web portal (serves the web UI + the new sync API endpoints)
    start_server(host="0.0.0.0", port=WEB_PORT, db_path="inventory.db")
    print(f"[Staff Portal] Open http://localhost:{WEB_PORT} in any browser on this network")

    controller = AppController(backend, db)

    # Clean shutdown — stop the sync thread when Qt exits
    exit_code = app.exec()
    engine.stop()
    sys.exit(exit_code)
