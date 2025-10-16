from gpiozero import AngularServo
from time import sleep

class DoorLock:
    def __init__(self, pin=18, min_pulse_width=0.0005, max_pulse_width=0.0024):
        self.servo = AngularServo(
            pin, 
            min_pulse_width=min_pulse_width, 
            max_pulse_width=max_pulse_width, 
            initial_angle=90  # Locked position
        )
    
    def unlock(self):
        """Rotate servo to unlock the door"""
        try:
            print("Unlocking door...")
            self.servo.angle = -90
            sleep(5)  # Keep door unlocked for 5 seconds
            return True
        except Exception as e:
            print(f"Error unlocking door: {e}")
            return False
            
    def lock(self):
        """Rotate servo back to lock the door"""
        try:
            print("Locking door...")
            self.servo.angle = 90
            sleep(1)  # Brief pause to ensure lock is engaged
            return True
        except Exception as e:
            print(f"Error locking door: {e}")
            return False
            
    def operate_lock(self):
        """Complete unlock and lock cycle"""
        try:
            self.unlock()
            self.lock()
            return True
        except Exception as e:
            print(f"Error operating lock: {e}")
            self.servo.angle = 90  # Try to return to locked position
            return False
        finally:
            self.servo.close()
            print("Lock operation complete")
            
if __name__ == "__main__":
    try:
        lock = DoorLock()
        lock.operate_lock()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure we clean up GPIO resources
        try:
            lock.servo.close()
        except:
            pass