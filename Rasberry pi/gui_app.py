"""
Raspberry Pi Door Lock GUI Application
Built with Pygame for touchscreen interface
"""

import pygame
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import requests
from datetime import datetime
import time
import random
import string

# Load environment variables
load_dotenv()

# Try to import the required modules
try:
    from fingerprint.main import FingerprintSensor
    from face_recognition_folder.return_face import FaceRecognition
    from face_recognition_folder.image_capture import ImageCapture
    from servo.rotate import DoorLock
except ImportError as e:
    print(f"Warning: Some hardware modules not available: {e}")
    FingerprintSensor = None
    FaceRecognition = None
    ImageCapture = None
    DoorLock = None


# =========================================
# CONFIGURATION
# =========================================

BACKEND_URL = os.getenv("BACKEND_URL", "https://oracle-apis.hardikgarg.me/doorlock")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "YourDoorLockBot")

# Screen settings
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
FPS = 30

# Colors
COLOR_BG = (240, 240, 245)
COLOR_PRIMARY = (41, 128, 185)
COLOR_SUCCESS = (46, 204, 113)
COLOR_ERROR = (231, 76, 60)
COLOR_WARNING = (241, 196, 15)
COLOR_TEXT = (44, 62, 80)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (189, 195, 199)
COLOR_DARK_GRAY = (127, 140, 141)


# =========================================
# PYGAME SETUP
# =========================================

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Door Lock Control")
clock = pygame.time.Clock()

# Fonts
font_title = pygame.font.Font(None, 48)
font_large = pygame.font.Font(None, 36)
font_medium = pygame.font.Font(None, 28)
font_small = pygame.font.Font(None, 22)


# =========================================
# UTILITY FUNCTIONS
# =========================================

def draw_text(text, font, color, x, y, center=False):
    """Draw text on screen"""
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    screen.blit(text_surface, text_rect)
    return text_rect


def draw_button(text, x, y, width, height, color, text_color=COLOR_WHITE, font=font_medium):
    """Draw a button and return its rect"""
    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, COLOR_DARK_GRAY, rect, 2, border_radius=10)
    
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    
    return rect


