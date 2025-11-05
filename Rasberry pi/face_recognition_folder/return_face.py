"""
Face Recognition Module
Handles real-time face detection and recognition using trained models
"""

import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import os


class FaceRecognition:
    """Main face recognition class for door lock system"""
    
    def __init__(self, encodings_path="encodings.pickle", authorized_names=None):
        """
        Initialize face recognition system
        
        Args:
            encodings_path: Path to pickled face encodings
            authorized_names: List of authorized user names (None = all users)
        """
        self.encodings_path = encodings_path
        self.authorized_names = authorized_names
        self.picam2 = None
        self.known_face_encodings = []
        self.known_face_names = []
        self.cv_scaler = 10  # Image downscale factor for faster processing
        
        # Load encodings
        self._load_encodings()
    
    def _load_encodings(self):
        """Load pre-trained face encodings from file"""
        try:
            # Get absolute path
            if not os.path.isabs(self.encodings_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                self.encodings_path = os.path.join(script_dir, self.encodings_path)
            
            print(f"[INFO] Loading encodings from: {self.encodings_path}")
            
            with open(self.encodings_path, "rb") as f:
                data = pickle.loads(f.read())
            
            self.known_face_encodings = data["encodings"]
            self.known_face_names = data["names"]
            
            print(f"[INFO] Loaded {len(self.known_face_encodings)} face encodings")
            
        except FileNotFoundError:
            print(f"[WARNING] Encodings file not found: {self.encodings_path}")
            print("[INFO] Attempting to download latest model from cloud...")
            
            # Try to download from cloud
            if self._download_encodings_from_cloud():
                print("[INFO] Successfully downloaded encodings from cloud")
                # Try loading again
                try:
                    with open(self.encodings_path, "rb") as f:
                        data = pickle.loads(f.read())
                    
                    self.known_face_encodings = data["encodings"]
                    self.known_face_names = data["names"]
                    
                    print(f"[INFO] Loaded {len(self.known_face_encodings)} face encodings from cloud")
                except Exception as e:
                    print(f"[ERROR] Failed to load downloaded encodings: {e}")
                    print("[WARNING] Face recognition will return 'Unknown' for all faces")
            else:
                print("[WARNING] Failed to download encodings from cloud")
                print("[WARNING] Face recognition will return 'Unknown' for all faces")
                
        except Exception as e:
            print(f"[ERROR] Failed to load encodings: {e}")
            print("[WARNING] Face recognition will return 'Unknown' for all faces")
    
    def _download_encodings_from_cloud(self):
        """Download latest trained model from cloud backend"""
        try:
            import requests
            import os
            
            # Get backend URL from environment or use default
            backend_url = os.getenv("BACKEND_URL", "http://localhost:7000/doorlock")
            model_url = f"{backend_url}/models/trained_model.pkl"
            
            print(f"[INFO] Downloading model from: {model_url}")
            
            response = requests.get(model_url, timeout=30)
            
            if response.status_code == 200:
                # Save the downloaded model to the encodings path
                with open(self.encodings_path, "wb") as f:
                    f.write(response.content)
                
                print(f"[INFO] Model downloaded successfully to: {self.encodings_path}")
                return True
            else:
                print(f"[ERROR] Failed to download model. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Exception while downloading model: {e}")
            return False
    
    def _init_camera(self):
        """Initialize camera"""
        if self.picam2 is None:
            # Release any existing camera instances
            self._release_camera()
            time.sleep(0.5)
            
            try:
                self.picam2 = Picamera2()
                self.picam2.configure(
                    self.picam2.create_preview_configuration(
                        main={"format": 'XRGB8888', "size": (1920, 1080)}
                    )
                )
                self.picam2.start()
                time.sleep(1)  # Camera warm-up
                print("[INFO] Camera initialized")
            except Exception as e:
                print(f"[ERROR] Camera initialization failed: {e}")
                raise
    
    def _release_camera(self):
        """Release camera resources"""
        try:
            if self.picam2:
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None
            cv2.destroyAllWindows()
            time.sleep(0.5)
        except Exception as e:
            print(f"[INFO] Error releasing camera: {e}")
    
    def _process_frame(self, frame):
        """
        Process a single frame to detect and recognize faces
        
        Args:
            frame: BGR image from camera
            
        Returns:
            Recognized name or "Unknown"
        """
        # Convert BGR to RGB (no downscaling for better accuracy)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if not face_locations:
            return "Unknown"
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(
            rgb_frame, 
            face_locations, 
            model='large'
        )
        
        # Compare with known faces
        for face_encoding in face_encodings:
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, 
                face_encoding
            )
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                
                # Accept match if distance is below threshold
                if face_distances[best_match_index] < 0.6:
                    name = self.known_face_names[best_match_index]
                    
                    # Check if authorized (if list provided)
                    if self.authorized_names is None or name in self.authorized_names:
                        return name
        
        return "Unknown"
    
    def find_face(self, timeout=15, show_preview=False):
        """
        Detect and recognize faces with timeout
        
        Args:
            timeout: Maximum time to wait for face recognition (seconds)
            show_preview: Show camera preview window (useful for debugging)
            
        Returns:
            Recognized name or "Unknown"
        """
        try:
            self._init_camera()
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Capture frame
                frame = self.picam2.capture_array()
                
                # Process and recognize
                name = self._process_frame(frame)
                
                # Show preview if requested
                if show_preview:
                    cv2.putText(
                        frame, 
                        f"Scanning... {name}", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        1, 
                        (0, 255, 0), 
                        2
                    )
                    cv2.imshow("Face Recognition", frame)
                    
                    # Allow early exit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Return immediately if recognized
                if name != "Unknown":
                    print(f"[INFO] Recognized: {name}")
                    return name
            
            print("[INFO] No face recognized within timeout")
            return "Unknown"
            
        except Exception as e:
            print(f"[ERROR] Face recognition failed: {e}")
            return "Unknown"
            
        finally:
            self._release_camera()
    
    def release_camera(self):
        """Public method to release camera resources"""
        self._release_camera()
    
    def __del__(self):
        """Cleanup on deletion"""
        self._release_camera()


# Backward compatibility class (deprecated)
class FaceRecognizer(FaceRecognition):
    """Legacy class name - use FaceRecognition instead"""
    
    def recognize_face(self, timeout=15):
        """Legacy method - use find_face() instead"""
        return self.find_face(timeout=timeout, show_preview=True)


if __name__ == "__main__":
    # Example usage
    recognizer = FaceRecognition()
    name = recognizer.find_face(show_preview=True)
    print(f"Detected: {name}")

