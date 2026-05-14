import time
import cv2
import numpy as np
from deepface import DeepFace
from .local_auth_storage import LocalAuthStorage

# DeepFace model to use — "Facenet" is fast and accurate; no dlib required
MODEL_NAME = "Facenet"
DETECTOR = "opencv"


class FaceRecognitionAuth:
    """Handles face registration and real-time face authentication using DeepFace."""

    def __init__(self, storage=None, tolerance=0.55):
        self.storage = storage or LocalAuthStorage()
        # tolerance maps to a distance threshold (lower = stricter)
        # Facenet cosine distance: 0.40 is roughly equivalent to face_recognition's 0.55
        self.tolerance = tolerance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_embedding(self, rgb_frame):
        """Return a 128-d face embedding from an RGB frame, or None if no face found."""
        try:
            result = DeepFace.represent(
                img_path=rgb_frame,
                model_name=MODEL_NAME,
                detector_backend=DETECTOR,
                enforce_detection=True,
            )
            # result is a list of dicts; take the first detected face
            if result:
                return np.array(result[0]["embedding"])
        except Exception:
            pass
        return None

    def _cosine_distance(self, a, b):
        """Cosine distance between two embedding vectors (0 = identical, 1 = orthogonal)."""
        a = a / (np.linalg.norm(a) + 1e-10)
        b = b / (np.linalg.norm(b) + 1e-10)
        return float(1.0 - np.dot(a, b))

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

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            embedding = self._get_embedding(rgb_frame)
            if embedding is not None:
                samples.append(embedding)

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

        # Average the captured embeddings for a robust reference vector
        avg_embedding = np.mean(samples, axis=0)
        return True, avg_embedding, f"Captured {len(samples)} facial samples"

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
        best_distance = float("inf")

        # Scale tolerance: face_recognition uses Euclidean ~0.55;
        # map to cosine distance by dividing by ~2.5 (empirical approximation)
        cosine_threshold = self.tolerance / 2.5

        while time.time() - start_time < timeout_seconds:
            ret, frame = cap.read()
            if not ret:
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            embedding = self._get_embedding(rgb_frame)

            if embedding is not None:
                distances = [
                    self._cosine_distance(embedding, known) for known in known_encodings
                ]
                min_index = int(np.argmin(distances))
                min_dist = distances[min_index]

                if min_dist < best_distance:
                    best_distance = min_dist
                    best_match = user_names[min_index]

                if best_distance <= cosine_threshold:
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
            return False, None, "Face not recognized with enough confidence"
        return False, None, "Face authentication timed out"

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def set_tolerance(self, tolerance):
        """Adjust the face distance tolerance for matching."""
        self.tolerance = tolerance
