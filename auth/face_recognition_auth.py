import time
import cv2
import numpy as np
import face_recognition
from .local_auth_storage import LocalAuthStorage


class FaceRecognitionAuth:
    """Handles face registration and real-time face authentication."""
    def __init__(self, storage=None, tolerance=0.55):
        self.storage = storage or LocalAuthStorage()
        self.tolerance = tolerance

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

            rgb_frame = frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_frame)
            if face_locations:
                encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if encodings:
                    samples.append(encodings[0])

            cv2.putText(frame, f"Look at camera: {len(samples)}/{sample_count}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow("Face Registration", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        if len(samples) < 1:
            return False, None, "No face detected during registration"

        return True, np.mean(samples, axis=0), f"Captured {len(samples)} facial samples"

    def capture_and_register_face(self, username, sample_count=5, timeout_seconds=30):
        """Capture face samples and register the user."""
        if not username:
            return False, "Username is required"

        success, encoding, message = self._capture_face_samples(sample_count, timeout_seconds)
        if not success:
            return False, message

        stored_success, stored_message = self.storage.register_face(username, encoding)
        return stored_success, stored_message

    def authenticate_user_face(self, timeout_seconds=15):
        """Authenticate a user by scanning their face from the camera."""
        encodings_dict = self.storage.get_all_face_encodings()
        if not encodings_dict:
            return False, None, "No registered faces found"

        user_names = list(encodings_dict.keys())
        known_encodings = list(encodings_dict.values())

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False, None, "Cannot access camera"

        start_time = time.time()
        best_match = None
        best_distance = float('inf')

        while time.time() - start_time < timeout_seconds:
            ret, frame = cap.read()
            if not ret:
                continue

            rgb_frame = frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_frame)
            if face_locations:
                encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if encodings:
                    distance = face_recognition.face_distance(known_encodings, encodings[0])
                    min_index = int(np.argmin(distance))
                    if distance[min_index] < best_distance:
                        best_distance = float(distance[min_index])
                        best_match = user_names[min_index]

                    if best_distance <= self.tolerance:
                        cap.release()
                        cv2.destroyAllWindows()
                        self.storage.log_auth_attempt(best_match, "face_recognition", True)
                        return True, best_match, f"Welcome, {best_match}!"

            cv2.putText(frame, "Authenticating...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow("Face Authentication", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        self.storage.log_auth_attempt(best_match or "unknown", "face_recognition", False)
        if best_match:
            return False, None, "Face not recognized with enough confidence"
        return False, None, "Face authentication timed out"

    def set_tolerance(self, tolerance):
        """Adjust the face distance tolerance for matching."""
        self.tolerance = tolerance
