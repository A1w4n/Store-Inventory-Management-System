"""
Authentication module for Inventory Management System.

This module provides:
- Local authentication data storage (QR codes, face encodings)
- QR code authentication (requires pyzbar)
- Face recognition authentication (requires face_recognition)
"""

from .local_auth_storage import LocalAuthStorage

# Lazy imports to handle missing dependencies
def __getattr__(name):
    if name == 'QRCodeAuth':
        try:
            from .qr_code_auth import QRCodeAuth
            return QRCodeAuth
        except ImportError as e:
            raise ImportError(f"QRCodeAuth requires qrcode and pyzbar. Install with: pip install qrcode pyzbar") from e
    if name == 'FaceRecognitionAuth':
        try:
            from .face_recognition_auth import FaceRecognitionAuth
            return FaceRecognitionAuth
        except ImportError as e:
            raise ImportError(f"FaceRecognitionAuth requires face_recognition and opencv-python. Install with: pip install face-recognition opencv-python") from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'LocalAuthStorage',
    'QRCodeAuth',
    'FaceRecognitionAuth',
]
