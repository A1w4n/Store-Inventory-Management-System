import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from auth_service import AuthService

from Login_UI import LoginWindow as UI_Base 
from Dashboard_UI import InventoryDashboard

class LoginWindow(UI_Base):
    def __init__(self, auth_service: AuthService):
        # UI_Base already sets FramelessWindowHint and WA_TranslucentBackground
        super().__init__() 
        self.auth_service = auth_service  # The Backend instance
        
        # We don't call _build_ui() again because super().__init__() already does.
        # Calling it twice might create duplicate layouts.

    def _handle_sign_in(self):
        """
        The Bridge: UI collects data -> Backend processes -> UI displays result
        """
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        remember = self.remember_checkbox.isChecked()

        # Validation logic using the UI components inherited from UI_Base
        if not username:
            self._highlight_error(self.username_input)
            return
        if not password:
            self._highlight_error(self.password_input)
            return

        # Hand off data to the backend service
        success, message = self.auth_service.validate_login(username, password)

        if success:
            self.dashboard = InventoryDashboard()
            self.dashboard.show()
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", message)
            # Use the inherited error highlighting
            self._highlight_error(self.username_input)
            self._highlight_error(self.password_input)

    # Re-implementing the error highlight reset logic if not present in UI_Base
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
                background-color: #F9FAFB;
                border: 1.5px solid #D1D5DB;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 14px;
                color: #111827;
            }
            QLineEdit:focus { border: 2px solid #4F46E5; background-color: #ffffff; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Instantiate backend first
    # Ensure AuthService is defined in auth_service.py
    backend = AuthService()
    
    # Pass backend into the UI
    window = LoginWindow(backend)
    # The window is set to fullScreen in UI_Base.__init__
    window.show() 
    sys.exit(app.exec())