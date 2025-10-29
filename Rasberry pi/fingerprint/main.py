import time
import serial
import adafruit_fingerprint

class FingerprintSensor:
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
        """Initialize fingerprint sensor with the specified serial connection parameters"""
        try:
            # Validate and find working port
            working_port = self.find_working_port()
            if not working_port:
                raise Exception("No valid fingerprint sensor port found")
            
            uart = serial.Serial(working_port, baudrate=57600, timeout=1)
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