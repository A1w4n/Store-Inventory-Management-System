import cv2
import face_recognition
import numpy as np
from .local_auth_storage import LocalAuthStorage

class FaceRecognitionAuth:
    """Handles face recognition for authentication."""
    
    def __init__(self, storage=None):
        self.storage = storage or LocalAuthStorage()
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.known_face_encodings = {}
        self.known_face_names = {}
        self._load_known_faces()
    
    def _load_known_faces(self):
        """Load all registered face encodings from storage."""
        self.known_face_encodings = self.storage.get_all_face_encodings()
    
    def capture_and_register_face(self, username, num_samples=5):
        """
        Capture face samples from camera and register them.
        Returns (success, message)
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False, "Cannot access camera"
        
        face_samples = []
        samples_captured = 0
        
        print(f"Registering face for {username}. Please look at the camera...")
        
        while samples_captured < num_samples:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return False, "Failed to read from camera"
            
            # Resize for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            if face_encodings:
                face_samples.extend(face_encodings)
                samples_captured = len(face_samples)
                
                # Draw rectangle on original frame
                for (top, right, bottom, left) in face_locations:
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
            cv2.putText(frame, f"Samples: {samples_captured}/{num_samples}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Face Registration", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return False, "Registration cancelled"
        
        cap.release()
        cv2.destroyAllWindows()
        
        if face_samples:
            # Average the encodings for better accuracy
            avg_encoding = np.mean(face_samples, axis=0)
            success, msg = self.storage.register_face(username, avg_encoding)
            if success:
                self.known_face_encodings[username] = avg_encoding
            return success, msg
        
        return False, "No face detected during registration"
    
    def authenticate_user_face(self, timeout_seconds=10):
        """
        Authenticate user by face recognition.
        Returns (success, username, message)
        """
        if not self.known_face_encodings:
            return False, None, "No users registered for face recognition"
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False, None, "Cannot access camera"
        
        start_time = cv2.getTickCount()
        process_every_n_frames = 5
        frame_count = 0
        
        print("Scanning face for authentication. Press 'q' to cancel...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return False, None, "Failed to read from camera"
            
            frame_count += 1
            
            # Process every nth frame for performance
            if frame_count % process_every_n_frames == 0:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                face_names = []
                face_distances = []
                
                for face_encoding in face_encodings:
                    # Compare with all known faces
                    distances = {}
                    for username, known_encoding in self.known_face_encodings.items():
                        distance = face_recognition.face_distance([known_encoding], face_encoding)
                        distances[username] = distance[0]
                    
                    if distances:
                        best_match = min(distances, key=distances.get)
                        if distances[best_match] < 0.6:  # Threshold for face match
                            face_names.append(best_match)
                            face_distances.append(distances[best_match])
                        else:
                            face_names.append("Unknown")
                            face_distances.append(distances[best_match])
                
                # If we found a match, authenticate
                if face_names and face_names[0] != "Unknown":
                    cap.release()
                    cv2.destroyAllWindows()
                    username = face_names[0]
                    self.storage.log_auth_attempt(username, "face_recognition", True)
                    return True, username, f"Welcome, {username}!"
            
            # Draw rectangles around faces
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(frame, name, (left, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            cv2.imshow("Face Authentication", frame)
            
            # Check timeout
            elapsed_seconds = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
            if elapsed_seconds > timeout_seconds:
                cap.release()
                cv2.destroyAllWindows()
                self.storage.log_auth_attempt("unknown", "face_recognition", False)
                return False, None, "Face authentication timeout"
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return False, None, "Face authentication cancelled"
        
        cap.release()
        cv2.destroyAllWindows()
        return False, None, "Face not recognized"
