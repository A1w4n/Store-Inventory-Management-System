import cv2
import qrcode
import uuid
from pyzbar.pyzbar import decode
from .local_auth_storage import LocalAuthStorage

class QRCodeAuth:
    """Handles QR code generation and scanning for authentication."""
    
    def __init__(self, storage=None):
        self.storage = storage or LocalAuthStorage()
    
    def generate_qr_code(self, username, output_path=None):
        """
        Generate a unique QR code for a user.
        Returns (success, qr_code_data, message)
        """
        try:
            # Generate unique QR code data
            qr_data = f"inventory_auth:{username}:{uuid.uuid4()}"
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save if path provided
            if output_path is None:
                output_path = f"qr_codes/{username}_qr.png"
            
            import os
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            img.save(output_path)
            
            # Store in local database
            success, msg = self.storage.register_qr(username, qr_data)
            
            if success:
                return True, qr_data, f"QR code generated and saved to {output_path}"
            else:
                return False, None, msg
        
        except Exception as e:
            return False, None, f"Error generating QR code: {str(e)}"
    
    def scan_qr_code(self, timeout_seconds=15):
        """
        Scan QR code from camera.
        Returns (success, qr_data, message)
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False, None, "Cannot access camera"
        
        print("Scanning QR code. Please show the QR code to the camera. Press 'q' to cancel...")
        
        start_time = cv2.getTickCount()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return False, None, "Failed to read from camera"
            
            # Detect QR codes
            decoded_objects = decode(frame)
            
            if decoded_objects:
                qr_data = decoded_objects[0].data.decode('utf-8')
                cap.release()
                cv2.destroyAllWindows()
                return True, qr_data, "QR code scanned successfully"
            
            # Display frame
            cv2.imshow("QR Code Scanner", frame)
            
            # Check timeout
            elapsed_seconds = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
            if elapsed_seconds > timeout_seconds:
                cap.release()
                cv2.destroyAllWindows()
                return False, None, "QR scanning timeout"
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return False, None, "QR scanning cancelled"
        
        cap.release()
        cv2.destroyAllWindows()
        return False, None, "No QR code detected"
    
    def authenticate_user_qr(self, timeout_seconds=15):
        """
        Authenticate user by scanning QR code.
        Returns (success, username, message)
        """
        success, qr_data, msg = self.scan_qr_code(timeout_seconds)
        
        if not success:
            self.storage.log_auth_attempt("unknown", "qr_code", False)
            return False, None, msg
        
        # Verify QR code
        success, username = self.storage.verify_qr(qr_data)
        
        if success:
            self.storage.log_auth_attempt(username, "qr_code", True)
            return True, username, f"Welcome, {username}!"
        else:
            self.storage.log_auth_attempt("unknown", "qr_code", False)
            return False, None, "QR code not registered"
    
    def regenerate_qr(self, username):
        """Regenerate a new QR code for a user."""
        try:
            # Delete old QR
            self.storage.delete_qr(username)
            
            # Generate new QR
            return self.generate_qr_code(username)
        except Exception as e:
            return False, None, f"Error regenerating QR: {str(e)}"
