import sys

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QCheckBox, QVBoxLayout, QHBoxLayout,
    QFrame, QGraphicsBlurEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPalette, QCursor

# for "Forgot Password?" 
class ClickableLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._default_color = "#4F46E5"
        self._hover_color   = "#3730A3"
        self._apply_style(self._default_color)

    def _apply_style(self, color):
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                font-weight: 600;
                background: transparent;
            }}
        """)

    def enterEvent(self, event):
        self._apply_style(self._hover_color)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(self._default_color)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            print("Forgot Password clicked")
        super().mousePressEvent(event)


# Main Login Window 
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setMinimumSize(800, 600)
        self._build_ui()
        self.showFullScreen()          

    #  UI Builder 
    def _build_ui(self):
        # Root layout — dark semi-transparent overlay (bg-black/50)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Overlay widget
        self.overlay = QWidget(self)
        self.overlay.setObjectName("overlay")
        self.overlay.setStyleSheet("""
            QWidget#overlay {
                background-color: rgba(0, 0, 0, 0.55);
            }
        """)
        self.overlay.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)

        # Card
        card = self._build_card()
        overlay_layout.addWidget(card, alignment=Qt.AlignCenter)

        root_layout.addWidget(self.overlay)

        # Window background colour (fallback if no image)
        self.setStyleSheet("""
            QWidget {
                background-color: #e5e7eb;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

    # Card (bg-white rounded-xl shadow-2xl max-w-md)
    def _build_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(440)
        card.setStyleSheet("""
            QFrame#card {
                background-color: #ffffff;
                border-radius: 16px;  
                border: 2px solid #000000;              
            }
        """)

        # Drop shadow via a wrapper
        card.setGraphicsEffect(self._make_shadow())

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(0)

        # Header
        layout.addWidget(self._build_header())
        layout.addSpacing(28)

        # Username
        layout.addWidget(self._label("Username or Email"))
        layout.addSpacing(6)
        self.username_input = self._build_input("Enter your username")
        layout.addWidget(self.username_input)
        layout.addSpacing(18)

        # Password
        layout.addWidget(self._label("Password"))
        layout.addSpacing(6)
        self.password_input = self._build_input("Enter your password", password=True)
        layout.addWidget(self.password_input)
        layout.addSpacing(16)

        # Remember me + Forgot password
        layout.addWidget(self._build_remember_row())
        layout.addSpacing(24)

        # Sign In button
        layout.addWidget(self._build_sign_in_button())

        return card

    #  Header
    def _build_header(self):
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        title = QLabel("Welcome Back")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: 700;
            color: #1F2937;
            background: transparent;
        """)

        subtitle = QLabel("Please sign in to your account")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #6B7280;
            background: transparent;
        """)

        v.addWidget(title)
        v.addWidget(subtitle)
        return container

    # Field Label 
    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #374151;
            background: transparent;
        """)
        return lbl

    #  Input Field 
    def _build_input(self, placeholder, password=False):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(46)

        if password:
            inp.setEchoMode(QLineEdit.Password)

        inp.setStyleSheet("""
            QLineEdit {
                background-color: #F9FAFB;
                border: 1.5px solid #D1D5DB;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 14px;
                color: #111827;
            }
            QLineEdit:focus {
                border: 2px solid #4F46E5;
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #9CA3AF;
            }
        """)
        return inp

    #  Remember Me + Forgot Password Row 
    def _build_remember_row(self):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)

        # Checkbox
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setCursor(QCursor(Qt.PointingHandCursor))
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #4B5563;
                background: transparent;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1.5px solid #D1D5DB;
                border-radius: 4px;
                background: #F9FAFB;
            }
            QCheckBox::indicator:checked {
                background-color: #4F46E5;
                border-color:     #4F46E5;
                image: url(none);
            }
            QCheckBox::indicator:hover {
                border-color: #4F46E5;
            }
        """)

        # Forgot password link
        forgot = ClickableLabel("Forgot Password?")

        h.addWidget(self.remember_checkbox)
        h.addStretch()
        h.addWidget(forgot)
        return row

    #  Sign In Button 
    def _build_sign_in_button(self):
        btn = QPushButton("Sign In")
        btn.setFixedHeight(48)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #4F46E5;
                color: #ffffff;
                font-size: 15px;
                font-weight: 600;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #4338CA;
            }
            QPushButton:pressed {
                background-color: #3730A3;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #818CF8;
            }
        """)
        btn.clicked.connect(self._handle_sign_in)
        return btn

    #  Shadow Effect 
    def _make_shadow(self):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        return shadow

    #  Sign In Handler 
    def _handle_sign_in(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username:
            self._highlight_error(self.username_input)
            return

        if not password:
            self._highlight_error(self.password_input)
            return

        remember = self.remember_checkbox.isChecked()
        print(f"Username : {username}")
        print(f"Password : {'*' * len(password)}")
        print(f"Remember : {remember}")

    #  Error Highlight 
    def _highlight_error(self, widget: QLineEdit):
        widget.setStyleSheet(widget.styleSheet() + """
            QLineEdit {
                border: 2px solid #EF4444;
                background-color: #FEF2F2;
            }
        """)
        widget.setPlaceholderText("Information required !")

        # Reset after user starts typing
        widget.textChanged.connect(lambda: self._reset_input(widget))

    def _reset_input(self, widget: QLineEdit):
        widget.setStyleSheet("""
            QLineEdit {
                background-color: #F9FAFB;
                border: 1.5px solid #D1D5DB;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 14px;
                color: #111827;
            }
            QLineEdit:focus {
                border: 2px solid #4F46E5;
                background-color: #ffffff;
            }
        """)

    #  ESC to close 
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)


#  Entry Point 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LoginWindow()
    sys.exit(app.exec())
