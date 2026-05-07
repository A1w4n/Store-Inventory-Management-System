# auth_service.py — AuthService accepts an existing InventoryDatabase instance

class AuthService:
    def __init__(self, db):
        """Initialize AuthService with an existing database instance."""
        self.db = db
        self.current_user = None
        self._ensure_default_user()

    def _ensure_default_user(self):
        """Create default admin user if it doesn't exist."""
        user = self.db.get_user_by_username("admin")
        if not user:
            self.db.add_user("admin", "password123", "admin@inventory.com")

    def validate_login(self, username, password):
        """Validate user login against database."""
        if not username or not password:
            return False, "Fields cannot be empty."

        user = self.db.get_user_by_username(username)

        if not user:
            return False, "Invalid username or password."

        if not user['is_active']:
            return False, "User account is inactive."

        if self.db.verify_password(user['password_hash'], password):
            self.current_user = user
            return True, "Login successful!"

        return False, "Invalid username or password."

    def reset_password_request(self, email):
        """Handle password reset request."""
        print(f"Backend: Sending reset link to {email}")
        return True

    def get_current_user(self):
        """Get currently logged-in user."""
        return self.current_user

    def logout(self):
        """Logout current user."""
        self.current_user = None