import sqlite3
import json
import os
from pathlib import Path

class LocalAuthStorage:
    """Manages local storage of authentication data including face encodings and QR codes."""
    
    def __init__(self, db_name="auth_data.db"):
        self.db_path = db_name
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the local authentication database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for face recognition data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                face_encoding TEXT NOT NULL,
                registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Table for QR code authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qr_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                qr_code TEXT UNIQUE NOT NULL,
                registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Table for authentication attempts (for logging)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                auth_method TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ============ Face Recognition Methods ============
    
    def register_face(self, username, face_encoding):
        """Register a user's face encoding."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert face encoding to JSON string
            encoding_json = json.dumps(face_encoding.tolist() if hasattr(face_encoding, 'tolist') else face_encoding)
            
            cursor.execute("""
                INSERT OR REPLACE INTO face_users (username, face_encoding)
                VALUES (?, ?)
            """, (username, encoding_json))
            
            conn.commit()
            conn.close()
            return True, "Face registered successfully"
        except Exception as e:
            return False, f"Error registering face: {str(e)}"
    
    def get_face_encoding(self, username):
        """Get a user's face encoding."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT face_encoding FROM face_users 
                WHERE username = ? AND is_active = 1
            """, (username,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                import numpy as np
                return True, np.array(json.loads(result[0]))
            return False, "Face encoding not found"
        except Exception as e:
            return False, f"Error retrieving face: {str(e)}"
    
    def get_all_face_encodings(self):
        """Get all registered face encodings for comparison."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, face_encoding FROM face_users 
                WHERE is_active = 1
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            import numpy as np
            encodings_dict = {}
            for username, encoding_json in results:
                encodings_dict[username] = np.array(json.loads(encoding_json))
            
            return encodings_dict
        except Exception as e:
            print(f"Error retrieving all faces: {str(e)}")
            return {}
    
    def delete_face(self, username):
        """Delete a user's face registration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM face_users WHERE username = ?
            """, (username,))
            
            conn.commit()
            conn.close()
            return True, "Face registration deleted"
        except Exception as e:
            return False, f"Error deleting face: {str(e)}"
    
    # ============ QR Code Methods ============
    
    def register_qr(self, username, qr_code):
        """Register a user's QR code."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO qr_users (username, qr_code)
                VALUES (?, ?)
            """, (username, qr_code))
            
            conn.commit()
            conn.close()
            return True, "QR code registered successfully"
        except Exception as e:
            return False, f"Error registering QR: {str(e)}"
    
    def verify_qr(self, qr_code):
        """Verify a QR code and return the associated username."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username FROM qr_users 
                WHERE qr_code = ? AND is_active = 1
            """, (qr_code,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return True, result[0]
            return False, "QR code not found"
        except Exception as e:
            return False, f"Error verifying QR: {str(e)}"
    
    def delete_qr(self, username):
        """Delete a user's QR registration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM qr_users WHERE username = ?
            """, (username,))
            
            conn.commit()
            conn.close()
            return True, "QR registration deleted"
        except Exception as e:
            return False, f"Error deleting QR: {str(e)}"
    
    # ============ Authentication Logging ============
    
    def log_auth_attempt(self, username, auth_method, success):
        """Log an authentication attempt."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO auth_attempts (username, auth_method, success)
                VALUES (?, ?, ?)
            """, (username, auth_method, success))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging auth attempt: {str(e)}")
    
    def get_auth_history(self, username=None, limit=100):
        """Get authentication history."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if username:
                cursor.execute("""
                    SELECT * FROM auth_attempts 
                    WHERE username = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (username, limit))
            else:
                cursor.execute("""
                    SELECT * FROM auth_attempts 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
            
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"Error retrieving auth history: {str(e)}")
            return []
