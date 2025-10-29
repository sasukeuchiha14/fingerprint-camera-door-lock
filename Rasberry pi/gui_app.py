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
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480
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
        
        response = requests.post(f"{BACKEND_URL}/api/add-user", json=data, timeout=10)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json().get('error', 'Unknown error')
    except Exception as e:
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
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {'user_id': user_id}
            
            response = requests.post(
                f"{BACKEND_URL}/api/upload-face-image",
                files=files,
                data=data,
                timeout=30
            )
            
            return response.status_code == 200
    except Exception as e:
        print(f"Upload failed: {e}")
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
                elif action == 'clear':
                    self.pin = ""
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
        self.step = "details"  # details -> fingerprint -> face -> complete
        self.name = ""
        self.email = ""
        self.phone = ""
        self.pin = ""
        self.fingerprint_id = None
        self.user_id = None
        self.face_images_captured = 0
        self.active_field = "name"
        self.buttons = {}
        self.keyboard_visible = False
        self.keyboard_text = ""
    
    def draw(self):
        screen.fill(COLOR_BG)
        
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
        
        # Back button
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
        
        # Simple keyboard for touch input
        if self.keyboard_visible:
            self.draw_simple_keyboard()
    
    def draw_simple_keyboard(self):
        """Draw a simple on-screen keyboard"""
        keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '@'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '.', 'DEL', 'SPC']
        ]
        
        key_width = 70
        key_height = 50
        start_x = 20
        start_y = SCREEN_HEIGHT - 250
        spacing = 5
        
        for row_idx, row in enumerate(keys):
            for col_idx, key in enumerate(row):
                x = start_x + col_idx * (key_width + spacing)
                y = start_y + row_idx * (key_height + spacing)
                
                self.buttons[f'key_{key}'] = draw_button(
                    key, x, y, key_width, key_height, COLOR_PRIMARY, font=font_small
                )
    
    def draw_fingerprint_enroll(self):
        """Draw fingerprint enrollment screen"""
        draw_text("Fingerprint Enrollment", font_large, COLOR_TEXT, SCREEN_WIDTH // 2, 120, center=True)
        draw_text("Place finger on sensor multiple times", font_medium, COLOR_TEXT, SCREEN_WIDTH // 2, 180, center=True)
        
        # Start enrollment button
        self.buttons['enroll_fp'] = draw_button(
            "Start Enrollment", SCREEN_WIDTH // 2 - 150, 250, 300, 70, COLOR_PRIMARY
        )
    
    def draw_face_capture(self):
        """Draw face capture screen"""
        draw_text("Face Capture", font_large, COLOR_TEXT, SCREEN_WIDTH // 2, 120, center=True)
        draw_text(f"Images captured: {self.face_images_captured}/5", font_medium, COLOR_TEXT, 
                 SCREEN_WIDTH // 2, 180, center=True)
        draw_text("Position face in front of camera", font_medium, COLOR_DARK_GRAY, 
                 SCREEN_WIDTH // 2, 220, center=True)
        
        # Capture button
        self.buttons['capture_face'] = draw_button(
            "Capture Image", SCREEN_WIDTH // 2 - 150, 270, 300, 70, COLOR_PRIMARY
        )
        
        if self.face_images_captured >= 5:
            # Complete button
            self.buttons['complete_face'] = draw_button(
                "Complete & Train Model", SCREEN_WIDTH // 2 - 180, 360, 360, 70, COLOR_SUCCESS
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
        for action, rect in self.buttons.items():
            if rect.collidepoint(pos):
                if action == 'back':
                    return 'back'
                elif action == 'done':
                    return 'back'
                elif action in ['name', 'email', 'phone', 'pin']:
                    self.active_field = action
                    self.keyboard_visible = True
                elif action == 'next':
                    if self.validate_details():
                        self.step = "fingerprint"
                    else:
                        return 'invalid_details'
                elif action == 'enroll_fp':
                    return 'enroll_fingerprint'
                elif action == 'capture_face':
                    return 'capture_face'
                elif action == 'complete_face':
                    return 'complete_face'
                elif action.startswith('key_'):
                    key = action.split('_')[1]
                    self.handle_keyboard_input(key)
        return None
    
    def handle_keyboard_input(self, key):
        """Handle keyboard input"""
        field_map = {
            'name': 'name',
            'email': 'email',
            'phone': 'phone',
            'pin': 'pin'
        }
        
        current_value = getattr(self, field_map[self.active_field])
        
        if key == 'DEL':
            setattr(self, field_map[self.active_field], current_value[:-1])
        elif key == 'SPC':
            setattr(self, field_map[self.active_field], current_value + ' ')
        elif self.active_field == 'pin' and len(current_value) < 4 and key.isdigit():
            setattr(self, field_map[self.active_field], current_value + key)
        elif self.active_field != 'pin':
            setattr(self, field_map[self.active_field], current_value + key.lower())
    
    def validate_details(self):
        """Validate user details"""
        return (len(self.name) > 0 and 
                len(self.pin) == 4 and 
                self.pin.isdigit())
    
    def enroll_fingerprint(self):
        """Enroll fingerprint"""
        if FingerprintSensor:
            try:
                # This would call the actual fingerprint enrollment
                # For now, we'll use a placeholder
                show_message("Place finger on sensor...", "info", 2000)
                # In real implementation: fingerprint_sensor.enroll()
                self.fingerprint_id = random.randint(1, 127)  # Demo
                self.step = "face"
                return True
            except Exception as e:
                show_message(f"Error: {str(e)}", "error")
                return False
        else:
            self.fingerprint_id = random.randint(1, 127)  # Demo mode
            self.step = "face"
            return True
    
    def capture_face_image(self):
        """Capture face image"""
        if ImageCapture:
            try:
                # Use ImageCapture class
                capturer = ImageCapture()
                image_path = capturer.capture_single_image(self.name, self.face_images_captured + 1)
                
                if image_path:
                    self.face_images_captured += 1
                    return True
                else:
                    return False
            except Exception as e:
                show_message(f"Error: {str(e)}", "error")
                return False
        else:
            self.face_images_captured += 1  # Demo mode
            return True
    
    def complete_registration(self):
        """Complete user registration"""
        # Create user in database
        success, result = create_user_api(
            self.name, self.email, self.phone, self.pin, self.fingerprint_id
        )
        
        if not success:
            show_message(f"Error: {result}", "error")
            return False
        
        self.user_id = result.get('user_id')
        
        # Upload face images (in real implementation)
        # for i in range(self.face_images_captured):
        #     upload_face_image(self.user_id, f"/tmp/face_{i}.jpg")
        
        # Trigger model retrain
        show_message("Training face recognition model...", "info", 3000)
        trigger_model_retrain()
        
        self.step = "complete"
        return True


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
                elif action == 'clear':
                    self.entered_pin = ""
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
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                screen_obj = screens[current_screen]
                action = screen_obj.handle_click(pos)
                
                # Handle actions
                if action == 'back':
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
                    screen_obj.enroll_fingerprint()
                
                elif action == 'capture_face' and current_screen == "create_user":
                    screen_obj.capture_face_image()
                
                elif action == 'complete_face' and current_screen == "create_user":
                    show_message("Creating user and training model...", "info", 2000)
                    if screen_obj.complete_registration():
                        show_message("User created successfully!", "success", 2000)
                
                elif action == 'generate_pin' and current_screen == "link_telegram":
                    screen_obj.generate_temp_pin()
                
                elif action == 'verify_pin' and current_screen == "link_telegram":
                    if screen_obj.verify_pin():
                        show_message("Telegram linked successfully!", "success", 2000)
                
                elif action == 'invalid_details':
                    show_message("Please fill all required fields correctly", "error")
        
        # Draw current screen
        screens[current_screen].draw()
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
