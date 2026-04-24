class AuthService:
    def __init__(self):
        # In a real app, this would connect to a database or API
        self._mock_user = "admin"
        self._mock_pass = "password123"

    def validate_login(self, username, password):
        if not username or not password:
            return False, "Fields cannot be empty."

        if username == self._mock_user and password == self._mock_pass:
            return True, "Login successful!"
        
        return False, "Invalid username or password."

    def reset_password_request(self, email):
        print(f"Backend: Sending reset link to {email}")
        return True