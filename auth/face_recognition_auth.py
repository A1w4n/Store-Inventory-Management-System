import time
import cv2
import numpy as np
from .local_auth_storage import LocalAuthStorage


class FaceRecognitionAuth:
    """Handles face registration and real-time face authentication using OpenCV.

    Uses OpenCV's Haar cascades for face detection and basic image comparison.
    Face encodings are stored locally via LocalAuthStorage.
    """

    def __init__(self, storage=None, tolerance=0.7):
        self.storage = storage or LocalAuthStorage()
        # Similarity threshold — higher = stricter (0.0 to 1.0)
        # 0.7 is a reasonable default; increase to 0.8 to be more strict
        self.tolerance = tolerance

        # Load Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_face_encoding(self, image):
        """Return face encoding from image, or None if no face found."""
        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            if len(faces) > 0:
                # Use the largest face found
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest_face

                # Extract face region with some padding
                padding = int(0.1 * max(w, h))
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(image.shape[1], x + w + padding)
                y2 = min(image.shape[0], y + h + padding)

                face_roi = image[y1:y2, x1:x2]
                if face_roi.size == 0:
                    return None

                # Resize to fixed size for consistent encoding
                face_resized = cv2.resize(face_roi, (100, 100))

                # Convert to grayscale and flatten
                face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
                encoding = face_gray.flatten().astype(np.float32)
                encoding = encoding / 255.0  # Normalize to 0-1

                return encoding

        except Exception as e:
            print(f"Face encoding error: {e}")
        return None

    def _cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        return dot_product / (norm_a * norm_b) if norm_a != 0 and norm_b != 0 else 0

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def _capture_face_samples(self, sample_count=5, timeout_seconds=30):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False, None, "Cannot access camera"

        samples = []
        start_time = time.time()

        while len(samples) < sample_count:
            if time.time() - start_time > timeout_seconds:
                break

            ret, frame = cap.read()
            if not ret:
                continue

            encoding = self._get_face_encoding(frame)
            if encoding is not None:
                samples.append(encoding)

            cv2.putText(
                frame,
                f"Look at camera: {len(samples)}/{sample_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            cv2.imshow("Face Registration", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()

        if not samples:
            return False, None, "No face detected during registration"

        # Average encodings for a robust reference vector
        avg_encoding = np.mean(samples, axis=0)
        return True, avg_encoding, f"Captured {len(samples)} facial samples"

    def capture_and_register_face(self, username, sample_count=5, timeout_seconds=30):
        """Capture face samples and register the user in local storage."""
        if not username:
            return False, "Username is required"

        success, encoding, message = self._capture_face_samples(sample_count, timeout_seconds)
        if not success:
            return False, message

        stored_success, stored_message = self.storage.register_face(username, encoding)
        return stored_success, stored_message

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate_user_face(self, timeout_seconds=15):
        """Authenticate a user by scanning their face from the camera."""
        encodings_dict = self.storage.get_all_face_encodings()
        if not encodings_dict:
            return False, None, "No registered faces found"

        user_names = list(encodings_dict.keys())
        known_encodings = [np.array(enc) for enc in encodings_dict.values()]

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False, None, "Cannot access camera"

        start_time = time.time()
        best_match = None
        best_similarity = -1.0

        while time.time() - start_time < timeout_seconds:
            ret, frame = cap.read()
            if not ret:
                continue

            encoding = self._get_face_encoding(frame)

            if encoding is not None:
                similarities = [
                    self._cosine_similarity(encoding, known) for known in known_encodings
                ]
                max_index = int(np.argmax(similarities))
                max_sim = similarities[max_index]

                if max_sim > best_similarity:
                    best_similarity = max_sim
                    best_match = user_names[max_index]

                if best_similarity >= self.tolerance:
                    cap.release()
                    cv2.destroyAllWindows()
                    self.storage.log_auth_attempt(best_match, "face_recognition", True)
                    return True, best_match, f"Welcome, {best_match}!"

            cv2.putText(
                frame,
                "Authenticating...",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            cv2.imshow("Face Authentication", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()
        self.storage.log_auth_attempt(best_match or "unknown", "face_recognition", False)

        if best_match:
            return False, None, f"Face not recognized with enough confidence (best similarity: {best_similarity:.2f})"
        return False, None, "Face authentication timed out"

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def set_tolerance(self, tolerance):
        """Adjust the similarity threshold (higher = stricter match required)."""
        self.tolerance = tolerance
