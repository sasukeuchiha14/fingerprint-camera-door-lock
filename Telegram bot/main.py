from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from os import getenv
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory
load_dotenv()

# Read bot token from environment
BOT_TOKEN = getenv("TOKEN")

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 Welcome to Door Status Bot!\n\n"
        "You can control and monitor your smart door system here.\n\n"
        "Commands:\n"
        "/status - Check door status\n"
        "/logs - View recent activity\n"
        "/help - See available commands"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Later, you can fetch live status from Raspberry Pi or Supabase
    await update.message.reply_text("🚪 Door Status: Locked 🔒")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Placeholder for logs fetched from database or Pi
    await update.message.reply_text("📜 No activity logs yet.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available Commands:\n"
        "/status - Check current door status\n"
        "/logs - Get entry logs\n"
        "/help - Show this help message"
    )

# --- Main Function ---
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing TOKEN in environment. Create a .env file with TOKEN=\"<your_bot_token>\" or set the env var.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("help", help_command))

    print("🤖 Door Status Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
