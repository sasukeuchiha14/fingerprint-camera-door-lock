"""
Telegram Bot for Door Lock System
Runs on VPS alongside Flask backend
Provides notifications and admin controls
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from os import getenv
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
from datetime import datetime, timedelta
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read configuration from environment
BOT_TOKEN = getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = getenv("SUPABASE_SERVICE_ROLE_KEY")
BACKEND_URL = getenv("BACKEND_URL", "https://oracle-apis.hardikgarg.me/doorlock")
ADMIN_CHAT_IDS = getenv("TELEGRAM_ADMIN_CHAT_IDS", "").split(",")  # Comma-separated list

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# =========================================
# HELPER FUNCTIONS
# =========================================

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return str(user_id) in ADMIN_CHAT_IDS


async def delete_pin_message(context: ContextTypes.DEFAULT_TYPE):
    """Delete PIN message and invalidate PIN after 10 minutes"""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message_id = job_data['message_id']
    temp_pin = job_data['temp_pin']
    
    try:
        # Delete the message from Telegram
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Deleted PIN message {message_id} for chat {chat_id}")
        
        # Invalidate the PIN on backend by calling cleanup endpoint
        try:
            requests.post(
                f"{BACKEND_URL}/api/invalidate-telegram-pin",
                json={"temp_pin": temp_pin},
                timeout=5
            )
            logger.info(f"Invalidated temp PIN: {temp_pin}")
        except Exception as e:
            logger.error(f"Failed to invalidate PIN on backend: {e}")
        
        # Send notification that PIN expired
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏱️ Your Telegram registration PIN has expired. Use /register to generate a new one.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error deleting PIN message: {e}")


def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str


# =========================================
# COMMAND HANDLERS
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if user already registered
    try:
        user_data = supabase.table("users").select("*").eq("telegram_chat_id", str(chat_id)).execute()
        is_registered = len(user_data.data) > 0
        is_admin_user = is_registered and user_data.data[0].get('is_admin', False)
    except:
        is_registered = False
        is_admin_user = False
    
    welcome_msg = (
        "🔐 <b>Smart Door Lock System Bot</b>\n\n"
        f"Welcome, {update.effective_user.first_name}!\n\n"
    )
    
    if is_registered:
        if is_admin_user:
            welcome_msg += (
                "👨‍💼 <b>Admin Commands:</b>\n"
                "/status - Check system status\n"
                "/logs - View recent access logs\n"
                "/users - List all users\n"
                "/stats - View statistics\n"
                "/retrain - Retrain face model\n"
                "/help - Show all commands\n"
            )
        else:
            welcome_msg += (
                "📱 <b>Available Commands:</b>\n"
                "/status - Check door status\n"
                "/help - Show help message\n"
            )
    else:
        welcome_msg += (
            "📝 <b>Not Registered Yet</b>\n\n"
            "To link your Telegram account:\n"
            "1. Use /register to get a PIN\n"
            "2. Enter the PIN on the door lock GUI\n"
            "3. Your account will be linked!\n\n"
            "Use /help for more information\n"
        )
    
    await update.message.reply_text(welcome_msg, parse_mode='HTML')


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a temporary PIN for Telegram registration"""
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    
    # Check if already registered
    try:
        user_data = supabase.table("users").select("*").eq("telegram_chat_id", str(chat_id)).execute()
        if user_data.data:
            await update.message.reply_text(
                "✅ You are already registered!\n\n"
                f"Name: {user_data.data[0]['name']}\n"
                f"Email: {user_data.data[0].get('email', 'N/A')}\n\n"
                "Use /help to see available commands.",
                parse_mode='HTML'
            )
            return
    except Exception as e:
        logger.error(f"Error checking registration: {e}")
    
    # Generate PIN via backend
    try:
        response = requests.post(f"{BACKEND_URL}/api/generate-telegram-pin", timeout=10)
        
        if response.status_code != 200:
            await update.message.reply_text(
                "❌ Failed to generate PIN. Please try again later."
            )
            return
        
        result = response.json()
        temp_pin = result['temp_pin']
        
        # Store chat_id with PIN
        verify_response = requests.post(
            f"{BACKEND_URL}/api/verify-telegram-pin",
            json={"temp_pin": temp_pin, "telegram_chat_id": str(chat_id)},
            timeout=10
        )
        
        msg = (
            "🔑 <b>Telegram Registration PIN</b>\n\n"
            f"Your PIN: <code>{temp_pin}</code>\n\n"
            "📱 <b>Next Steps:</b>\n"
            "1. Go to the door lock GUI\n"
            "2. Select 'Link Telegram'\n"
            "3. Click 'I Got the PIN - Continue'\n"
            "4. Authenticate yourself (PIN + Face + Fingerprint)\n"
            "5. Enter this Telegram PIN: <code>{temp_pin}</code>\n"
            "6. Complete!\n\n"
            "⏱ This PIN expires in 10 minutes.\n"
            "⚠️ Can only be used once.\n"
            "🔐 You must authenticate to link your account.\n"
            "🗑️ This message will auto-delete in 10 minutes.\n"
        )
        
        # Send message and store message_id for deletion
        sent_message = await update.message.reply_text(msg, parse_mode='HTML')
        
        # Schedule message deletion after 10 minutes (600 seconds)
        context.application.job_queue.run_once(
            delete_pin_message,
            600,  # 10 minutes
            data={'chat_id': chat_id, 'message_id': sent_message.message_id, 'temp_pin': temp_pin},
            name=f"delete_pin_{temp_pin}"
        )
        
    except Exception as e:
        logger.error(f"Error generating PIN: {e}")
        await update.message.reply_text(
            "❌ Error generating PIN. Please try again."
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check system status"""
    try:
        # Check backend health
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            backend_status = "🟢 Online" if response.status_code == 200 else "🔴 Offline"
        except:
            backend_status = "🔴 Offline"
        
        # Get model info
        try:
            response = requests.get(f"{BACKEND_URL}/api/get-model-info", timeout=5)
            if response.status_code == 200:
                model_info = response.json().get('model', {})
                model_version = model_info.get('model_version', 'Unknown')
                training_date = format_timestamp(model_info.get('training_date', ''))
                num_users = model_info.get('num_users', 0)
                model_status = f"🟢 Active\nVersion: {model_version}\nTrained: {training_date}\nUsers: {num_users}"
            else:
                model_status = "🔴 No active model"
        except:
            model_status = "⚠️ Unable to fetch"
        
        # Get user count
        users_response = supabase.table("users").select("*", count="exact").eq("is_active", True).execute()
        user_count = users_response.count if hasattr(users_response, 'count') else len(users_response.data)
        
        # Get recent access count (last 24h)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        logs_response = supabase.table("access_logs").select("*", count="exact").gte("timestamp", yesterday).execute()
        recent_access_count = logs_response.count if hasattr(logs_response, 'count') else len(logs_response.data)
        
        status_msg = (
            "📊 <b>System Status</b>\n\n"
            f"🖥️ <b>Backend Server:</b> {backend_status}\n"
            f"🧠 <b>Face Model:</b>\n{model_status}\n\n"
            f"👥 <b>Active Users:</b> {user_count}\n"
            f"📝 <b>Access Logs (24h):</b> {recent_access_count}\n"
        )
        
        await update.message.reply_text(status_msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await update.message.reply_text(f"❌ Error fetching status: {str(e)}")


async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View recent access logs"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin access required")
        return
    
    try:
        # Get limit from args or default to 10
        limit = 10
        if context.args and context.args[0].isdigit():
            limit = min(int(context.args[0]), 50)
        
        response = requests.get(f"{BACKEND_URL}/api/get-access-logs?limit={limit}", timeout=10)
        
        if response.status_code != 200:
            await update.message.reply_text("❌ Failed to fetch logs")
            return
        
        logs_data = response.json().get('logs', [])
        
        if not logs_data:
            await update.message.reply_text("📜 No access logs found")
            return
        
        logs_msg = f"📜 <b>Recent Access Logs (Last {limit})</b>\n\n"
        
        for log in logs_data:
            timestamp = format_timestamp(log.get('timestamp', ''))
            access_type = log.get('access_type', 'unknown')
            user_name = log.get('users', {}).get('name', 'Unknown') if log.get('users') else 'Unknown'
            method = log.get('authentication_method', 'N/A')
            
            # Emoji based on access type
            emoji = "✅" if access_type == "success" else "❌"
            if access_type == "break_in_attempt":
                emoji = "🚨"
            
            logs_msg += (
                f"{emoji} <b>{user_name}</b>\n"
                f"  • Time: {timestamp}\n"
                f"  • Type: {access_type}\n"
                f"  • Method: {method}\n\n"
            )
        
        await update.message.reply_text(logs_msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in logs command: {e}")
        await update.message.reply_text(f"❌ Error fetching logs: {str(e)}")


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin access required")
        return
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/get-users", timeout=10)
        
        if response.status_code != 200:
            await update.message.reply_text("❌ Failed to fetch users")
            return
        
        users_data = response.json().get('users', [])
        
        if not users_data:
            await update.message.reply_text("👥 No users found")
            return
        
        users_msg = "👥 <b>Registered Users</b>\n\n"
        
        for user in users_data:
            name = user.get('name', 'Unknown')
            email = user.get('email', 'N/A')
            fingerprint_id = user.get('fingerprint_id', 'N/A')
            last_access = user.get('last_access')
            
            if last_access:
                last_access = format_timestamp(last_access)
            else:
                last_access = 'Never'
            
            users_msg += (
                f"👤 <b>{name}</b>\n"
                f"  • Email: {email}\n"
                f"  • Fingerprint ID: {fingerprint_id}\n"
                f"  • Last Access: {last_access}\n\n"
            )
        
        await update.message.reply_text(users_msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in users command: {e}")
        await update.message.reply_text(f"❌ Error fetching users: {str(e)}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View system statistics"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin access required")
        return
    
    try:
        # Get various statistics
        users_response = supabase.table("users").select("*", count="exact").eq("is_active", True).execute()
        total_users = users_response.count if hasattr(users_response, 'count') else len(users_response.data)
        
        # Get access stats
        logs_response = supabase.table("access_logs").select("access_type", count="exact").execute()
        total_access = logs_response.count if hasattr(logs_response, 'count') else len(logs_response.data)
        
        # Count success vs failures
        success_count = len([log for log in logs_response.data if log['access_type'] == 'success'])
        failed_count = total_access - success_count
        
        # Break-in attempts
        break_in_response = supabase.table("access_logs").select("*", count="exact").eq("access_type", "break_in_attempt").execute()
        break_in_count = break_in_response.count if hasattr(break_in_response, 'count') else len(break_in_response.data)
        
        # Today's access
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_response = supabase.table("access_logs").select("*", count="exact").gte("timestamp", today).execute()
        today_count = today_response.count if hasattr(today_response, 'count') else len(today_response.data)
        
        stats_msg = (
            "📊 <b>System Statistics</b>\n\n"
            f"👥 <b>Total Users:</b> {total_users}\n"
            f"📝 <b>Total Access Logs:</b> {total_access}\n"
            f"✅ <b>Successful Access:</b> {success_count}\n"
            f"❌ <b>Failed Attempts:</b> {failed_count}\n"
            f"🚨 <b>Break-in Attempts:</b> {break_in_count}\n"
            f"📅 <b>Today's Access:</b> {today_count}\n"
        )
        
        if total_access > 0:
            success_rate = (success_count / total_access) * 100
            stats_msg += f"\n📈 <b>Success Rate:</b> {success_rate:.1f}%"
        
        await update.message.reply_text(stats_msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await update.message.reply_text(f"❌ Error fetching statistics: {str(e)}")


async def retrain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger model retraining"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin access required")
        return
    
    try:
        await update.message.reply_text("🔄 Starting model retraining... This may take a few minutes.")
        
        response = requests.post(f"{BACKEND_URL}/api/retrain-model", timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            await update.message.reply_text(
                f"✅ Model retrained successfully!\n\n"
                f"Users: {result.get('num_users', 'N/A')}\n"
                f"Hash: {result.get('model_hash', 'N/A')[:16]}..."
            )
        else:
            await update.message.reply_text("❌ Model retraining failed")
        
    except Exception as e:
        logger.error(f"Error in retrain command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    user_id = update.effective_user.id
    is_admin_user = is_admin(user_id)
    
    help_msg = "📖 <b>Available Commands</b>\n\n"
    
    if is_admin_user:
        help_msg += (
            "👨‍💼 <b>Admin Commands:</b>\n"
            "/start - Welcome message\n"
            "/status - Check system status\n"
            "/logs [n] - View recent access logs (default: 10)\n"
            "/users - List all registered users\n"
            "/stats - View system statistics\n"
            "/retrain - Trigger face model retraining\n"
            "/help - Show this help message\n"
        )
    else:
        help_msg += (
            "📱 <b>User Commands:</b>\n"
            "/start - Welcome message\n"
            "/status - Check door status\n"
            "/help - Show this help message\n"
        )
    
    await update.message.reply_text(help_msg, parse_mode='HTML')


# =========================================
# NOTIFICATION SENDER (Called by Backend)
# =========================================

async def send_notification_to_admins(bot, message: str):
    """Send notification to all admin chat IDs"""
    for chat_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to send notification to {chat_id}: {e}")


# =========================================
# MAIN
# =========================================

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Missing Supabase credentials in environment")
    
    # Build application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("retrain", retrain))
    app.add_handler(CommandHandler("help", help_command))
    
    logger.info("🤖 Door Lock Telegram Bot is running...")
    
    # Run bot
    app.run_polling()


if __name__ == "__main__":
    main()
