import time
import serial
import adafruit_fingerprint

class FingerprintSensor:
    def find_fingerprint(self):
        """Initialize fingerprint sensor with the specified serial connection parameters"""
        try:
            uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
        except Exception as e:
            print(f"Error initializing fingerprint sensor: {e}")
            raise
        
        """Check if a fingerprint matches any stored template
        Returns:
            bool: True if a match is found, False otherwise
        """
        print("Waiting for finger...")
        
        # Get fingerprint image
        while self.finger.get_image() != adafruit_fingerprint.OK:
            pass
        
        # Convert image to template
        if self.finger.image_2_tz(1) != adafruit_fingerprint.OK:
            print("Failed to convert image to template")
            return False
        
        # Search for matching fingerprint
        if self.finger.finger_search() != adafruit_fingerprint.OK:
            print("No matching fingerprint found")
            return False
            
        # Match found!
        print(f"Fingerprint matched with ID #{self.finger.finger_id}, confidence: {self.finger.confidence}")
        return True