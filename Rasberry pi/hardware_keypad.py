"""
Hardware Keypad Module for Raspberry Pi Door Lock
Uses 4x4 matrix keypad connected to GPIO pins
"""

from gpiozero import DigitalOutputDevice, Button
from time import sleep, time

class HardwareKeypad:
    def __init__(self):
        # Configure rows, columns, and keypad layout using BCM numbering
        self.rows_pins = [5, 6, 13, 19]  # BCM numbers corresponding to pins 29, 31, 33, 35
        self.cols_pins = [12, 16, 20, 21]  # BCM numbers corresponding to pins 32, 36, 38, 40
        self.keys = ["1", "2", "3", "A",
                    "4", "5", "6", "B",
                    "7", "8", "9", "C",
                    "*", "0", "#", "D"]
        
        # Initialize row pins as DigitalOutputDevice
        self.rows = [DigitalOutputDevice(pin) for pin in self.rows_pins]
        # Initialize column pins as Buttons
        self.cols = [Button(pin, pull_up=False) for pin in self.cols_pins]

    def read_keypad(self):
        """
        Read the currently pressed keys on the keypad.
        :return: A list of pressed keys.
        """
        pressed_keys = []
        # Set all rows to off initially
        for row in self.rows:
            row.off()
            
        # Scan each row and column to identify pressed keys
        for i, row in enumerate(self.rows):
            row.on()  # Enable the current row
            sleep(0.01)  # Small delay to stabilize signals
            for j, col in enumerate(self.cols):
                if col.is_pressed:  # Check if the column button is pressed
                    # Calculate the key index based on row and column
                    index = i * len(self.cols) + j
                    pressed_keys.append(self.keys[index])
            row.off()  # Disable the current row
        return pressed_keys

    def get_single_key_press(self, timeout=30):
        """
        Wait for a single key press and return it
        :param timeout: Maximum time in seconds to wait for input
        :return: The pressed key or None if timeout
        """
        last_key_pressed = []
        start_time = time()
        
        while (time() - start_time) < timeout:
            pressed_keys = self.read_keypad()
            
            if pressed_keys and pressed_keys != last_key_pressed:
                # Return the first key pressed
                return pressed_keys[0]
                    
            last_key_pressed = pressed_keys
            sleep(0.1)
                
        return None  # Timeout

    def check_pin_input(self):
        """Check for PIN input from hardware keypad (non-blocking with debouncing)"""
        if not hasattr(self, 'last_key_pressed'):
            self.last_key_pressed = []
        if not hasattr(self, 'last_key_time'):
            self.last_key_time = 0
            
        current_time = time()
        pressed_keys = self.read_keypad()
        
        # Debouncing: only process if different key or enough time has passed
        if pressed_keys and (pressed_keys != self.last_key_pressed or (current_time - self.last_key_time) > 0.3):
            key = pressed_keys[0]  # Take first key if multiple pressed
            self.last_key_pressed = pressed_keys
            self.last_key_time = current_time
            return key
        elif not pressed_keys:
            # Reset when no keys are pressed
            self.last_key_pressed = []
            
        return None

    def get_pin_input(self, max_length=4, timeout=60):
        """
        Get PIN input from keypad with visual feedback
        :param max_length: Maximum PIN length
        :param timeout: Maximum time in seconds to wait for complete input
        :return: Tuple (pin_string, success) where success indicates if PIN was completed
        """
        entered_keys = []
        last_key_pressed = []
        start_time = time()
        
        print("Enter PIN on hardware keypad. Press # to submit, * to clear.")
        
        while (time() - start_time) < timeout:
            pressed_keys = self.read_keypad()
            
            if pressed_keys and pressed_keys != last_key_pressed:
                for key in pressed_keys:
                    if key == "#":  # Submit PIN
                        pin_string = "".join(entered_keys)
                        print(f"PIN submitted: {'*' * len(pin_string)}")
                        return pin_string, True
                    elif key == "*":  # Clear entry
                        entered_keys = []
                        print("PIN cleared")
                    elif key.isdigit() and len(entered_keys) < max_length:
                        entered_keys.append(key)
                        print(f"PIN: {'*' * len(entered_keys)}")
                
                last_key_pressed = pressed_keys
            sleep(0.1)
                
        print("PIN input timeout")
        return "".join(entered_keys), False

    def cleanup(self):
        """Release resources used by GPIO pins"""
        try:
            for row in self.rows:
                row.close()
            for col in self.cols:
                col.close()
        except Exception as e:
            print(f"Warning: Error during keypad cleanup: {e}")

    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()


class PasswordInput(HardwareKeypad):
    """Legacy class for backward compatibility"""
    
    def __init__(self, password=None):
        super().__init__()
        # Define the secret password
        self.password = password if password else ["1", "2", "3", "4"]

    def get_password(self, max_attempts=3, timeout=30):
        """
        Wait for user to enter password via keypad
        :param max_attempts: Maximum number of attempts allowed
        :param timeout: Maximum time in seconds to wait for input
        :return: True if correct password entered, False otherwise
        """
        entered_keys = []
        last_key_pressed = []
        attempt_count = 0
        start_time = time()
        
        try:
            print("Enter password on keypad. Press # to submit, * to clear.")
            
            while attempt_count < max_attempts and (time() - start_time) < timeout:
                pressed_keys = self.read_keypad()
                
                if pressed_keys and pressed_keys != last_key_pressed:
                    for key in pressed_keys:
                        if key == "#":  # Submit password
                            if entered_keys == self.password:
                                print("Correct Password!")
                                return True
                            else:
                                print("Wrong Password!")
                                attempt_count += 1
                                entered_keys = []  # Clear for next attempt
                                return False
                        elif key == "*":  # Clear entry
                            entered_keys = []
                            print("Entry cleared")
                        else:
                            entered_keys.append(key)
                            print(f"Entered: {'*' * len(entered_keys)}")
                    
                    last_key_pressed = pressed_keys
                sleep(0.1)
                
            print("Password entry failed")
            return False
        finally:
            # Always clean up GPIO resources when done
            self.cleanup()