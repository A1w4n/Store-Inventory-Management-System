import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Signal

from auth_service import AuthService
from Login_UI import LoginWindow as UI_Base
from Dashboard_UI import InventoryDashboard
from database import InventoryDatabase

class LoginWindow(UI_Base):
    login_success_signal = Signal(str)

    def __init__(self, auth_service: AuthService):
        """
        Extends the Login UI with logic to communicate with the AuthService.
        """
        super().__init__() 
        self.auth_service = auth_service
        
        # Connect the sign-in button from Login_UI to the handler
        self.signin_btn.clicked.connect(self._handle_sign_in)

    def _handle_sign_in(self):
        """
        The Bridge: Collects credentials, validates via Backend, and toggles UI.
        """
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        # Simple UI-side validation
        if not username:
            self._highlight_error(self.username_input)
            return
        if not password:
            self._highlight_error(self.password_input)
            return

        # Backend validation
        success, message = self.auth_service.validate_login(username, password)

        if success:
            self.login_success_signal.emit(username)
            self.close()
        else:
            self.error_label.setText(f"Unable to Login!")
            self.error_label.show()
            self.highlight_error(self.username_input)
            self.highlight_error(self.password_input)

    def _highlight_error(self, widget):
        """Applies error styling if fields are empty."""
        widget.setStyleSheet(widget.styleSheet() + """
            QLineEdit {
                border: 2px solid #EF4444;
                background-color: #FEF2F2;
            }
        """)
        widget.setPlaceholderText("Information required!")
        widget.textChanged.connect(lambda: self._reset_input(widget))

    def _reset_input(self, widget):
        """Resets the input style to the standard slate theme."""
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
        #self.dashboard_window.logout_signal.connect(self.show_login)
        self.login_window.show()

    def show_dashboard(self):
        self.dashboard_window.show()

    def show_login(self):
        self.login_window.show()
        self.dashboard_window.close()       

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Initialize database and auth service
    db = InventoryDatabase()
    backend = AuthService(db_path="inventory.db")

    controller = AppController(backend, db)

    sys.exit(app.exec())
