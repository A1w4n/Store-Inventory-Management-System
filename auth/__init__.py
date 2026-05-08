"""
Authentication module for Inventory Management System.

This module provides:
- Local authentication data storage (face encodings, QR codes)
- Face recognition authentication (requires opencv-python)
- QR code authentication (requires pyzbar)
"""

from .local_auth_storage import LocalAuthStorage

# Lazy import face recognition and QR code to handle missing dependencies
def __getattr__(name):
    if name == 'FaceRecognitionAuth':
        try:
            from .face_recognition_auth import FaceRecognitionAuth
            return FaceRecognitionAuth
        except ImportError as e:
            raise ImportError(f"FaceRecognitionAuth requires cv2. Install with: pip install opencv-python") from e
    elif name == 'QRCodeAuth':
        try:
            from .qr_code_auth import QRCodeAuth
            return QRCodeAuth
        except ImportError as e:
            raise ImportError(f"QRCodeAuth requires qrcode and pyzbar. Install with: pip install qrcode pyzbar") from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'LocalAuthStorage',
    'FaceRecognitionAuth',
    'QRCodeAuth',
]
