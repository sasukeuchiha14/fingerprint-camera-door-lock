"""
Flask Backend Server for Door Lock System
Runs on VPS at localhost:7000 (internal)
Accessible via: https://oracle-apis.hardikgarg.me/doorlock/

Nginx Configuration:
  location /doorlock/ {
      proxy_pass http://localhost:7000/;
      rewrite ^/doorlock(/.*)$ $1 break;
  }

Handles:
- User management
- Face model training and hosting
- Authentication verification
- Webhook endpoints for Telegram bot
- Sync with Raspberry Pi
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
import hashlib
import pickle
import face_recognition
import cv2
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from pathlib import Path
import json
import logging
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Model storage configuration
MODEL_DIR = Path("/var/www/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_MODEL_PATH = MODEL_DIR / "trained_model.pkl"

# Upload configuration
UPLOAD_DIR = Path("/tmp/face_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =========================================
# HELPER FUNCTIONS
# =========================================

def send_telegram_notification(message: str, notification_type: str = "info"):
    """Send notification via Telegram bot to all linked users"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not configured")
            return False
        
        # Get all users with linked Telegram accounts
        users_response = supabase.table("users").select("telegram_chat_id").not_.is_("telegram_chat_id", "null").execute()
        
        if not users_response.data:
            logger.warning("No users with linked Telegram accounts found")
            return False
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Add emoji based on type
        emoji_map = {
            "success": "✅",
            "error": "❌", 
            "warning": "⚠️",
            "info": "ℹ️",
            "unlock": "🔓",
            "security_alert": "🚨",
            "break_in": "🚨"
        }
        emoji = emoji_map.get(notification_type, "📢")
        
        formatted_message = f"{emoji} {message}"
        
        # Send to all linked users
        sent_count = 0
        for user in users_response.data:
            try:
                payload = {
                    "chat_id": user["telegram_chat_id"],
                    "text": formatted_message,
                    "parse_mode": "HTML"
                }
                
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    sent_count += 1
                else:
                    logger.warning(f"Failed to send to chat {user['telegram_chat_id']}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error sending to chat {user['telegram_chat_id']}: {e}")
        
        logger.info(f"Telegram notification sent to {sent_count}/{len(users_response.data)} users")
        return sent_count > 0
        
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def train_face_model():
    """
    Train face recognition model from all user images in Supabase
    Returns: (success, model_path, model_hash, num_users)
    """
    try:
        logger.info("Starting face model training...")
        
        # Fetch all active users
        users_response = supabase.table("users").select("*").eq("is_active", True).execute()
        users = users_response.data
        
        if not users:
            logger.warning("No active users found for training")
            return False, None, None, 0
        
        known_encodings = []
        known_names = []
        
        # Process each user
        for user in users:
            user_id = user['user_id']
            user_name = user['name']
            
            # Get face images for this user
            images_response = supabase.table("face_images").select("*").eq("user_id", user_id).execute()
            face_images = images_response.data
            
            if not face_images:
                logger.warning(f"No face images found for user {user_name}")
                continue
            
            # Download and process each image
            for img_record in face_images:
                image_url = img_record['image_url']
                
                # Download image from Supabase Storage
                try:
                    # Extract bucket and path from URL
                    # URL format: https://<project>.supabase.co/storage/v1/object/public/face-images/<path>
                    bucket_name = "face-images"
                    file_path = image_url.split(f"{bucket_name}/")[-1]
                    
                    image_data = supabase.storage.from_(bucket_name).download(file_path)
                    
                    # Convert to numpy array
                    nparr = np.frombuffer(image_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Get face encodings
                    encodings = face_recognition.face_encodings(rgb_image)
                    
                    if encodings:
                        known_encodings.append(encodings[0])
                        known_names.append(user_name)
                        logger.info(f"Processed image for {user_name}")
                    else:
                        logger.warning(f"No face found in image for {user_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing image {image_url}: {e}")
                    continue
        
        if not known_encodings:
            logger.error("No valid face encodings generated")
            return False, None, None, 0
        
        # Save model
        data = {
            "encodings": known_encodings,
            "names": known_names
        }
        
        with open(CURRENT_MODEL_PATH, "wb") as f:
            pickle.dump(data, f)
        
        # Calculate hash
        model_hash = calculate_file_hash(CURRENT_MODEL_PATH)
        
        # Generate version string
        model_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save model metadata to database
        model_url = f"https://oracle-apis.hardikgarg.me/doorlock/models/trained_model.pkl"
        
        # Deactivate old models
        supabase.table("model_metadata").update({"is_active": False}).eq("is_active", True).execute()
        
        # Insert new model metadata
        model_data = {
            "model_version": model_version,
            "model_url": model_url,
            "model_hash": model_hash,
            "num_users": len(users),
            "is_active": True
        }
        supabase.table("model_metadata").insert(model_data).execute()
        
        logger.info(f"Model trained successfully: {model_version}, Users: {len(users)}, Hash: {model_hash}")
        
        # Send notification
        send_telegram_notification(
            f"Face model retrained successfully!\n"
            f"Version: {model_version}\n"
            f"Users: {len(users)}\n"
            f"Face encodings: {len(known_encodings)}",
            "success"
        )
        
        return True, CURRENT_MODEL_PATH, model_hash, len(users)
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        send_telegram_notification(f"Model training failed: {str(e)}", "error")
        return False, None, None, 0


# =========================================
# API ENDPOINTS
# =========================================

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "door-lock-backend"
    }), 200