def draw_input_field(x, y, width, height, text, active=False):
    """Draw an input field"""
    color = COLOR_PRIMARY if active else COLOR_GRAY
    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, COLOR_WHITE, rect, border_radius=5)
    pygame.draw.rect(screen, color, rect, 3, border_radius=5)
    
    if text:
        draw_text(text, font_medium, COLOR_TEXT, x + 10, y + 10)
    
    # Draw blinking cursor if field is active
    if active:
        cursor_visible = (pygame.time.get_ticks() // 500) % 2  # Blink every 500ms
        if cursor_visible:
            text_width = font_medium.size(text)[0] if text else 0
            cursor_x = x + 10 + text_width
            cursor_y = y + 10
            pygame.draw.line(screen, COLOR_TEXT, (cursor_x, cursor_y), (cursor_x, cursor_y + 25), 2)
    
    return rect


def generate_temp_pin():
    """Generate a 4-digit temporary PIN"""
    return ''.join(random.choices(string.digits, k=4))


def show_message(message, message_type="info", duration=2000):
    """Show a temporary message overlay"""
    colors = {
        "info": COLOR_PRIMARY,
        "success": COLOR_SUCCESS,
        "error": COLOR_ERROR,
        "warning": COLOR_WARNING
    }
    
    color = colors.get(message_type, COLOR_PRIMARY)
    
    # Semi-transparent overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # Message box
    box_width, box_height = 600, 200
    box_x = (SCREEN_WIDTH - box_width) // 2
    box_y = (SCREEN_HEIGHT - box_height) // 2
    
    pygame.draw.rect(screen, color, (box_x, box_y, box_width, box_height), border_radius=15)
    pygame.draw.rect(screen, COLOR_WHITE, (box_x + 10, box_y + 10, box_width - 20, box_height - 20), border_radius=10)
    
    # Wrap text if too long
    words = message.split(' ')
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + word + " "
        if font_large.size(test_line)[0] < box_width - 40:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word + " "
    if current_line:
        lines.append(current_line)
    
    # Draw text lines
    y_offset = box_y + box_height // 2 - (len(lines) * 20)
    for line in lines:
        draw_text(line.strip(), font_large, COLOR_TEXT, SCREEN_WIDTH // 2, y_offset, center=True)
        y_offset += 40
    
    pygame.display.flip()
    pygame.time.wait(duration)


# =========================================
# API FUNCTIONS
# =========================================

def create_user_api(name, email, phone, pin_code, fingerprint_id):
    """Create a new user via API"""
    try:
        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "pin_code": pin_code,
            "fingerprint_id": fingerprint_id
        }
        
        print(f"[INFO] Creating user with data: {data}")
        response = requests.post(f"{BACKEND_URL}/api/add-user", json=data, timeout=10)
        
        print(f"[INFO] User creation response status: {response.status_code}")
        print(f"[INFO] User creation response text: {response.text}")
        
        if response.status_code in [200, 201]:  # Accept both 200 OK and 201 Created
            result = response.json()
            if 'user' in result:
                return True, result['user']  # Return the user object directly
            else:
                return True, result  # Fallback if structure is different
        else:
            error_msg = response.json().get('error', f'HTTP {response.status_code}')
            print(f"[ERROR] User creation failed: {error_msg}")
            return False, error_msg
    except Exception as e:
        print(f"[ERROR] User creation exception: {e}")
        return False, str(e)


def verify_temp_pin_and_link_telegram(temp_pin, telegram_chat_id):
    """Verify temporary PIN and link Telegram chat ID to user"""
    try:
        data = {
            "temp_pin": temp_pin,
            "telegram_chat_id": telegram_chat_id
        }
        
        response = requests.post(f"{BACKEND_URL}/api/link-telegram", json=data, timeout=10)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json().get('error', 'Invalid PIN or already used')
    except Exception as e:
        return False, str(e)


def verify_user_for_unlock(pin_code, fingerprint_id, face_name=None):
    """Verify user credentials for door unlock"""
    try:
        data = {
            "pin_code": pin_code,
            "fingerprint_id": fingerprint_id,
            "face_match": face_name
        }
        
        response = requests.post(f"{BACKEND_URL}/api/verify-user", json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('success', False), result.get('user')
        
        return False, None
    except Exception as e:
        print(f"Verification failed: {e}")
        return False, None


def log_access(user_id=None, access_type="success", method="gui", notes=None):
    """Log access attempt"""
    try:
        data = {
            "user_id": user_id,
            "access_type": access_type,
            "authentication_method": method,
            "notes": notes
        }
        
        requests.post(f"{BACKEND_URL}/api/log-access", json=data, timeout=5)
    except:
        pass


def upload_face_image(user_id, image_path):
    """Upload face image to backend"""
    try:
        # Check if image file exists
        if not os.path.exists(image_path):
            print(f"[ERROR] Image file does not exist: {image_path}")
            return False
        
        file_size = os.path.getsize(image_path)
        print(f"[INFO] Uploading image: {image_path} ({file_size} bytes)")
        print(f"[INFO] User ID: {user_id}")
        print(f"[INFO] Backend URL: {BACKEND_URL}/api/upload-face-image")
        
        with open(image_path, 'rb') as f:
            files = {'image': f}  # Fixed: backend expects 'image', not 'file'
            data = {'user_id': user_id}
            
            print(f"[INFO] Sending POST request...")
            response = requests.post(
                f"{BACKEND_URL}/api/upload-face-image",
                files=files,
                data=data,
                timeout=30
            )
            
            print(f"[INFO] Upload response status: {response.status_code}")
            print(f"[INFO] Upload response headers: {dict(response.headers)}")
            print(f"[INFO] Upload response text: {response.text}")
            
            if response.status_code == 200 or response.status_code == 201:
                print(f"[SUCCESS] Image uploaded successfully: {image_path}")
                return True
            else:
                print(f"[ERROR] Upload failed with status {response.status_code}")
                print(f"[ERROR] Response body: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print(f"[ERROR] Upload timeout for {image_path}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Connection error uploading {image_path}")
        return False
    except Exception as e:
        print(f"[ERROR] Upload failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def trigger_model_retrain():
    """Trigger face recognition model retraining"""
    try:
        response = requests.post(f"{BACKEND_URL}/api/retrain-model", timeout=60)
        return response.status_code == 200
    except Exception as e:
        print(f"Retrain failed: {e}")
        return False


# =========================================
# SCREEN CLASSES
# =========================================

class MainMenu:
    """Main menu screen"""
    
    def __init__(self):
        self.buttons = {}
    
    def draw(self):
        screen.fill(COLOR_BG)
        
        # Title
        draw_text("Door Lock System", font_title, COLOR_PRIMARY, SCREEN_WIDTH // 2, 60, center=True)
        
        # Buttons
        button_width = 350
        button_height = 80
        button_x = (SCREEN_WIDTH - button_width) // 2
        start_y = 150
        spacing = 100
        
        self.buttons['unlock'] = draw_button(
            "Unlock Door", button_x, start_y, button_width, button_height, COLOR_SUCCESS
        )
        
        self.buttons['create_user'] = draw_button(
            "Create New User", button_x, start_y + spacing, button_width, button_height, COLOR_PRIMARY
        )
        
        self.buttons['link_telegram'] = draw_button(
            "Link Telegram", button_x, start_y + spacing * 2, button_width, button_height, COLOR_WARNING
        )
        
        # Footer
        draw_text("Touch to select", font_small, COLOR_DARK_GRAY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30, center=True)
    
    def handle_click(self, pos):
        for action, rect in self.buttons.items():
            if rect.collidepoint(pos):
                return action
        return None


class UnlockDoor:
    """Door unlock screen"""
    
    def __init__(self):
        self.pin = ""
        self.step = "pin"  # pin -> face -> fingerprint -> unlock
        self.fingerprint_id = None
        self.face_name = None
        self.message = "Enter 4-digit PIN"
        self.buttons = {}
    
    def draw(self):
        screen.fill(COLOR_BG)
        
        # Title
        draw_text("Unlock Door", font_title, COLOR_PRIMARY, SCREEN_WIDTH // 2, 40, center=True)
        
        # Status message
        draw_text(self.message, font_medium, COLOR_TEXT, SCREEN_WIDTH // 2, 100, center=True)
        
        if self.step == "pin":
            # PIN input
            pin_display = "•" * len(self.pin)
            draw_text(pin_display, font_large, COLOR_TEXT, SCREEN_WIDTH // 2, 200, center=True)
            
            # Number pad
            self.draw_numpad()
        
        elif self.step in ["face", "fingerprint", "unlock"]:
            # Show progress
            progress_text = {
                "face": "Position your face in front of camera...",
                "fingerprint": "Place finger on sensor...",
                "unlock": "Unlocking door..."
            }
            draw_text(progress_text[self.step], font_large, COLOR_PRIMARY, SCREEN_WIDTH // 2, 240, center=True)
        
        # Back button
        self.buttons['back'] = draw_button("Back", 20, SCREEN_HEIGHT - 70, 150, 50, COLOR_GRAY, COLOR_TEXT)
    
    def draw_numpad(self):
        """Draw numeric keypad"""
        button_size = 80
        spacing = 20
        start_x = (SCREEN_WIDTH - (button_size * 3 + spacing * 2)) // 2
        start_y = 250
        
        # Number buttons
        for i in range(9):
            row = i // 3
            col = i % 3
            x = start_x + col * (button_size + spacing)
            y = start_y + row * (button_size + spacing)
            
            self.buttons[f'num_{i+1}'] = draw_button(
                str(i + 1), x, y, button_size, button_size, COLOR_PRIMARY
            )
        
        # Bottom row: Clear, 0, Enter
        self.buttons['clear'] = draw_button(
            "CLR", start_x, start_y + 3 * (button_size + spacing), button_size, button_size, COLOR_ERROR
        )
        
        self.buttons['num_0'] = draw_button(
            "0", start_x + button_size + spacing, start_y + 3 * (button_size + spacing), 
            button_size, button_size, COLOR_PRIMARY
        )
        
        self.buttons['enter'] = draw_button(
            "OK", start_x + 2 * (button_size + spacing), start_y + 3 * (button_size + spacing), 
            button_size, button_size, COLOR_SUCCESS
        )
    
    def handle_click(self, pos):
        for action, rect in self.buttons.items():
            if rect.collidepoint(pos):
                if action == 'back':
                    return 'back'
                elif action.startswith('num_'):
                    num = action.split('_')[1]
                    if len(self.pin) < 4:
                        self.pin += num
                    # Don't return, just continue to update display
                elif action == 'clear':
                    self.pin = ""
                    # Don't return, just continue to update display
                elif action == 'enter' and len(self.pin) == 4:
                    return 'verify_pin'
        return None
    
    def verify_and_unlock(self):
        """Perform authentication and unlock"""
        # Step 1: Face recognition
        self.step = "face"
        self.message = "Scanning face..."
        
        if FaceRecognition:
            try:
                face_rec = FaceRecognition()
                self.face_name = face_rec.find_face()
                face_rec.release_camera()
                
                if self.face_name == "Unknown":
                    return False, "Face not recognized"
            except Exception as e:
                return False, f"Face error: {str(e)}"
        else:
            self.face_name = "test_user"  # Demo mode
        
        # Step 2: Fingerprint
        self.step = "fingerprint"
        self.message = "Scanning fingerprint..."
        
        if FingerprintSensor:
            try:
                fp_sensor = FingerprintSensor()
                if fp_sensor.find_fingerprint():
                    self.fingerprint_id = fp_sensor.finger.finger_id
                else:
                    return False, "Fingerprint not recognized"
            except Exception as e:
                return False, f"Fingerprint error: {str(e)}"
        else:
            self.fingerprint_id = 1  # Demo mode
        
        # Step 3: Verify with backend
        success, user = verify_user_for_unlock(self.pin, self.fingerprint_id, self.face_name)
        
        if not success:
            log_access(access_type="failed_combined", method="gui", notes="Authentication failed")
            return False, "Authentication failed"
        
        # Step 4: Unlock door
        self.step = "unlock"
        self.message = "Access granted! Unlocking..."
        
        if DoorLock:
            try:
                DoorLock().operate_lock()
            except Exception as e:
                print(f"Lock error: {e}")
        
        log_access(user_id=user.get('user_id'), access_type="success", method="gui")
        
        return True, f"Welcome, {user.get('name', 'User')}!"


class CreateUser:
    """Create new user screen"""
    
    def __init__(self):
        self._step = "details"  # details -> fingerprint -> face -> complete
        self.name = ""
        self.email = ""
        self.phone = ""
        self.pin = ""
        self.fingerprint_id = None
        self.user_id = None
        self.face_images_captured = 0
        self.captured_image_paths = []  # Store paths of captured images
        self.active_field = "name"
        self.buttons = {}
        self.camera = None
        self.camera_surface = None
    
    @property
    def step(self):
        return self._step
    
    @step.setter
    def step(self, value):
        if self._step != value:
            print(f"[DEBUG] STEP CHANGED: '{self._step}' -> '{value}'")
            import traceback
            traceback.print_stack()
        self._step = value
    
    def draw(self):
        screen.fill(COLOR_BG)
        
        # Clear buttons from previous screen
        self.buttons = {}
        
        # Title
        draw_text("Create New User", font_title, COLOR_PRIMARY, SCREEN_WIDTH // 2, 40, center=True)
        
        if self.step == "details":
            self.draw_details_form()
        elif self.step == "fingerprint":
            self.draw_fingerprint_enroll()
        elif self.step == "face":
            self.draw_face_capture()
        elif self.step == "complete":
            self.draw_completion()
        
        # Back button (added after specific screen buttons)
        self.buttons['back'] = draw_button("Back", 20, SCREEN_HEIGHT - 70, 150, 50, COLOR_GRAY, COLOR_TEXT)
    
    def draw_details_form(self):
        """Draw user details form"""
        y = 100
        spacing = 70
        
        # Name
        draw_text("Name:", font_medium, COLOR_TEXT, 50, y)
        draw_input_field(200, y - 5, 550, 50, self.name, self.active_field == "name")
        self.buttons['name'] = pygame.Rect(200, y - 5, 550, 50)
        
        # Email
        y += spacing
        draw_text("Email:", font_medium, COLOR_TEXT, 50, y)
        draw_input_field(200, y - 5, 550, 50, self.email, self.active_field == "email")
        self.buttons['email'] = pygame.Rect(200, y - 5, 550, 50)
        
        # Phone
        y += spacing
        draw_text("Phone:", font_medium, COLOR_TEXT, 50, y)
        draw_input_field(200, y - 5, 550, 50, self.phone, self.active_field == "phone")
        self.buttons['phone'] = pygame.Rect(200, y - 5, 550, 50)
        
        # PIN
        y += spacing
        draw_text("PIN (4 digits):", font_medium, COLOR_TEXT, 50, y)
        pin_display = "•" * len(self.pin)
        draw_input_field(200, y - 5, 550, 50, pin_display, self.active_field == "pin")
        self.buttons['pin'] = pygame.Rect(200, y - 5, 550, 50)
        
        # Next button
        y += spacing + 20
        self.buttons['next'] = draw_button("Next", SCREEN_WIDTH // 2 - 100, y, 200, 60, COLOR_SUCCESS)
        
        # Hint for keyboard input
        draw_text("Click field to select, then type with keyboard", font_small, COLOR_DARK_GRAY, 
                 SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30, center=True)
    
    def draw_fingerprint_enroll(self):
        """Draw fingerprint enrollment screen"""
        draw_text("Fingerprint Enrollment", font_large, COLOR_TEXT, SCREEN_WIDTH // 2, 120, center=True)
        draw_text("Place finger on sensor multiple times", font_medium, COLOR_TEXT, SCREEN_WIDTH // 2, 180, center=True)
        
        # Start enrollment button
        self.buttons['enroll_fp'] = draw_button(
            "Start Enrollment", SCREEN_WIDTH // 2 - 150, 250, 300, 70, COLOR_PRIMARY
        )
    
    def draw_face_capture(self):
        """Draw face capture screen with live camera feed"""
        draw_text("Face Capture", font_large, COLOR_TEXT, SCREEN_WIDTH // 2, 30, center=True)
        draw_text(f"Images captured: {self.face_images_captured}/5", font_medium, COLOR_TEXT, 
                 SCREEN_WIDTH // 2, 70, center=True)
        
        # Initialize camera if not already done
        if self.camera is None and ImageCapture:
            try:
                import cv2
                from picamera2 import Picamera2
                self.camera = Picamera2()
                config = self.camera.create_preview_configuration(main={"size": (640, 480)})
                self.camera.configure(config)
                self.camera.start()
                time.sleep(0.5)  # Let camera warm up
            except Exception as e:
                print(f"Camera init error: {e}")
                self.camera = None
        
        # Show live camera feed
        if self.camera:
            try:
                import cv2
                import numpy as np
                
                # Capture frame
                frame = self.camera.capture_array()
                
                # Convert from RGB to BGR for OpenCV
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Resize to fit screen (keeping aspect ratio)
                display_height = 280
                aspect_ratio = frame.shape[1] / frame.shape[0]
                display_width = int(display_height * aspect_ratio)
                frame_resized = cv2.resize(frame, (display_width, display_height))
                
                # Convert to pygame surface
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                frame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2)))
                
                # Display on screen
                x_pos = (SCREEN_WIDTH - display_width) // 2
                screen.blit(frame_surface, (x_pos, 110))
                
            except Exception as e:
                print(f"Camera feed error: {e}")
                draw_text("Camera feed unavailable", font_medium, COLOR_ERROR, 
                         SCREEN_WIDTH // 2, 200, center=True)
        else:
            # No camera - show placeholder
            pygame.draw.rect(screen, COLOR_DARK_GRAY, (160, 110, 480, 280), border_radius=10)
            draw_text("Camera Preview", font_medium, COLOR_WHITE, SCREEN_WIDTH // 2, 250, center=True)
        
        # Capture button
        self.buttons['capture_face'] = draw_button(
            "Capture Image", SCREEN_WIDTH // 2 - 150, 400, 300, 60, COLOR_PRIMARY
        )
        
        if self.face_images_captured >= 5:
            # Complete button
            self.buttons['complete_face'] = draw_button(
                "Complete & Train Model", SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT - 120, 360, 60, COLOR_SUCCESS
            )
    
    def draw_completion(self):
        """Draw completion screen"""
        draw_text("✓ User Created Successfully!", font_large, COLOR_SUCCESS, 
                 SCREEN_WIDTH // 2, 200, center=True)
        draw_text(f"Name: {self.name}", font_medium, COLOR_TEXT, SCREEN_WIDTH // 2, 260, center=True)
        draw_text(f"Fingerprint ID: {self.fingerprint_id}", font_medium, COLOR_TEXT, 
                 SCREEN_WIDTH // 2, 300, center=True)
        
        self.buttons['done'] = draw_button(
            "Done", SCREEN_WIDTH // 2 - 100, 360, 200, 60, COLOR_PRIMARY
        )
    
    def handle_click(self, pos):
        print(f"[DEBUG] handle_click called with pos: {pos}")
        for action, rect in self.buttons.items():
            if rect.collidepoint(pos):
                print(f"[DEBUG] Button clicked: action='{action}', step='{self.step}'")
                if action == 'back':
                    return 'back'
                elif action == 'done':
                    return 'back'
                elif action in ['name', 'email', 'phone', 'pin']:
                    self.active_field = action
                elif action == 'next':
                    if self.step == "details" and self.validate_details():
                        self.step = "fingerprint"
                    else:
                        return 'invalid_details'
                elif action == 'enroll_fp':
                    return 'enroll_fingerprint'
                elif action == 'capture_face':
                    return 'capture_face'
                elif action == 'complete_face':
                    return 'complete_face'
        return None
    
    def handle_keyboard_event(self, event):
        """Handle keyboard input from external keyboard"""
        if event.type != pygame.KEYDOWN:
            return
        
        # SAFETY: Only handle keyboard events when on details step
        if self.step != "details":
            print(f"[DEBUG] handle_keyboard_event called but step is '{self.step}', not 'details' - ignoring")
            return
        
        print(f"[DEBUG] Processing keyboard event in handle_keyboard_event. Key: {event.key}")
        
        field_map = {
            'name': 'name',
            'email': 'email',
            'phone': 'phone',
            'pin': 'pin'
        }
        
        if self.active_field not in field_map:
            return
        
        current_value = getattr(self, field_map[self.active_field])
        
        if event.key == pygame.K_BACKSPACE:
            setattr(self, field_map[self.active_field], current_value[:-1])
        elif event.key == pygame.K_TAB:
            # Cycle through fields
            fields = ['name', 'email', 'phone', 'pin']
            current_idx = fields.index(self.active_field)
            self.active_field = fields[(current_idx + 1) % len(fields)]
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            # Try to go to next step
            if self.validate_details():
                print(f"[DEBUG] Enter pressed - changing step from '{self.step}' to 'fingerprint'")
                self.step = "fingerprint"
        else:
            # Handle character input
            if self.active_field == 'pin':
                # Only allow digits for PIN, max 4 chars
                if event.unicode.isdigit() and len(current_value) < 4:
                    setattr(self, field_map[self.active_field], current_value + event.unicode)
            else:
                # Allow alphanumeric and common symbols for other fields
                if event.unicode.isprintable():
                    setattr(self, field_map[self.active_field], current_value + event.unicode)
    
    def validate_details(self):
        """Validate user details"""
        return (len(self.name) > 0 and 
                len(self.pin) == 4 and 
                self.pin.isdigit())
    
    def enroll_fingerprint(self):
        """Enroll fingerprint"""
        print(f"[INFO] Starting fingerprint enrollment for user: {self.name}")
        show_message("Enrolling fingerprint...\nPlace finger on sensor", "info", 2000)
        
        if FingerprintSensor:
            try:
                fp_sensor = FingerprintSensor()
                
                # Enroll new fingerprint
                show_message("Place finger on sensor...", "info", 2000)
                result = fp_sensor.enroll_fingerprint()
                
                if result:
                    self.fingerprint_id = fp_sensor.finger.finger_id
                    print(f"[INFO] Fingerprint enrolled successfully! ID: {self.fingerprint_id}")
                    show_message(f"Fingerprint enrolled!\nID: {self.fingerprint_id}", "success", 2000)
                    self.step = "face"
                    print(f"[INFO] Moving to face capture step")
                    return True
                else:
                    print("[ERROR] Fingerprint enrollment failed")
                    show_message("Fingerprint enrollment failed", "error", 2000)
                    return False
            except Exception as e:
                print(f"[ERROR] Fingerprint enrollment exception: {e}")
                show_message(f"Error: {str(e)}", "error", 2000)
                return False
        else:
            # Demo mode
            self.fingerprint_id = random.randint(1, 127)
            print(f"[INFO] Demo mode: Fingerprint ID {self.fingerprint_id}")
            show_message(f"Demo: Fingerprint ID {self.fingerprint_id}", "success", 2000)
            self.step = "face"
            return True
    
    def capture_face_image(self):
        """Capture face image"""
        print(f"[DEBUG] capture_face_image() called. Current step: {self.step}")
        
        if ImageCapture:
            try:
                # Completely close preview camera to allow ImageCapture to use the camera
                if self.camera:
                    try:
                        self.camera.stop()
                        self.camera.close()
                    except:
                        pass
                    self.camera = None
                    time.sleep(0.5)  # Give camera time to fully release
                
                # Use ImageCapture class to capture and save image
                # Ensure we use the correct dataset path relative to this script
                dataset_path = os.path.join(os.path.dirname(__file__), "face_recognition_folder", "dataset")
                capturer = ImageCapture(dataset_folder=dataset_path)
                image_path = capturer.capture_single_image(self.name, self.face_images_captured + 1)
                
                if image_path:
                    self.face_images_captured += 1
                    self.captured_image_paths.append(image_path)
                    print(f"[INFO] Captured image {self.face_images_captured}/5: {image_path}")
                    show_message(f"Image {self.face_images_captured}/5 captured!", "success", 1500)
                    
                    # Reinitialize preview camera for next capture (only if we haven't captured all 5)
                    if self.face_images_captured < 5:
                        try:
                            import cv2
                            from picamera2 import Picamera2
                            self.camera = Picamera2()
                            config = self.camera.create_preview_configuration(main={"size": (640, 480)})
                            self.camera.configure(config)
                            self.camera.start()
                            time.sleep(0.5)  # Let camera warm up
                            print("[INFO] Preview camera reinitialized")
                        except Exception as cam_err:
                            print(f"[WARNING] Camera reinit error: {cam_err}")
                            # Don't set camera to None - keep it as is, we'll try again on next capture
                    
                    print(f"[DEBUG] capture_face_image() returning True. Step: {self.step}")
                    return True
                else:
                    show_message("Failed to capture image", "error", 2000)
                    # Try to reinitialize preview camera even after failure
                    if self.camera is None:
                        try:
                            import cv2
                            from picamera2 import Picamera2
                            self.camera = Picamera2()
                            config = self.camera.create_preview_configuration(main={"size": (640, 480)})
                            self.camera.configure(config)
                            self.camera.start()
                            time.sleep(0.5)
                        except:
                            pass
                    print(f"[DEBUG] capture_face_image() returning False. Step: {self.step}")
                    return False
                    
            except Exception as e:
                show_message(f"Error: {str(e)}", "error", 2000)
                print(f"[ERROR] Capture error: {e}")
                # Try to reinitialize preview camera even after error
                if self.camera is None:
                    try:
                        import cv2
                        from picamera2 import Picamera2
                        self.camera = Picamera2()
                        config = self.camera.create_preview_configuration(main={"size": (640, 480)})
                        self.camera.configure(config)
                        self.camera.start()
                        time.sleep(0.5)
                    except:
                        pass
                print(f"[DEBUG] capture_face_image() returning False (exception). Step: {self.step}")
                return False
        else:
            # Demo mode
            self.face_images_captured += 1
            self.captured_image_paths.append(f"/tmp/demo_{self.name}_{self.face_images_captured}.jpg")
            show_message(f"Demo: Image {self.face_images_captured}/5 captured", "success", 1500)
            print(f"[DEBUG] capture_face_image() returning True (demo). Step: {self.step}")
            return True
    
    def cleanup_camera(self):
        """Cleanup camera resources"""
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
            except:
                pass
            self.camera = None
    
    def complete_registration(self):
        """Complete user registration"""
        # Cleanup camera
        self.cleanup_camera()
        
        # Create user in database
        show_message("Creating user in database...", "info", 2000)
        success, result = create_user_api(
            self.name, self.email, self.phone, self.pin, self.fingerprint_id
        )
        
        if not success:
            show_message(f"Error: {result}", "error", 3000)
            return False
        
        self.user_id = result.get('user_id')
        print(f"[INFO] User created with ID: {self.user_id}")
        
        # Upload face images to backend
        uploaded_successfully = []
        if len(self.captured_image_paths) > 0:
            print(f"[INFO] Starting upload of {len(self.captured_image_paths)} images...")
            print(f"[INFO] Image paths: {self.captured_image_paths}")
            show_message(f"Uploading {len(self.captured_image_paths)} face images...", "info", 2000)
            upload_count = 0
            for i, image_path in enumerate(self.captured_image_paths):
                print(f"[INFO] Uploading image {i+1}/{len(self.captured_image_paths)}: {image_path}")
                # Check if file exists before uploading
                if not os.path.exists(image_path):
                    print(f"[ERROR] Image file not found: {image_path}")
                    continue
                    
                print(f"[INFO] File exists, size: {os.path.getsize(image_path)} bytes")
                if upload_face_image(self.user_id, image_path):
                    upload_count += 1
                    uploaded_successfully.append(image_path)
                    print(f"[SUCCESS] Successfully uploaded: {image_path}")
                    show_message(f"Uploaded {upload_count}/{len(self.captured_image_paths)} images", "info", 1000)
                else:
                    print(f"[ERROR] Failed to upload: {image_path}")
                    show_message(f"Upload failed for image {i+1}", "error", 2000)
            
            print(f"[INFO] Upload complete: {upload_count}/{len(self.captured_image_paths)} images uploaded successfully")
            
            if upload_count == 0:
                show_message("Error: No images uploaded successfully", "error", 3000)
                print("[ERROR] Registration failed: No images uploaded")
                return False
            elif upload_count < len(self.captured_image_paths):
                show_message(f"Warning: Only {upload_count}/{len(self.captured_image_paths)} images uploaded", "warning", 2000)
                print(f"[WARNING] Partial upload: {upload_count}/{len(self.captured_image_paths)} images")
        else:
            print("[ERROR] No captured image paths found!")
            show_message("Error: No face images captured", "error", 3000)
            return False
        
        # Trigger model retrain
        show_message("Training face recognition model...", "info", 3000)
        retrain_success = trigger_model_retrain()
        
        if retrain_success:
            show_message("Model trained successfully!", "success", 2000)
            print("[INFO] Model training completed")
        else:
            show_message("Warning: Model training may have failed", "warning", 2000)
        
        # Clean up local image files after successful upload and registration
        self.cleanup_local_images()
        
        self.step = "complete"
        return True
    
    def cleanup_local_images(self):
        """Delete local image files after successful upload"""
        try:
            for image_path in self.captured_image_paths:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"[INFO] Deleted local image: {image_path}")
                else:
                    print(f"[WARNING] Local image already removed: {image_path}")
            
            # Also try to remove the user's folder if it's empty
            if self.captured_image_paths:
                user_folder = os.path.dirname(self.captured_image_paths[0])
                try:
                    if os.path.exists(user_folder) and not os.listdir(user_folder):
                        os.rmdir(user_folder)
                        print(f"[INFO] Removed empty user folder: {user_folder}")
                except OSError:
                    # Folder not empty, that's fine
                    pass
                    
        except Exception as e:
            print(f"[WARNING] Error during image cleanup: {e}")
            # Don't fail the registration for cleanup errors


class LinkTelegram:
    """Link Telegram account screen"""
    
    def __init__(self):
        self.step = "instructions"  # instructions -> enter_pin -> complete
        self.temp_pin = ""
        self.entered_pin = ""
        self.chat_id = ""
        self.buttons = {}
    
    def draw(self):
        screen.fill(COLOR_BG)
        
        # Title
        draw_text("Link Telegram", font_title, COLOR_PRIMARY, SCREEN_WIDTH // 2, 40, center=True)
        
        if self.step == "instructions":
            self.draw_instructions()
        elif self.step == "enter_pin":
            self.draw_pin_entry()
        elif self.step == "complete":
            self.draw_completion()
        
        # Back button
        self.buttons['back'] = draw_button("Back", 20, SCREEN_HEIGHT - 70, 150, 50, COLOR_GRAY, COLOR_TEXT)
    
    def draw_instructions(self):
        """Draw instruction screen"""
        y = 100
        
        draw_text("Follow these steps:", font_large, COLOR_TEXT, SCREEN_WIDTH // 2, y, center=True)
        
        y += 60
        instructions = [
            "1. Open Telegram app",
            f"2. Search for @{TELEGRAM_BOT_USERNAME}",
            "3. Send /start command",
            "4. Send /register command",
            "5. Bot will send you a 4-digit PIN",
            "6. Return here and enter the PIN"
        ]
        
        for instruction in instructions:
            draw_text(instruction, font_medium, COLOR_TEXT, 100, y)
            y += 40
        
        # Generate temporary PIN button
        self.buttons['generate'] = draw_button(
            "I'm Ready - Generate PIN", SCREEN_WIDTH // 2 - 180, y + 20, 360, 70, COLOR_SUCCESS
        )
    
    def draw_pin_entry(self):
        """Draw PIN entry screen"""
        y = 120
        
        draw_text("Enter the 4-digit PIN from Telegram bot", font_medium, COLOR_TEXT, 
                 SCREEN_WIDTH // 2, y, center=True)
        
        y += 80
        pin_display = "•" * len(self.entered_pin)
        draw_text(pin_display, font_large, COLOR_TEXT, SCREEN_WIDTH // 2, y, center=True)
        
        # Number pad
        self.draw_numpad()
    
    def draw_numpad(self):
        """Draw numeric keypad"""
        button_size = 80
        spacing = 20
        start_x = (SCREEN_WIDTH - (button_size * 3 + spacing * 2)) // 2
        start_y = 220
        
        # Number buttons
        for i in range(9):
            row = i // 3
            col = i % 3
            x = start_x + col * (button_size + spacing)
            y = start_y + row * (button_size + spacing)
            
            self.buttons[f'num_{i+1}'] = draw_button(
                str(i + 1), x, y, button_size, button_size, COLOR_PRIMARY
            )
        
        # Bottom row
        self.buttons['clear'] = draw_button(
            "CLR", start_x, start_y + 3 * (button_size + spacing), button_size, button_size, COLOR_ERROR
        )
        
        self.buttons['num_0'] = draw_button(
            "0", start_x + button_size + spacing, start_y + 3 * (button_size + spacing), 
            button_size, button_size, COLOR_PRIMARY
        )
        
        self.buttons['verify'] = draw_button(
            "OK", start_x + 2 * (button_size + spacing), start_y + 3 * (button_size + spacing), 
            button_size, button_size, COLOR_SUCCESS
        )
    
    def draw_completion(self):
        """Draw completion screen"""
        draw_text("✓ Telegram Linked Successfully!", font_large, COLOR_SUCCESS, 
                 SCREEN_WIDTH // 2, 200, center=True)
        draw_text("You will now receive door notifications", font_medium, COLOR_TEXT, 
                 SCREEN_WIDTH // 2, 260, center=True)
        
        self.buttons['done'] = draw_button(
            "Done", SCREEN_WIDTH // 2 - 100, 340, 200, 60, COLOR_PRIMARY
        )
    
    def handle_click(self, pos):
        for action, rect in self.buttons.items():
            if rect.collidepoint(pos):
                if action == 'back' or action == 'done':
                    return 'back'
                elif action == 'generate':
                    return 'generate_pin'
                elif action.startswith('num_'):
                    num = action.split('_')[1]
                    if len(self.entered_pin) < 4:
                        self.entered_pin += num
                    # Don't return, just continue to update display
                elif action == 'clear':
                    self.entered_pin = ""
                    # Don't return, just continue to update display
                elif action == 'verify' and len(self.entered_pin) == 4:
                    return 'verify_pin'
        return None
    
    def generate_temp_pin(self):
        """Generate temporary PIN (this should be done by backend)"""
        self.temp_pin = generate_temp_pin()
        # In real implementation, this would be sent to user via Telegram bot
        # For now, we'll show it on screen for testing
        show_message(f"Test PIN (will be sent by bot): {self.temp_pin}", "info", 3000)
        self.step = "enter_pin"
    
    def verify_pin(self):
        """Verify temporary PIN"""
        # In real implementation, verify with backend
        # For demo, we'll just check if it matches
        if self.entered_pin == self.temp_pin:
            self.step = "complete"
            return True
        else:
            show_message("Invalid PIN. Please try again.", "error")
            self.entered_pin = ""
            return False


# =========================================
# MAIN APPLICATION
# =========================================

def main():
    """Main application loop"""
    current_screen = "main_menu"
    screens = {
        "main_menu": MainMenu(),
        "unlock": UnlockDoor(),
        "create_user": CreateUser(),
        "link_telegram": LinkTelegram()
    }
    
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                # Handle keyboard input for CreateUser screen
                if current_screen == "create_user":
                    screen_obj = screens[current_screen]
                    print(f"[DEBUG] KEYDOWN event received. Key: {event.key}, Current step: {screen_obj.step}")
                    if screen_obj.step == "details":
                        screen_obj.handle_keyboard_event(event)
                    else:
                        print(f"[DEBUG] Ignoring key press - not on details step")
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                screen_obj = screens[current_screen]
                action = screen_obj.handle_click(pos)
                
                # Handle actions
                if action == 'back':
                    # Cleanup camera if leaving create_user screen
                    if current_screen == "create_user":
                        screen_obj.cleanup_camera()
                    
                    current_screen = "main_menu"
                    # Reset screens
                    screens["unlock"] = UnlockDoor()
                    screens["create_user"] = CreateUser()
                    screens["link_telegram"] = LinkTelegram()
                
                elif action == 'unlock':
                    current_screen = "unlock"
                
                elif action == 'create_user':
                    current_screen = "create_user"
                
                elif action == 'link_telegram':
                    current_screen = "link_telegram"
                
                elif action == 'verify_pin' and current_screen == "unlock":
                    show_message("Authenticating...", "info", 1000)
                    success, message = screen_obj.verify_and_unlock()
                    show_message(message, "success" if success else "error", 3000)
                    if success:
                        current_screen = "main_menu"
                        screens["unlock"] = UnlockDoor()
                
                elif action == 'enroll_fingerprint' and current_screen == "create_user":
                    print(f"[INFO] Fingerprint enrollment action triggered. Current step: {screen_obj.step}")
                    if screen_obj.enroll_fingerprint():
                        # Successfully enrolled, moved to face step
                        print(f"[INFO] Fingerprint enrolled successfully. New step: {screen_obj.step}")
                    else:
                        print(f"[WARNING] Fingerprint enrollment failed. Current step: {screen_obj.step}")
                
                elif action == 'capture_face' and current_screen == "create_user":
                    print(f"[INFO] Capture face action triggered. Images captured so far: {screen_obj.face_images_captured}/5")
                    screen_obj.capture_face_image()
                    print(f"[INFO] After capture. Images captured: {screen_obj.face_images_captured}/5, Step: {screen_obj.step}")
                
                elif action == 'complete_face' and current_screen == "create_user":
                    print(f"[INFO] Complete registration triggered. Images: {screen_obj.face_images_captured}, Paths: {len(screen_obj.captured_image_paths)}")
                    show_message("Creating user and training model...", "info", 2000)
                    if screen_obj.complete_registration():
                        show_message("User created successfully!", "success", 2000)
                        print("[INFO] Registration completed successfully")
                
                elif action == 'generate_pin' and current_screen == "link_telegram":
                    screen_obj.generate_temp_pin()
                
                elif action == 'verify_pin' and current_screen == "link_telegram":
                    if screen_obj.verify_pin():
                        show_message("Telegram linked successfully!", "success", 2000)
                
                elif action == 'invalid_details':
                    show_message("Please fill all required fields correctly", "error", 2000)
        
        # Draw current screen
        screens[current_screen].draw()
        pygame.display.flip()
        clock.tick(FPS)
    
    # Cleanup before exit
    if current_screen == "create_user":
        screens[current_screen].cleanup_camera()
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
