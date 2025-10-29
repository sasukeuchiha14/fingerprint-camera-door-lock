import time
import serial
import adafruit_fingerprint

class FingerprintSensor:
    def __init__(self):
        """Initialize fingerprint sensor with auto port detection"""
        self.finger = None
        self.uart = None
        self._initialize_sensor()
    
    def _initialize_sensor(self):
        """Initialize the fingerprint sensor by finding the working port"""
        try:
            # Validate and find working port
            working_port = self.find_working_port()
            if not working_port:
                raise Exception("No valid fingerprint sensor port found")
            
            self.uart = serial.Serial(working_port, baudrate=57600, timeout=1)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(self.uart)
            print(f"Fingerprint sensor initialized on {working_port}")
        except Exception as e:
            print(f"Error initializing fingerprint sensor: {e}")
            raise
    
    @staticmethod
    def validate_serial_port(port, baudrate=57600, timeout=1):
        """Validate if the serial port returns correct fingerprint sensor response
        
        Args:
            port: Serial port path (e.g., "/dev/ttyAMA0")
            baudrate: Communication speed (default: 57600)
            timeout: Read timeout in seconds (default: 1)
            
        Returns:
            bool: True if valid response received, False otherwise
        """
        try:
            ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            # Send handshake command to fingerprint sensor
            ser.write(b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x03\x01\x00\x05')
            response = ser.read(12)
            ser.close()
            
            # Check if response has correct header and structure
            # Valid response should start with b'\xef\x01\xff\xff\xff\xff'
            if len(response) == 12 and response[:6] == b'\xef\x01\xff\xff\xff\xff':
                print(f"✓ Valid response from {port}: {response.hex()}")
                return True
            else:
                print(f"✗ Invalid response from {port}: {response.hex() if response else 'No response'}")
                return False
        except Exception as e:
            print(f"✗ Error on {port}: {e}")
            return False
    
    @staticmethod
    def find_working_port(ports=["/dev/ttyAMA0", "/dev/ttyAMA10", "/dev/serial0", "/dev/serial1"]):
        """Find the first working serial port for the fingerprint sensor
        
        Args:
            ports: List of serial ports to test
            
        Returns:
            str: Path to working serial port, or None if none found
        """
        print("Searching for fingerprint sensor...")
        for port in ports:
            print(f"Trying {port}...")
            if FingerprintSensor.validate_serial_port(port):
                print(f"Found working port: {port}")
                return port
        print("No working fingerprint sensor found!")
        return None
    
    def find_fingerprint(self):
        """Check if a fingerprint matches any stored template
        Returns:
            bool: True if a match is found, False otherwise
        """
        if not self.finger:
            print("Fingerprint sensor not initialized")
            return False
        
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
    
    def enroll_fingerprint(self, location=None):
        """Enroll a new fingerprint
        
        Args:
            location: Storage location (1-127). If None, finds next available slot.
            
        Returns:
            bool: True if enrollment successful, False otherwise
        """
        if not self.finger:
            print("Fingerprint sensor not initialized")
            return False
        
        if location is None:
            # Find next available slot
            location = self._find_next_slot()
            if location is None:
                print("No available fingerprint slots!")
                return False
        
        print(f"Enrolling fingerprint at location {location}")
        print("Place finger on sensor...")
        
        # First image
        while self.finger.get_image() != adafruit_fingerprint.OK:
            pass
        
        print("Image captured. Processing...")
        if self.finger.image_2_tz(1) != adafruit_fingerprint.OK:
            print("Failed to process first image")
            return False
        
        print("Remove finger")
        time.sleep(1)
        
        while self.finger.get_image() != adafruit_fingerprint.NOFINGER:
            pass
        
        print("Place same finger again...")
        
        # Second image
        while self.finger.get_image() != adafruit_fingerprint.OK:
            pass
        
        print("Image captured. Processing...")
        if self.finger.image_2_tz(2) != adafruit_fingerprint.OK:
            print("Failed to process second image")
            return False
        
        # Create model
        print("Creating fingerprint model...")
        if self.finger.create_model() != adafruit_fingerprint.OK:
            print("Failed to create fingerprint model")
            return False
        
        # Store model
        print(f"Storing fingerprint model at location {location}...")
        if self.finger.store_model(location) != adafruit_fingerprint.OK:
            print("Failed to store fingerprint model")
            return False
        
        print(f"✓ Fingerprint enrolled successfully at location {location}")
        self.finger.finger_id = location
        return True
    
    def _find_next_slot(self):
        """Find the next available fingerprint storage slot
        
        Returns:
            int: Next available slot number (1-127), or None if all slots are full
        """
        if not self.finger:
            return 1
        
        # Read template count
        if self.finger.read_templates() != adafruit_fingerprint.OK:
            print("Failed to read templates")
            return 1  # Default to slot 1
        
        # Check each slot from 1 to 127
        for location in range(1, 128):
            if self.finger.load_model(location) != adafruit_fingerprint.OK:
                # Slot is empty
                return location
        
        return None  # All slots full