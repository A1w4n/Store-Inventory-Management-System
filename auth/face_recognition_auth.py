import time
import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from .local_auth_storage import LocalAuthStorage


class FaceRecognitionAuth:
    """Handles face registration and real-time face authentication using InsightFace.

    InsightFace uses ONNX Runtime — no TensorFlow, no dlib, deploys cleanly on Render.
    Embeddings are 512-d ArcFace vectors stored locally via LocalAuthStorage.
    """

    def __init__(self, storage=None, tolerance=0.55):
        self.storage = storage or LocalAuthStorage()
        # Cosine similarity threshold — higher = stricter (0.0 to 1.0)
        # 0.55 is a reasonable default; increase to 0.65 to be more strict
        self.tolerance = tolerance
        self._app = None  # lazy-loaded on first use

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_app(self):
        """Lazy-load the InsightFace model (downloads on first run, cached after)."""
        if self._app is None:
            self._app = FaceAnalysis(
                name="buffalo_sc",   # lightweight model: detector + ArcFace recognizer
                providers=["CPUExecutionProvider"],
            )
            self._app.prepare(ctx_id=0, det_size=(640, 640))
        return self._app

    def _get_embedding(self, bgr_frame):
        """Return a 512-d ArcFace embedding from a BGR frame, or None if no face found."""
        try:
            app = self._get_app()
            faces = app.get(bgr_frame)
            if faces:
                return faces[0].normed_embedding  # already L2-normalised
        except Exception:
            pass
        return None

    def _cosine_similarity(self, a, b):
        """Cosine similarity (1.0 = identical, 0.0 = unrelated)."""
        return float(np.dot(a, b))  # both vectors are already normalised

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

            embedding = self._get_embedding(frame)
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

        # Average embeddings and re-normalise for a robust reference vector
        avg = np.mean(samples, axis=0)
        avg = avg / (np.linalg.norm(avg) + 1e-10)
        return True, avg, f"Captured {len(samples)} facial samples"

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

            embedding = self._get_embedding(frame)

            if embedding is not None:
                similarities = [
                    self._cosine_similarity(embedding, known) for known in known_encodings
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
            return False, None, "Face not recognized with enough confidence"
        return False, None, "Face authentication timed out"

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def set_tolerance(self, tolerance):
        """Adjust the cosine similarity threshold (higher = stricter match required)."""
        self.tolerance = tolerance
