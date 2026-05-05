import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QCheckBox, QVBoxLayout, QHBoxLayout,
    QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Matching the Dashboard dimensions exactly
        self.setWindowTitle("ProStock | Login")
        self.setMinimumSize(1000, 600)
        self.resize(1240, 820) 
        self._build_ui()

    def _build_ui(self):
        # Main horizontal layout to split the screen
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- LEFT SIDE: Brand/Background Section ---
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("backgroundSide")
        # Indigo/Slate gradient to match the dashboard branding
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
        
        brand_name = QLabel("Inventory")
        brand_name.setStyleSheet("color: white; font-size: 42px; font-weight: 800; background: transparent;")
        brand_name.setAlignment(Qt.AlignCenter)
        
        brand_sub = QLabel("Inventory Management System for you.")
        brand_sub.setStyleSheet("color: #9ca3af; font-size: 16px; background: transparent;")
        
        bg_layout.addWidget(brand_logo)
        bg_layout.addWidget(brand_name)
        bg_layout.addWidget(brand_sub)
        
        # --- RIGHT SIDE: Login Form Section ---
        self.form_container = QWidget()
        self.form_container.setStyleSheet("background-color: #ffffff;")
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(100, 0, 100, 0) # Center the form
        form_layout.setAlignment(Qt.AlignCenter)

        # Welcome Text
        welcome_lbl = QLabel("Welcome Back")
        welcome_lbl.setStyleSheet("font-size: 32px; font-weight: 700; color: #111827;")
        
        instruction_lbl = QLabel("Please enter your details to sign in")
        instruction_lbl.setStyleSheet("font-size: 14px; color: #6b7280; margin-bottom: 30px;")

        # Inputs
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedHeight(45)
        self.username_input.setStyleSheet(self._input_style())

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(45)
        self.password_input.setStyleSheet(self._input_style())

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
        forgot_row = QHBoxLayout()
        forgot_row.addStretch()  
        forgot_row.addWidget(self.forgot_btn)

        # Sign In Button
        self.signin_btn = QPushButton("Log In")
        self.signin_btn.setFixedHeight(45)
        self.signin_btn.setCursor(Qt.PointingHandCursor)
        self.signin_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold; margin-top: 5px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()

        # Assemble Form
        form_layout.addWidget(welcome_lbl)
        form_layout.addWidget(instruction_lbl)
        form_layout.addWidget(QLabel("Username")) 
        form_layout.addWidget(self.username_input)
        form_layout.addSpacing(0)
        form_layout.addWidget(QLabel("Password")) 
        form_layout.addWidget(self.password_input)
        form_layout.addLayout(forgot_row)
        form_layout.addSpacing(25)
        form_layout.addWidget(self.signin_btn)
        form_layout.addWidget(self.error_label)

        # Add both halves to main layout
        self.main_layout.addWidget(self.bg_frame, 1)    # Left takes 1 part
        self.main_layout.addWidget(self.form_container, 1) # Right takes 1 part

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
            QLineEdit:focus { border: 2px solid #6366f1; background-color: white; }
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())