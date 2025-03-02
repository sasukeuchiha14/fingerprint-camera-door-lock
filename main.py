import time
import sys
import traceback

# Try to import the required modules
try:
    from fingerprint.main import FingerprintSensor
    from face_recognition_folder.return_face import FaceRecognition
    face_recognition = FaceRecognition()
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Initialize variables
tries = 0
authorized = False

# Add cleanup function to ensure camera is released
def cleanup_camera():
    import cv2
    try:
        cv2.destroyAllWindows()
        # Allow a short time for resources to be released
        time.sleep(0.5)
    except:
        pass

# Main loop
while not authorized:
    tries += 1
    print(f"Attempt #{tries}")
    
    # Attempt face recognition
    
    # Make sure any previous camera instances are cleaned up
    cleanup_camera()
    try:
        # To find face, we need to call the find_face method
        name = face_recognition.find_face()
        # Release camera resources
        face_recognition.release_camera()
        
        if name == "Unknown":
            print("Try again...")
            authorized = False
        else:
            print(f"Welcome, {name}!")
            authorized = True
    except Exception as e:
        print(f"Error during face recognition: {e}")
        print(traceback.format_exc())
        break
    
    # Add delays to avoid conflicts with fingerprint sensor and to close camera resources
    time.sleep(1.0)
    cleanup_camera()
    time.sleep(1.0)
    
    
    # Attempt fingerprint recognition
    
    print("Place finger on sensor...")
    # To find fingerprint, we need to call the find_fingerprint method
    fingerprint_check = FingerprintSensor().find_fingerprint()
    
    if fingerprint_check:
        print("Fingerprint recognized.")
        authorized = True
    else:
        print("Fingerprint not recognized. Try again...")
        authorized = False
    
    # If tries exceed 3, exit
    if tries == 3 and not authorized:
        print("Too many tries. Exiting...")
        break

# Final check
if not authorized:
    print("Access denied after 3 attempts.")
    cleanup_camera()
    sys.exit(1)
else:
    print("Access granted after {tries} attempts.")
    cleanup_camera()
    sys.exit(0)