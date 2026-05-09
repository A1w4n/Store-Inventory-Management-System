from dotenv import load_dotenv
from cloud_sync import CloudSync
import os
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Signal
from auth_service import AuthService
from Login_UI import LoginWindow as UI_Base
from Dashboard_UI import InventoryDashboard
from database import InventoryDatabase
from web_server import start_server 

# Load environment variables from .env
load_dotenv()

# Run sync before launching app
sync = CloudSync()
sync.sync_all()

# Fetch variables
DATABASE_URL = os.getenv("DATABASE_URL")

# For local SQLite
db = InventoryDatabase(backend="sqlite", db_path="inventory.db")

# For PostgreSQL (if DATABASE_URL is set)
db = InventoryDatabase(
    backend="postgres",
    pg_url="postgresql://neondb_owner:npg_UAfxw7k9KFaP@ep-broad-water-aov46oze-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

# ── Pass db into your services ─────────────────────────
backend = AuthService(db)

if DATABASE_URL:
    try:
        import psycopg2
        connection = psycopg2.connect(DATABASE_URL)
        print("Database connected successfully!")
    except ImportError:
        print("[WARNING] psycopg2 not installed, skipping PostgreSQL connectivity test.")
    except Exception as e:
        print(f"Error connecting to database: {e}")
else:
    print("[INFO] DATABASE_URL not set, skipping PostgreSQL connectivity test.")

WEB_PORT = 5000


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
    def __init__(self, auth_service: AuthService, db: InventoryDatabase):
        self.auth_service = auth_service
        self.db = db
        self.login_window = LoginWindow(auth_service)
        self.dashboard_window = InventoryDashboard(db)

        self.login_window.login_success_signal.connect(self.show_dashboard)
        self.login_window.show()

    def show_dashboard(self):
        self.dashboard_window.show()

    def show_login(self):
        self.login_window.show()
        self.dashboard_window.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    db      = InventoryDatabase()
    backend = AuthService(db)

    # Start the staff web portal in a background daemon thread
    start_server(host="0.0.0.0", port=WEB_PORT, db_path="inventory.db")
    print(f"[Staff Portal] Open http://localhost:{WEB_PORT} in any browser on this network")

    controller = AppController(backend, db)
    sys.exit(app.exec())
