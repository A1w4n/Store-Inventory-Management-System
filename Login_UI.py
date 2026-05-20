import sys
import threading
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QCheckBox, QVBoxLayout, QHBoxLayout,
    QFrame, QSizePolicy, QSpacerItem, QTabWidget,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient

# Import only LocalAuthStorage at module level (doesn't have heavy dependencies)
from auth import LocalAuthStorage


class QRScannerThread(QThread):
    """Thread for QR scanning to avoid UI blocking."""
    login_signal = Signal(bool, str, str)  # success, username, message
    
    def __init__(self, qr_auth):
        super().__init__()
        self.qr_auth = qr_auth
    
    def run(self):
        success, username, message = self.qr_auth.authenticate_user_qr()
        self.login_signal.emit(success, username or "", message)


class FaceRecognitionThread(QThread):
    """Thread for face authentication to avoid UI blocking."""
    login_signal = Signal(bool, str, str)

    def __init__(self, face_auth):
        super().__init__()
        self.face_auth = face_auth

    def run(self):
        success, username, message = self.face_auth.authenticate_user_face()
        self.login_signal.emit(success, username or "", message)


class LoginWindow(QWidget):
    login_success_signal = Signal(str)

    def __init__(self, auth_service=None):
        super().__init__()
        self.auth_service = auth_service
        self.storage = LocalAuthStorage()
        
        # Lazy import of heavy dependencies
        try:
            from auth import QRCodeAuth
            self.qr_auth = QRCodeAuth(self.storage)
        except ImportError:
            self.qr_auth = None

        try:
            from auth import FaceRecognitionAuth
            self.face_auth = FaceRecognitionAuth(self.storage)
        except ImportError:
            self.face_auth = None
        
        # Thread references
        self.qr_thread = None
        self.face_thread = None
        
        self.setWindowTitle("ProStock Inventory | Login")
        self.setMinimumSize(1000, 600)
        self.resize(1240, 820)
        self._build_ui()

    def _build_ui(self):
        # Main horizontal layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- LEFT SIDE: Brand/Background Section ---
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("backgroundSide")
        self.bg_frame.setStyleSheet("""
            QFrame#backgroundSide {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                            stop:0 #111827, stop:1 #4f46e5);
            }
        """)
        
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setAlignment(Qt.AlignCenter)
        
        brand_logo = QLabel("📦")
        brand_logo.setStyleSheet("font-size: 80px; background: transparent;")
        brand_logo.setAlignment(Qt.AlignCenter)
        
        brand_name = QLabel("ProStock Inventory")
        brand_name.setStyleSheet("color: white; font-size: 42px; font-weight: 800; background: transparent;")
        brand_name.setAlignment(Qt.AlignCenter)
        
        brand_sub = QLabel("ProStock Inventory Management System")
        brand_sub.setStyleSheet("color: #9ca3af; font-size: 16px; background: transparent;")
        
        bg_layout.addWidget(brand_logo)
        bg_layout.addWidget(brand_name)
        bg_layout.addWidget(brand_sub)

        # --- RIGHT SIDE: Login Form Section with Tabs ---
        self.form_container = QWidget()
        self.form_container.setStyleSheet("background-color: #ffffff;")
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(50, 30, 50, 30)
        form_layout.setAlignment(Qt.AlignTop)

        # Welcome Text
        welcome_lbl = QLabel("Welcome Back")
        welcome_lbl.setStyleSheet("font-size: 32px; font-weight: 700; color: #111827;")
        
        instruction_lbl = QLabel("Choose your authentication method")
        instruction_lbl.setStyleSheet("font-size: 14px; color: #6b7280; margin-bottom: 15px;")

        form_layout.addWidget(welcome_lbl)
        form_layout.addWidget(instruction_lbl)

        # Tab Widget for different login methods
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._tab_style())

        # Tab 1: Traditional Login
        self.traditional_tab = QWidget()
        self._build_traditional_login(self.traditional_tab)
        self.tabs.addTab(self.traditional_tab, "Traditional")

        # Tab 2: QR Code
        self.qr_tab = QWidget()
        self._build_qr_login(self.qr_tab)
        self.tabs.addTab(self.qr_tab, "QR Code")

        # Tab 3: Face Recognition
        self.face_tab = QWidget()
        self._build_face_login(self.face_tab)
        self.tabs.addTab(self.face_tab, "Face Recognition")

        form_layout.addWidget(self.tabs)
        form_layout.addStretch()

        # Add both halves to main layout
        self.main_layout.addWidget(self.bg_frame, 1)
        self.main_layout.addWidget(self.form_container, 1)

    def _build_traditional_login(self, tab):
        """Build traditional username/password login tab."""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Username
        username_lbl = QLabel("Username")
        username_lbl.setStyleSheet("font-weight: 600; color: #374151;")
        layout.addWidget(username_lbl)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(45)
        self.username_input.setStyleSheet(self._input_style())
        layout.addWidget(self.username_input)

        # Password
        password_lbl = QLabel("Password")
        password_lbl.setStyleSheet("font-weight: 600; color: #374151;")
        layout.addWidget(password_lbl)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(45)
        self.password_input.setStyleSheet(self._input_style())
        layout.addWidget(self.password_input)

        # Remember me + Forgot password
        forgot_row = QHBoxLayout()
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setStyleSheet("color: #6b7280;")
        forgot_row.addWidget(self.remember_checkbox)
        forgot_row.addStretch()
        
        self.forgot_btn = QPushButton("Forgot password?")
        self.forgot_btn.setStyleSheet("""
            QPushButton {
                color: #4f46e5;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
            QPushButton:hover { color: #4338ca; text-decoration: underline; }
        """)
        forgot_row.addWidget(self.forgot_btn)
        layout.addLayout(forgot_row)

        # Sign In Button
        self.signin_btn = QPushButton("Log In")
        self.signin_btn.setFixedHeight(45)
        self.signin_btn.setCursor(Qt.PointingHandCursor)
        self.signin_btn.setStyleSheet(self._button_style())
        self.signin_btn.clicked.connect(self._handle_traditional_login)
        layout.addWidget(self.signin_btn)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        layout.addStretch()

    def _build_face_login(self, tab):
        """Build face recognition login tab."""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel("😀")
        icon_label.setStyleSheet("font-size: 60px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        info_label = QLabel("Face Recognition Login")
        info_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #111827; text-align: center;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        desc_label = QLabel("Register your face once, then use the camera to login.")
        desc_label.setStyleSheet("font-size: 13px; color: #6b7280; text-align: center; margin: 15px 0px;")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)

        layout.addSpacing(20)

        self.face_scan_btn = QPushButton("Start Face Authentication")
        self.face_scan_btn.setFixedHeight(45)
        self.face_scan_btn.setCursor(Qt.PointingHandCursor)
        self.face_scan_btn.setStyleSheet(self._button_style())
        self.face_scan_btn.clicked.connect(self._start_face_auth)
        layout.addWidget(self.face_scan_btn)

        self.face_error_label = QLabel("")
        self.face_error_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold; text-align: center;")
        self.face_error_label.hide()
        layout.addWidget(self.face_error_label)

        layout.addSpacing(20)

        self.register_face_btn = QPushButton("Register New Face")
        self.register_face_btn.setFixedHeight(40)
        self.register_face_btn.setCursor(Qt.PointingHandCursor)
        self.register_face_btn.setStyleSheet(self._secondary_button_style())
        self.register_face_btn.clicked.connect(self._register_new_face)
        layout.addWidget(self.register_face_btn)

        layout.addStretch()

    def _build_qr_login(self, tab):
        """Build QR code login tab."""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel("📱")
        icon_label.setStyleSheet("font-size: 60px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        info_label = QLabel("QR Code Login")
        info_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #111827; text-align: center;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        desc_label = QLabel("Click below to scan your QR code.\nPosition the QR code in front of your camera.")
        desc_label.setStyleSheet("font-size: 13px; color: #6b7280; text-align: center; margin: 15px 0px;")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)

        layout.addSpacing(20)

        # Scan button
        self.qr_scan_btn = QPushButton("Start QR Scan")
        self.qr_scan_btn.setFixedHeight(45)
        self.qr_scan_btn.setCursor(Qt.PointingHandCursor)
        self.qr_scan_btn.setStyleSheet(self._button_style())
        self.qr_scan_btn.clicked.connect(self._start_qr_auth)
        layout.addWidget(self.qr_scan_btn)

        # QR error label
        self.qr_error_label = QLabel("")
        self.qr_error_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold; text-align: center;")
        self.qr_error_label.hide()
        layout.addWidget(self.qr_error_label)

        layout.addSpacing(20)

        # Register QR button
        self.register_qr_btn = QPushButton("Generate New QR Code")
        self.register_qr_btn.setFixedHeight(40)
        self.register_qr_btn.setCursor(Qt.PointingHandCursor)
        self.register_qr_btn.setStyleSheet(self._secondary_button_style())
        self.register_qr_btn.clicked.connect(self._register_new_qr)
        layout.addWidget(self.register_qr_btn)

        layout.addStretch()

    def _handle_traditional_login(self):
        """Handle traditional username/password login."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self._show_error("Please enter both username and password", self.error_label)
            return

        if self.auth_service:
            success, message = self.auth_service.validate_login(username, password)
            if success:
                self.storage.log_auth_attempt(username, "traditional", True)
                self._on_login_success(username)
            else:
                self.storage.log_auth_attempt(username, "traditional", False)
                self._show_error(message, self.error_label)
        else:
            QMessageBox.warning(self, "Error", "Auth service not configured")

    def _start_qr_auth(self):
        """Start QR code authentication in a separate thread."""
        if not self.qr_auth:
            QMessageBox.warning(self, "Error", "QR code scanning not available. Install qrcode and pyzbar packages.")
            return
        
        self.qr_scan_btn.setEnabled(False)
        self.qr_scan_btn.setText("Scanning...")
        self.qr_error_label.hide()

        self.qr_thread = QRScannerThread(self.qr_auth)
        self.qr_thread.login_signal.connect(self._handle_qr_auth_result)
        self.qr_thread.start()

    def _start_face_auth(self):
        """Start face recognition authentication in a separate thread."""
        if not self.face_auth:
            QMessageBox.warning(self, "Error", "Face recognition not available. Install face-recognition and opencv-python packages.")
            return

        self.face_scan_btn.setEnabled(False)
        self.face_scan_btn.setText("Authenticating...")
        self.face_error_label.hide()

        self.face_thread = FaceRecognitionThread(self.face_auth)
        self.face_thread.login_signal.connect(self._handle_face_auth_result)
        self.face_thread.start()

    def _handle_face_auth_result(self, success, username, message):
        """Handle face authentication result."""
        self.face_scan_btn.setEnabled(True)
        self.face_scan_btn.setText("Start Face Authentication")

        if success:
            self._on_login_success(username)
        else:
            self._show_error(message, self.face_error_label)

    def _register_new_face(self):
        """Register a new face — requires password verification first."""
        if not self.face_auth:
            QMessageBox.warning(self, "Error", "Face recognition not available. Install face-recognition and opencv-python packages.")
            return

        if not self._verify_password_dialog():
            return  # user cancelled or failed password check

        username, ok = self._get_username_dialog()
        if not ok or not username:
            return

        try:
            success, message = self.face_auth.capture_and_register_face(username)
            if success:
                QMessageBox.information(self, "Face Registered", message)
            else:
                self._show_error(message, self.face_error_label)
        except Exception as e:
            self._show_error(f"Error: {str(e)}", self.face_error_label)

    def _handle_qr_auth_result(self, success, username, message):
        """Handle QR authentication result."""
        self.qr_scan_btn.setEnabled(True)
        self.qr_scan_btn.setText("Start QR Scan")

        if success:
            self._on_login_success(username)
        else:
            self._show_error(message, self.qr_error_label)

    def _register_new_qr(self):
        """Register a new QR code — requires password verification first."""
        if not self._verify_password_dialog():
            return  # user cancelled or failed password check

        username, ok = self._get_username_dialog()
        if not ok or not username:
            return

        try:
            success, qr_data, message = self.qr_auth.generate_qr_code(username)
            if success:
                QMessageBox.information(self, "QR Code Generated",
                                       f"{message}\n\nYour QR code has been saved.")
            else:
                self._show_error(message, self.qr_error_label)
        except Exception as e:
            self._show_error(f"Error: {str(e)}", self.qr_error_label)

    def _verify_password_dialog(self):
        """Show a password prompt and verify it against the auth service.
        
        Returns True if the password is correct, False otherwise.
        The user gets 3 attempts before being locked out of the dialog.
        """
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Password Required")
        dialog.setFixedWidth(380)
        dialog.setStyleSheet("background-color: #ffffff;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        # Header
        title = QLabel("🔒  Verify Your Password")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        layout.addWidget(title)

        sub = QLabel("Enter your password to continue with this action.")
        sub.setStyleSheet("font-size: 13px; color: #6b7280;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Username field (pre-filled if traditional login was used)
        user_lbl = QLabel("Username")
        user_lbl.setStyleSheet("font-weight: 600; color: #374151; font-size: 13px;")
        layout.addWidget(user_lbl)

        user_input = QLineEdit()
        user_input.setPlaceholderText("Enter your username")
        user_input.setFixedHeight(40)
        user_input.setStyleSheet(self._input_style())
        # Pre-fill from traditional login tab if available
        prefill = self.username_input.text().strip()
        if prefill:
            user_input.setText(prefill)
        layout.addWidget(user_input)

        # Password field
        pass_lbl = QLabel("Password")
        pass_lbl.setStyleSheet("font-weight: 600; color: #374151; font-size: 13px;")
        layout.addWidget(pass_lbl)

        pass_input = QLineEdit()
        pass_input.setPlaceholderText("Enter your password")
        pass_input.setEchoMode(QLineEdit.Password)
        pass_input.setFixedHeight(40)
        pass_input.setStyleSheet(self._input_style())
        layout.addWidget(pass_input)

        # Error label (hidden until a wrong attempt)
        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
        err_lbl.hide()
        layout.addWidget(err_lbl)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("Confirm")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet(self._button_style())
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet(self._secondary_button_style())
        layout.addWidget(btn_box)

        attempts = [0]
        MAX_ATTEMPTS = 3
        verified = [False]

        def _try_verify():
            username = user_input.text().strip()
            password = pass_input.text().strip()

            if not username or not password:
                err_lbl.setText("Please enter both username and password.")
                err_lbl.show()
                return

            if not self.auth_service:
                err_lbl.setText("Auth service not configured.")
                err_lbl.show()
                return

            success, _ = self.auth_service.validate_login(username, password)
            if success:
                verified[0] = True
                dialog.accept()
            else:
                attempts[0] += 1
                remaining = MAX_ATTEMPTS - attempts[0]
                if remaining > 0:
                    err_lbl.setText(f"Incorrect password. {remaining} attempt(s) remaining.")
                    pass_input.clear()
                    pass_input.setFocus()
                else:
                    err_lbl.setText("Too many failed attempts.")
                    btn_box.button(QDialogButtonBox.Ok).setEnabled(False)
                err_lbl.show()

        btn_box.accepted.connect(_try_verify)
        btn_box.rejected.connect(dialog.reject)
        pass_input.returnPressed.connect(_try_verify)

        dialog.exec()
        return verified[0]

    def _get_username_dialog(self):
        """Show dialog to get username."""
        from PySide6.QtWidgets import QInputDialog
        username, ok = QInputDialog.getText(self, "Enter Username", 
                                           "Username for registration:")
        return username, ok

    def _on_login_success(self, username):
        self.login_success_signal.emit(username)
        self.close()

    def _show_error(self, message, label):
        """Show error message in label."""
        label.setText(message)
        label.show()

    def _input_style(self):
        return """
            QLineEdit {
                background-color: #f9fafb;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                color: #111827;
            }
            QLineEdit:focus { 
                border: 2px solid #6366f1; 
                background-color: white; 
            }
        """

    def _button_style(self):
        return """
            QPushButton {
                background-color: #6366f1;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover { 
                background-color: #4f46e5; 
            }
            QPushButton:pressed { 
                background-color: #4338ca; 
            }
        """

    def _secondary_button_style(self):
        return """
            QPushButton {
                background-color: #e5e7eb;
                color: #374151;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                border: 1px solid #d1d5db;
            }
            QPushButton:hover { 
                background-color: #d1d5db; 
            }
        """

    def _tab_style(self):
        return """
            QTabWidget::pane { 
                border: 1px solid #e5e7eb; 
                background: white;
            }
            QTabBar::tab { 
                background-color: #f3f4f6;
                color: #6b7280;
                padding: 8px 20px;
                margin-right: 2px;
                border: 1px solid #e5e7eb;
            }
            QTabBar::tab:selected { 
                background-color: white;
                color: #111827;
                border-bottom: 2px solid #6366f1;
            }
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())