@app.route("/api/verify-user", methods=["POST"])
def verify_user():
    """
    Verify user credentials (PIN, fingerprint ID, face)
    Request body: {
        "pin_code": "1234",
        "fingerprint_id": 1,
        "face_match": "Hardik Garg" (optional)
    }
    """
    try:
        data = request.get_json()
        pin_code = data.get("pin_code")
        fingerprint_id = data.get("fingerprint_id")
        face_match = data.get("face_match")
        
        # Query user from database
        query = supabase.table("users").select("*").eq("is_active", True)
        
        if pin_code:
            query = query.eq("pin_code", pin_code)
        
        if fingerprint_id is not None:
            query = query.eq("fingerprint_id", fingerprint_id)
        
        response = query.execute()
        
        if not response.data:
            # Log failed attempt
            log_data = {
                "access_type": "failed_authentication",
                "authentication_method": "combined",
                "notes": f"No user found with PIN: {pin_code}, Fingerprint: {fingerprint_id}"
            }
            supabase.table("access_logs").insert(log_data).execute()
            
            return jsonify({
                "success": False,
                "message": "Authentication failed"
            }), 401
        
        user = response.data[0]
        
        # Log successful attempt
        log_data = {
            "user_id": user['user_id'],
            "access_type": "success",
            "authentication_method": "combined",
            "notes": f"User verified via PIN and fingerprint"
        }
        supabase.table("access_logs").insert(log_data).execute()
        
        # Send notification
        send_telegram_notification(
            f"🔓 Door unlocked by <b>{user['name']}</b>\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Method: PIN + Fingerprint",
            "door_unlock"
        )
        
        return jsonify({
            "success": True,
            "user": {
                "user_id": user['user_id'],
                "name": user['name'],
                "email": user['email']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying user: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/log-access", methods=["POST"])
def log_access():
    """
    Log access attempt from Raspberry Pi
    Request body: {
        "user_id": "uuid" (optional),
        "access_type": "success|failed_password|failed_face|failed_fingerprint|break_in_attempt",
        "authentication_method": "password|face|fingerprint|combined",
        "confidence_score": 0.95 (optional),
        "notes": "Additional info"
    }
    """
    try:
        data = request.get_json()
        
        log_data = {
            "user_id": data.get("user_id"),
            "access_type": data.get("access_type"),
            "authentication_method": data.get("authentication_method"),
            "confidence_score": data.get("confidence_score"),
            "notes": data.get("notes")
        }
        
        result = supabase.table("access_logs").insert(log_data).execute()
        
        # Get current timestamp for notifications
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        access_type = data.get("access_type")
        method = data.get("authentication_method", "Unknown")
        
        # Convert method names to user-friendly format
        method_names = {
            "password": "PIN Code",
            "face": "Face Recognition", 
            "fingerprint": "Fingerprint",
            "gui": "Combined Authentication",
            "combined": "Combined Authentication"
        }
        friendly_method = method_names.get(method, method.capitalize())
        
        # Send notifications based on access type
        if access_type == "success":
            # Get user name for successful access
            user_id = data.get("user_id")
            user_name = "Unknown User"
            
            if user_id:
                try:
                    user_response = supabase.table("users").select("name").eq("user_id", user_id).execute()
                    if user_response.data:
                        user_name = user_response.data[0]["name"]
                except Exception as e:
                    logger.error(f"Error getting user name: {e}")
            
            # Send successful unlock notification
            send_door_unlock_notification(user_name, friendly_method, current_time)
            
        elif access_type in ["failed_password", "failed_face", "failed_fingerprint", "failed_combined"]:
            # Count recent failed attempts in last hour
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            failed_attempts = supabase.table("access_logs").select("*", count="exact").gte("timestamp", one_hour_ago).in_("access_type", ["failed_password", "failed_face", "failed_fingerprint", "failed_combined"]).execute()
            attempts_count = failed_attempts.count if hasattr(failed_attempts, 'count') else len(failed_attempts.data)
            
            # Send failed attempt notification
            send_failed_attempt_notification(friendly_method, current_time, attempts_count)
            
        elif access_type == "break_in_attempt":
            # Send break-in notification to admins only
            send_telegram_notification(
                f"🚨 <b>BREAK-IN ATTEMPT DETECTED!</b>\n"
                f"Time: {current_time}\n"
                f"Details: {data.get('notes', 'Unknown')}",
                "break_in"
            )
        
        return jsonify({
            "success": True,
            "log_id": result.data[0]['log_id']
        }), 200
        
    except Exception as e:
        logger.error(f"Error logging access: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def send_door_unlock_notification(user_name: str, method: str, timestamp: str):
    """Send door unlock notification via Telegram"""
    try:
        message = (
            f"🔓 <b>Door Unlocked Successfully!</b>\n\n"
            f"👤 User: {user_name}\n"
            f"🔐 Method: {method.capitalize()}\n"
            f"⏰ Time: {timestamp}\n\n"
            f"Have a great day! 🌟"
        )
        
        send_telegram_notification(message, "unlock")
        logger.info(f"Door unlock notification sent for user: {user_name}")
        
    except Exception as e:
        logger.error(f"Error sending door unlock notification: {e}")


def send_failed_attempt_notification(method: str, timestamp: str, attempts_count: int):
    """Send failed attempt notification via Telegram"""
    try:
        security_warning = ""
        if attempts_count > 3:
            security_warning = f"\n\n⚠️ <b>HIGH ALERT:</b> {attempts_count} failed attempts in the last hour!"
        elif attempts_count > 1:
            security_warning = f"\n\n⚠️ <b>CAUTION:</b> {attempts_count} failed attempts in the last hour."
        
        message = (
            f"🚫 <b>Failed Door Access Attempt</b>\n\n"
            f"🔐 Method: {method.capitalize()}\n"
            f"⏰ Time: {timestamp}\n"
            f"📊 Recent attempts: {attempts_count}"
            f"{security_warning}\n\n"
            f"If this wasn't you, please check your premises immediately! 🚨"
        )
        
        send_telegram_notification(message, "security_alert")
        logger.info(f"Failed attempt notification sent: {method}")
        
    except Exception as e:
        logger.error(f"Error sending failed attempt notification: {e}")


@app.route("/api/get-users", methods=["GET"])
def get_users():
    """Get all active users"""
    try:
        response = supabase.table("users").select("*").eq("is_active", True).execute()
        return jsonify({
            "success": True,
            "users": response.data
        }), 200
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/add-user", methods=["POST"])
def add_user():
    """
    Add new user
    Request body: {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "pin_code": "1234",
        "fingerprint_id": 3
    }
    """
    try:
        data = request.get_json()
        
        user_data = {
            "name": data.get("name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "pin_code": data.get("pin_code"),
            "fingerprint_id": data.get("fingerprint_id")
        }
        
        result = supabase.table("users").insert(user_data).execute()
        
        send_telegram_notification(
            f"👤 New user added: <b>{data.get('name')}</b>\n"
            f"Email: {data.get('email')}\n"
            f"Fingerprint ID: {data.get('fingerprint_id')}",
            "info"
        )
        
        return jsonify({
            "success": True,
            "user": result.data[0]
        }), 201
        
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload-face-image", methods=["POST"])
def upload_face_image():
    """
    Upload face image for a user
    Form data:
        - user_id: UUID
        - image: file
    """
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image file"}), 400
        
        user_id = request.form.get('user_id')
        image_file = request.files['image']
        
        if not user_id:
            return jsonify({"success": False, "error": "user_id required"}), 400
        
        # Save temporarily
        filename = secure_filename(f"{user_id}_{datetime.now().timestamp()}.jpg")
        temp_path = UPLOAD_DIR / filename
        image_file.save(temp_path)
        
        # Upload to Supabase Storage
        with open(temp_path, 'rb') as f:
            file_data = f.read()
            
        storage_path = f"{user_id}/{filename}"
        supabase.storage.from_("face-images").upload(storage_path, file_data)
        
        # Get public URL
        image_url = supabase.storage.from_("face-images").get_public_url(storage_path)
        
        # Save to database
        image_data = {
            "user_id": user_id,
            "image_url": image_url
        }
        supabase.table("face_images").insert(image_data).execute()
        
        # Clean up temp file
        temp_path.unlink()
        
        return jsonify({
            "success": True,
            "image_url": image_url
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading face image: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/retrain-model", methods=["POST"])
def retrain_model():
    """Trigger face recognition model retraining"""
    try:
        success, model_path, model_hash, num_users = train_face_model()
        
        if success:
            return jsonify({
                "success": True,
                "model_hash": model_hash,
                "num_users": num_users,
                "message": "Model retrained successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Model training failed"
            }), 500
            
    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/get-model-info", methods=["GET"])
def get_model_info():
    """Get current active model information"""
    try:
        response = supabase.table("model_metadata").select("*").eq("is_active", True).order("training_date", desc=True).limit(1).execute()
        
        if response.data:
            return jsonify({
                "success": True,
                "model": response.data[0]
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "No active model found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/models/trained_model.pkl", methods=["GET"])
def download_model():
    """Download current trained model"""
    try:
        if not CURRENT_MODEL_PATH.exists():
            return jsonify({"error": "Model not found"}), 404
        
        from flask import send_file
        return send_file(
            CURRENT_MODEL_PATH,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name='trained_model.pkl'
        )
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/get-access-logs", methods=["GET"])
def get_access_logs():
    """Get recent access logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        response = supabase.table("access_logs").select("*, users(name, email)").order("timestamp", desc=True).limit(limit).execute()
        
        return jsonify({
            "success": True,
            "logs": response.data
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching access logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sync-status", methods=["POST"])
def sync_status():
    """
    Raspberry Pi sends status update
    Request body: {
        "status": "online|offline",
        "last_sync": "timestamp",
        "model_hash": "current_model_hash"
    }
    """
    try:
        data = request.get_json()
        
        # Check if model needs update
        current_model = supabase.table("model_metadata").select("*").eq("is_active", True).order("training_date", desc=True).limit(1).execute()
        
        needs_update = False
        if current_model.data:
            server_hash = current_model.data[0]['model_hash']
            pi_hash = data.get('model_hash', '')
            needs_update = (server_hash != pi_hash)
        
        return jsonify({
            "success": True,
            "needs_model_update": needs_update,
            "latest_model_hash": current_model.data[0]['model_hash'] if current_model.data else None,
            "latest_model_url": current_model.data[0]['model_url'] if current_model.data else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error syncing status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate-telegram-pin", methods=["POST"])
def generate_telegram_pin():
    """
    Generate temporary PIN for Telegram linking
    Request body: {
        "user_id": "uuid" (optional - if linking existing user)
    }
    Returns: {
        "temp_pin": "1234",
        "expires_at": "timestamp"
    }
    """
    try:
        import random
        import string
        from datetime import datetime, timedelta
        
        # Generate 4-digit PIN
        temp_pin = ''.join(random.choices(string.digits, k=4))
        expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
        
        # Store in system_settings as temporary data
        setting_key = f"telegram_pin_{temp_pin}"
        setting_value = {
            "pin": temp_pin,
            "expires_at": expires_at,
            "used": False
        }
        
        supabase.table("system_settings").upsert({
            "setting_key": setting_key,
            "setting_value": json.dumps(setting_value),
            "description": "Temporary PIN for Telegram linking"
        }).execute()
        
        return jsonify({
            "success": True,
            "temp_pin": temp_pin,
            "expires_at": expires_at
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating PIN: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/link-telegram", methods=["POST"])
def link_telegram():
    """
    Link Telegram chat ID to user account
    Request body: {
        "temp_pin": "1234",
        "user_id": "uuid" (optional - for authenticated linking)
    }
    OR
    {
        "temp_pin": "1234",
        "telegram_chat_id": "123456789" (legacy format)
    }
    """
    try:
        data = request.get_json()
        temp_pin = data.get('temp_pin')
        telegram_chat_id = data.get('telegram_chat_id')  # Optional for legacy support
        user_id = data.get('user_id')  # Optional for authenticated linking
        
        if not temp_pin:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        # Verify PIN exists and not expired
        setting_key = f"telegram_pin_{temp_pin}"
        pin_data = supabase.table("system_settings").select("*").eq("setting_key", setting_key).execute()
        
        if not pin_data.data:
            return jsonify({"success": False, "error": "Invalid PIN"}), 400
        
        setting_value = json.loads(pin_data.data[0]['setting_value'])
        
        # Check if already used
        if setting_value.get('used'):
            return jsonify({"success": False, "error": "PIN already used"}), 400
        
        # Check expiration
        from datetime import datetime
        expires_at = datetime.fromisoformat(setting_value['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({"success": False, "error": "PIN expired"}), 400
        
        # Get telegram_chat_id from stored PIN data if not provided
        if not telegram_chat_id:
            telegram_chat_id = setting_value.get('telegram_chat_id')
            if not telegram_chat_id:
                return jsonify({"success": False, "error": "No chat ID associated with this PIN"}), 400
        
        # Get user_id from PIN data (if stored) or find next user without telegram or use provided user_id
        if user_id:
            # Authenticated linking - use the provided user_id
            target_user_id = user_id
        else:
            # Legacy flow - use stored user_id or find first user without telegram
            target_user_id = setting_value.get('user_id')
            
            if not target_user_id:
                # Find first user without telegram_chat_id
                users = supabase.table("users").select("*").is_("telegram_chat_id", "null").execute()
                if not users.data:
                    return jsonify({"success": False, "error": "No user found to link"}), 400
                target_user_id = users.data[0]['user_id']
        
        # Update user with telegram_chat_id
        supabase.table("users").update({
            "telegram_chat_id": telegram_chat_id,
            "updated_at": datetime.now().isoformat()
        }).eq("user_id", target_user_id).execute()
        
        # Mark PIN as used
        setting_value['used'] = True
        supabase.table("system_settings").update({
            "setting_value": json.dumps(setting_value)
        }).eq("setting_key", setting_key).execute()
        
        # Get updated user info
        user = supabase.table("users").select("*").eq("user_id", target_user_id).execute()
        
        return jsonify({
            "success": True,
            "user": user.data[0] if user.data else None,
            "message": "Telegram linked successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error linking Telegram: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/verify-telegram-pin", methods=["POST"])
def verify_telegram_pin():
    """
    Verify temporary PIN from Telegram bot
    Request body: {
        "temp_pin": "1234",
        "telegram_chat_id": "123456789"
    }
    """
    try:
        data = request.get_json()
        temp_pin = data.get('temp_pin')
        telegram_chat_id = str(data.get('telegram_chat_id'))
        
        # Store chat_id with PIN for later linking
        setting_key = f"telegram_pin_{temp_pin}"
        pin_data = supabase.table("system_settings").select("*").eq("setting_key", setting_key).execute()
        
        if not pin_data.data:
            return jsonify({"success": False, "error": "Invalid PIN"}), 400
        
        setting_value = json.loads(pin_data.data[0]['setting_value'])
        setting_value['telegram_chat_id'] = telegram_chat_id
        
        supabase.table("system_settings").update({
            "setting_value": json.dumps(setting_value)
        }).eq("setting_key", setting_key).execute()
        
        return jsonify({
            "success": True,
            "message": "PIN verified, proceed to GUI to complete linking"
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying PIN: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":
    # Run server
    app.run(
        host="0.0.0.0",
        port=7000,
        debug=False
    )
