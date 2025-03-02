import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle

class FaceRecognizer:
    def __init__(self, encodings_path="encodings.pickle", authorized_names=None):
        # Load pre-trained face encodings
        print("[INFO] loading encodings...")
        import os
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Create absolute path to encodings file
        encodings_path = os.path.join(script_dir, encodings_path)
        print(f"[INFO] looking for encodings at: {encodings_path}")
        with open(encodings_path, "rb") as f:
            data = pickle.loads(f.read())
        self.known_face_encodings = data["encodings"]
        self.known_face_names = data["names"]

        # Set authorized names
        self.authorized_names = authorized_names or ["hardik", "kartik"]

        # Make sure any running camera instances are fully released
        self._release_all_cameras()
        
        # Initialize the camera
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1920, 1080)}))
        self.picam2.start()

        # Scale factor for image processing (higher = faster but less accurate)
        self.cv_scaler = 10
        
    def _release_all_cameras(self):
        """Force release all camera resources"""
        import cv2
        # Close all OpenCV windows
        cv2.destroyAllWindows()
        
        # Try to release any existing Picamera2 instances
        import subprocess
        import time
        
        # Small delay to ensure resources are ready to be released
        time.sleep(0.5)
        
        try:
            # Find any running libcamera processes and terminate them
            subprocess.run(['pkill', '-f', 'libcamera'], stderr=subprocess.DEVNULL)
            time.sleep(1.0)  # Give time for the processes to terminate
        except Exception as e:
            print(f"[INFO] Error while releasing cameras: {e}")

    def process_frame(self, frame):
        # Resize the frame for better performance
        resized_frame = cv2.resize(frame, (0, 0), fx=(1/self.cv_scaler), fy=(1/self.cv_scaler))
        
        # Convert BGR to RGB
        rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces and get encodings
        face_locations = face_recognition.face_locations(rgb_resized_frame)
        
        # Skip encoding if no faces found
        if not face_locations:
            return "Unknown"
            
        face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')
        
        for face_encoding in face_encodings:
            # Compare with known faces
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                # Only accept matches below a certain distance threshold
                if face_distances[best_match_index] < 0.6:
                    name = self.known_face_names[best_match_index]
                    if name in self.authorized_names:
                        return name
        
        return "Unknown"

    def recognize_face(self, timeout=15):
        """Recognize faces with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Capture and process frame
            frame = self.picam2.capture_array()
            name = self.process_frame(frame)
            
            # Display the camera feed
            cv2.putText(frame, f"Scanning... {name}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Camera Feed", frame)
            
            # Check if recognized
            if name != "Unknown":
                return name
                
            # Check for keyboard interrupt
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        return "Unknown"  # Return Unknown if timeout occurs
        
    def __del__(self):
        """Release resources"""
        try:
            if hasattr(self, 'picam2'):
                self.picam2.stop()
                self.picam2.close()
                del self.picam2
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"[INFO] Error during cleanup: {e}")

class FaceRecognition:
    def __init__(self, authorized_names=None):
        self.authorized_names = authorized_names
        self.face_recognizer = None
    
    def find_face(self):
        """Public method to detect faces"""
        # Create a new face recognizer instance for each recognition attempt
        self.face_recognizer = FaceRecognizer(authorized_names=self.authorized_names)
        try:
            return self.face_recognizer.recognize_face()
        finally:
            # Ensure camera is properly released
            if hasattr(self.face_recognizer, 'picam2'):
                try:
                    self.face_recognizer.picam2.stop()
                    self.face_recognizer.picam2.close()
                except:
                    pass
            cv2.destroyAllWindows()
            
    def release_camera(self):
        """Release camera resources"""
        if hasattr(self, 'face_recognizer') and hasattr(self.face_recognizer, 'picam2'):
            self.face_recognizer.picam2.stop()
            self.face_recognizer.picam2.close()
            del self.face_recognizer.picam2
        cv2.destroyAllWindows()
    
    def __del__(self):
        """Cleanup resources"""
        # Ensure camera is properly released
        if hasattr(self, 'face_recognizer') and hasattr(self.face_recognizer, 'picam2'):
            try:
                self.face_recognizer.picam2.stop()
            except:
                pass
        cv2.destroyAllWindows()

# Example usage
if __name__ == "__main__":
    recognizer = FaceRecognition()
    name = recognizer.find_face()
    print(f"Detected: {name}")
