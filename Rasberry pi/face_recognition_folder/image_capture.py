"""
Image Capture Module
Captures face images for training the face recognition model
"""

import cv2
import os
from datetime import datetime
from picamera2 import Picamera2
import time


class ImageCapture:
    """Handles capturing images for face recognition training"""
    
    def __init__(self, dataset_folder="dataset"):
        self.dataset_folder = dataset_folder
        self.picam2 = None
        
    def _init_camera(self):
        """Initialize camera if not already initialized"""
        if self.picam2 is None:
            try:
                self.picam2 = Picamera2()
                self.picam2.configure(
                    self.picam2.create_preview_configuration(
                        main={"format": 'XRGB8888', "size": (640, 480)}
                    )
                )
                self.picam2.start()
                time.sleep(2)  # Camera warm-up
            except Exception as e:
                print(f"[ERROR] Camera initialization failed: {e}")
                raise
    
    def _release_camera(self):
        """Release camera resources"""
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None
            except:
                pass
        cv2.destroyAllWindows()
    
    def create_person_folder(self, person_name):
        """Create folder for person's images"""
        if not os.path.exists(self.dataset_folder):
            os.makedirs(self.dataset_folder)
        
        person_folder = os.path.join(self.dataset_folder, person_name)
        if not os.path.exists(person_folder):
            os.makedirs(person_folder)
        return person_folder
    
    def capture_single_image(self, person_name, image_number=None):
        """Capture a single image and save it"""
        try:
            self._init_camera()
            folder = self.create_person_folder(person_name)
            
            # Capture frame
            frame = self.picam2.capture_array()
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if image_number is not None:
                filename = f"{person_name}_{image_number}_{timestamp}.jpg"
            else:
                filename = f"{person_name}_{timestamp}.jpg"
            
            filepath = os.path.join(folder, filename)
            
            # Save image
            cv2.imwrite(filepath, frame)
            print(f"[INFO] Image saved: {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"[ERROR] Failed to capture image: {e}")
            return None
        finally:
            self._release_camera()
    
    def capture_multiple_images(self, person_name, count=5):
        """Capture multiple images with GUI feedback"""
        try:
            self._init_camera()
            folder = self.create_person_folder(person_name)
            
            captured_files = []
            
            for i in range(count):
                print(f"[INFO] Capturing image {i+1}/{count}...")
                time.sleep(1)  # Brief pause between captures
                
                # Capture frame
                frame = self.picam2.capture_array()
                
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{person_name}_{i+1}_{timestamp}.jpg"
                filepath = os.path.join(folder, filename)
                
                # Save image
                cv2.imwrite(filepath, frame)
                captured_files.append(filepath)
                print(f"[INFO] Image {i+1} saved: {filepath}")
            
            return captured_files
            
        except Exception as e:
            print(f"[ERROR] Failed to capture images: {e}")
            return []
        finally:
            self._release_camera()
    
    def capture_interactive(self, person_name):
        """Interactive image capture with live preview (for manual use)"""
        try:
            self._init_camera()
            folder = self.create_person_folder(person_name)
            
            photo_count = 0
            print(f"[INFO] Taking photos for {person_name}. Press SPACE to capture, 'q' to quit.")
            
            while True:
                # Capture and display frame
                frame = self.picam2.capture_array()
                cv2.imshow('Capture', frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord(' '):  # Space key
                    photo_count += 1
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{person_name}_{timestamp}.jpg"
                    filepath = os.path.join(folder, filename)
                    cv2.imwrite(filepath, frame)
                    print(f"[INFO] Photo {photo_count} saved: {filepath}")
                
                elif key == ord('q'):  # Q key
                    break
            
            print(f"[INFO] Capture completed. {photo_count} photos saved for {person_name}.")
            return photo_count
            
        finally:
            self._release_camera()
    
    def __del__(self):
        """Cleanup on deletion"""
        self._release_camera()


# For backward compatibility and standalone use
def capture_photos(person_name):
    """Legacy function for standalone use"""
    capturer = ImageCapture()
    return capturer.capture_interactive(person_name)


if __name__ == "__main__":
    # Example usage
    PERSON_NAME = "hardik"
    capture_photos(PERSON_NAME)
