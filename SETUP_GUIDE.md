# 🛠️ Complete Setup Guide

Your comprehensive guide to deploying the Smart Door Lock System from scratch.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Hardware Assembly](#hardware-assembly)
3. [Supabase Setup](#supabase-setup)
4. [VPS Backend Deployment](#vps-backend-deployment)
5. [Telegram Bot Setup](#telegram-bot-setup)
6. [Raspberry Pi Configuration](#raspberry-pi-configuration)
7. [Testing & Verification](#testing--verification)
8. [Admin Management](#admin-management)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Checklist
- [ ] Raspberry Pi 4 or 5 (recommended: 4GB RAM)
- [ ] 7-inch touchscreen display (800x480)
- [ ] R307 Fingerprint Sensor
- [ ] Pi Camera Module v2 (or compatible USB webcam)
- [ ] SG90 Servo Motor
- [ ] MicroSD card (32GB+, Class 10)
- [ ] Power supply (5V 3A)
- [ ] Jumper wires (M-F, 20+ pieces)
- [ ] Breadboard (optional, for prototyping)

### Software/Services
- [ ] Supabase account (free tier works)
- [ ] VPS server (1GB RAM minimum)
- [ ] Domain/subdomain for backend
- [ ] Telegram account

### Skills Required
- Basic Linux command line
- Understanding of GPIO pins
- SSH access knowledge
- Basic networking (optional for troubleshooting)

---

## Hardware Assembly

### 1. Fingerprint Sensor (R307)

**Connection:**
```
R307 Sensor    →  Raspberry Pi
----------------------------------------
VCC (Red)      →  5V (Pin 2 or 4)
GND (Black)    →  GND (Pin 6)
TX (White)     →  RX GPIO 15 (Pin 10)
RX (Green)     →  TX GPIO 14 (Pin 8)
```

**Enable Serial Port:**
```bash
sudo raspi-config
# 3. Interface Options → Serial Port
# Login shell: No
# Serial hardware: Yes
sudo reboot
```

**Test:**
```bash
cd "Rasberry pi/fingerprint"
python3 test_serial.py
```

### 2. Pi Camera

**Connect:**
- Insert ribbon cable into CSI port
- Blue side faces ethernet port
- Enable camera:
  ```bash
  sudo raspi-config
  # 3. Interface Options → Camera → Enable
  sudo reboot
  ```

**Test:**
```bash
libcamera-hello
# or
raspistill -o test.jpg
```

### 3. Servo Motor

**Connection:**
```
Servo          →  Raspberry Pi
----------------------------------------
VCC (Red)      →  5V (Pin 2)
GND (Brown)    →  GND (Pin 14)
Signal (Orange)→  GPIO 17 (Pin 11)
```

**Test:**
```bash
cd "Rasberry pi/servo"
python3 rotate.py
```

### 4. Touchscreen

**7-inch DSI Touchscreen:**
- Connect via DSI port
- Power via GPIO pins
- Should auto-detect on boot

**USB Touchscreen:**
- Just plug in via USB
- Calibrate if needed:
  ```bash
  sudo apt install xinput-calibrator
  xinput_calibrator
  ```

---

## Supabase Setup

### Step 1: Create Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign in / Create account
3. Click "New Project"
4. Fill details:
   - Name: `door-lock-system`
   - Database Password: (save this!)
   - Region: (closest to you)
5. Wait for project creation (~2 minutes)

### Step 2: Run Database Schema

1. Go to **SQL Editor** (left sidebar)
2. Click "New Query"
3. Copy entire contents of `supabase/setup.sql`
4. Paste and click "Run"
5. Verify tables created:
   - Go to **Table Editor**
   - Should see: users, face_images, access_logs, model_metadata, system_settings, notifications

### Step 3: Get API Keys

1. Go to **Project Settings** → **API**
2. Copy these values (you'll need them):
   ```
   Project URL: https://xxxxx.supabase.co
   anon/public key: eyJhbGc...
   service_role key: eyJhbGc... (keep secret!)
   JWT Secret: (under JWT Settings)
   ```

### Step 4: Create Storage Bucket (Optional)

For face images:
1. Go to **Storage** → **New Bucket**
2. Name: `face-images`
3. Public: No
4. Create

---

## VPS Backend Deployment

### Step 1: Server Setup

**SSH to your VPS:**
```bash
ssh user@oracle-apis.hardikgarg.me
```

**Update system:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git nginx -y
```

### Step 2: Clone Repository

```bash
cd ~
git clone https://github.com/sasukeuchiha14/fingerprint-camera-door-lock.git
cd fingerprint-camera-door-lock/Backend
```

### Step 3: Install Dependencies

```bash
pip3 install -r requirements.txt
```

Required packages:
- flask
- flask-cors
- python-dotenv
- supabase
- face-recognition
- opencv-python
- numpy
- requests

### Step 4: Configure Environment

```bash
nano .env
```

Add:
```env
# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-service-role-key...
SUPABASE_JWT_SECRET=your-jwt-secret

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_ADMIN_CHAT_IDS=  # Leave empty, managed via database now

# Backend URL (for self-reference)
BACKEND_URL=https://oracle-apis.hardikgarg.me/doorlock
```

### Step 5: Setup Nginx Reverse Proxy

```bash
sudo cp nginx.conf /etc/nginx/sites-available/doorlock
sudo ln -s /etc/nginx/sites-available/doorlock /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Optional: SSL with Certbot**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d oracle-apis.hardikgarg.me
```

### Step 6: Start Backend Server

**Test run:**
```bash
python3 server.py
# Should see: Running on http://0.0.0.0:7000
```

**Production (keep terminal open):**
```bash
python3 server.py
```

**Or use screen/tmux:**
```bash
screen -S doorlock-backend
python3 server.py
# Press Ctrl+A, D to detach
# Reattach: screen -r doorlock-backend
```

### Step 7: Test Backend

```bash
# From another terminal
curl http://localhost:7000/health
# Should return: {"status":"healthy","timestamp":"..."}

curl https://oracle-apis.hardikgarg.me/doorlock/health
# Should also work via nginx
```

---

## Telegram Bot Setup

### Step 1: Create Bot

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Choose name: `My Door Lock Bot`
5. Choose username: `MyDoorLockBot` (must end in 'bot')
6. Copy the token: `123456789:ABCdefgh...`

### Step 2: Get Your Chat ID

1. Search for `@userinfobot`
2. Send `/start`
3. Copy your chat ID: `123456789`

### Step 3: Configure Bot

**On VPS:**
```bash
cd ~/fingerprint-camera-door-lock/Telegram\ bot
nano .env
```

Add:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABCdefgh...your-token...

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# Backend
BACKEND_URL=https://oracle-apis.hardikgarg.me/doorlock
```

### Step 4: Install Dependencies

```bash
pip3 install -r requirements.txt
```

### Step 5: Start Bot

**Test:**
```bash
python3 main.py
# Should see: Door Lock Telegram Bot is running...
```

**Production:**
```bash
screen -S doorlock-telegram
python3 main.py
# Ctrl+A, D to detach
```

### Step 6: Test Bot

1. Open Telegram
2. Search for your bot: `@MyDoorLockBot`
3. Send `/start`
4. Should receive welcome message

---

## Raspberry Pi Configuration

### Step 1: Raspberry Pi OS Setup

**Flash OS:**
1. Download Raspberry Pi Imager
2. Flash "Raspberry Pi OS with Desktop" to SD card
3. Boot Pi and complete setup wizard

**Update system:**
```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Enable Interfaces

```bash
sudo raspi-config
```

Enable:
- Interface Options → Camera → Yes
- Interface Options → Serial Port → Shell: No, Hardware: Yes
- System Options → Boot → Desktop (for GUI)

Reboot:
```bash
sudo reboot
```

### Step 3: Clone Repository

```bash
cd ~/Desktop
git clone https://github.com/sasukeuchiha14/fingerprint-camera-door-lock.git
cd fingerprint-camera-door-lock/Rasberry\ pi
```

### Step 4: Install Dependencies

```bash
pip3 install -r requirements.txt --break-system-packages
```

This installs:
- pygame
- face-recognition
- opencv-python
- adafruit-fingerprint
- picamera2
- gpiozero
- requests
- python-dotenv

### Step 5: Configure Environment

```bash
nano .env
```

Add:
```env
BACKEND_URL=https://oracle-apis.hardikgarg.me/doorlock
TELEGRAM_BOT_USERNAME=MyDoorLockBot
```

### Step 6: Test GUI

```bash
python3 gui_app.py
```

Should see touchscreen interface with three buttons.

### Step 7: Autostart (Optional)

**Method 1: Desktop Autostart**
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/doorlock.desktop
```

Add:
```ini
[Desktop Entry]
Type=Application
Name=Door Lock GUI
Exec=python3 /home/pi/Desktop/fingerprint-camera-door-lock/Rasberry\ pi/gui_app.py
Terminal=false
```

**Method 2: systemd Service**
```bash
sudo nano /etc/systemd/system/doorlock-gui.service
```

Add:
```ini
[Unit]
Description=Door Lock GUI
After=graphical.target

[Service]
Type=simple
User=pi
Environment="DISPLAY=:0"
WorkingDirectory=/home/pi/Desktop/fingerprint-camera-door-lock/Rasberry pi
ExecStart=/usr/bin/python3 gui_app.py
Restart=always

[Install]
WantedBy=graphical.target
```

Enable:
```bash
sudo systemctl enable doorlock-gui.service
sudo systemctl start doorlock-gui.service
```

---

## Testing & Verification

### Complete System Test

#### 1. Create First User

**Via GUI:**
1. Tap "Create New User"
2. Fill details:
   - Name: Test User
   - Email: test@example.com
   - Phone: +1234567890
   - PIN: 1234
3. Tap "Next"
4. Tap "Start Enrollment"
5. Place finger on sensor 3-5 times
6. Tap "Capture Image" 5 times (different angles)
7. Tap "Complete & Train Model"
8. Wait for model training (~2 minutes)

**Verify:**
```bash
# Check user in database
curl https://oracle-apis.hardikgarg.me/doorlock/api/get-users
```

#### 2. Link Telegram

**Via GUI:**
1. Tap "Link Telegram"
2. Tap "I'm Ready - Generate PIN"
3. Note the PIN

**Via Telegram:**
1. Open bot: `@MyDoorLockBot`
2. Send `/register`
3. Bot sends 4-digit PIN

**Back to GUI:**
1. Enter PIN from bot
2. Tap "OK"
3. Should show "Linked!"

**Verify:**
- Send `/status` to bot
- Should respond with system status

#### 3. Test Door Unlock

1. Tap "Unlock Door"
2. Enter PIN: 1234
3. Look at camera for face scan
4. Place finger on sensor
5. Should unlock!

**Check Telegram:**
- Should receive notification: "🔓 Door unlocked by Test User"

---

## Admin Management

### Set Admin User

**Via Supabase Dashboard:**
1. Go to [app.supabase.com](https://app.supabase.com)
2. Select your project
3. Table Editor → `users`
4. Find user row
5. Edit `is_admin` column → `true`
6. Save

### Test Admin Commands

Send to Telegram bot:
```
/status   → System health check
/logs     → Recent 10 access logs
/users    → All registered users
/stats    → Door usage statistics
/retrain  → Trigger model retraining
```

Only admins can use these commands.

---

## Troubleshooting

### Backend Issues

**"Connection refused"**
```bash
# Check if backend is running
curl http://localhost:7000/health

# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check logs
tail -f /var/log/nginx/error.log
```

**"Import error: face_recognition"**
```bash
# Install system dependencies
sudo apt install cmake build-essential -y
pip3 install dlib face-recognition
```

### Raspberry Pi Issues

**"Fingerprint sensor not found"**
```bash
# Check serial port
ls -l /dev/serial*
# Should show /dev/serial0

# Test serial
sudo minicom -D /dev/serial0 -b 57600

# Re-enable in raspi-config
sudo raspi-config
```

**"Camera not working"**
```bash
# Test camera
libcamera-hello

# Check if enabled
vcgencmd get_camera
# Should show: supported=1 detected=1

# Re-enable
sudo raspi-config
# Interface Options → Camera → Yes
sudo reboot
```

**"Pygame not opening"**
```bash
# Check display
echo $DISPLAY
# Should be :0

# Export if needed
export DISPLAY=:0
python3 gui_app.py
```

**"Touch not responding"**
```bash
# List input devices
xinput list

# Calibrate touchscreen
sudo apt install xinput-calibrator
xinput_calibrator
```

### Database Issues

**"Table does not exist"**
```sql
-- Re-run schema in Supabase SQL Editor
-- Copy from supabase/setup.sql
```

**"RLS policy error"**
```sql
-- Disable RLS for testing (not recommended for production)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
```

### Telegram Bot Issues

**"Bot not responding"**
```bash
# Check bot is running
ps aux | grep main.py

# Check logs
# (check terminal where bot is running)

# Test bot token
curl https://api.telegram.org/bot<TOKEN>/getMe
```

**"Unauthorized error"**
- Verify `TELEGRAM_BOT_TOKEN` in .env
- Check token with BotFather

### Common Errors

**"Cloud unavailable"**
- Check `BACKEND_URL` in .env
- Test: `curl https://oracle-apis.hardikgarg.me/doorlock/health`
- Verify internet connection

**"Model not found"**
- Ensure model training completed
- Check `model_metadata` table in Supabase
- Trigger retrain: `/retrain` via Telegram

**"PIN expired"**
- PINs expire after 10 minutes
- Generate new PIN via `/register`

---

## Production Checklist

### Security
- [ ] Change all default passwords
- [ ] Enable SSL on backend (certbot)
- [ ] Enable RLS policies in Supabase
- [ ] Use strong Supabase service role key
- [ ] Don't commit `.env` files to git
- [ ] Restrict Supabase API access by IP (optional)

### Performance
- [ ] Backend server has adequate resources (1GB+ RAM)
- [ ] Database has proper indexes (already in setup.sql)
- [ ] Face images are compressed
- [ ] Model file is optimized

### Monitoring
- [ ] Set up Telegram notifications
- [ ] Test admin commands work
- [ ] Check access logs regularly
- [ ] Monitor backend uptime
- [ ] Set up database backups (Supabase auto-backup)

### Maintenance
- [ ] Document admin users
- [ ] Keep dependencies updated
- [ ] Backup face model periodically
- [ ] Clean old access logs (optional)
- [ ] Test disaster recovery

---

## Quick Reference Commands

### Raspberry Pi
```bash
# Start GUI
python3 gui_app.py

# Test fingerprint
python3 fingerprint/test_serial.py

# Test camera
libcamera-hello

# Check logs
journalctl -u doorlock-gui.service -f
```

### VPS Backend
```bash
# Start backend
python3 server.py

# Check health
curl http://localhost:7000/health

# View users
curl https://oracle-apis.hardikgarg.me/doorlock/api/get-users

# Reload nginx
sudo systemctl reload nginx
```

### Telegram Bot
```bash
# Start bot
python3 main.py

# User commands
/start
/register

# Admin commands
/status
/logs
/users
/stats
/retrain
```

### Database
```sql
-- View all users
SELECT * FROM users;

-- View recent logs
SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 10;

-- Set admin
UPDATE users SET is_admin = true WHERE name = 'Your Name';

-- View active model
SELECT * FROM model_metadata WHERE is_active = true;
```

---

## Support & Resources

### Documentation
- **README.md** - Project overview
- **Backend/NGINX_SETUP.md** - Nginx configuration
- **.env.example** - Environment template

### Hardware Documentation
- [R307 Datasheet](https://www.openhacks.com/uploadsproductos/r307_fingerprint_module_user_manual.pdf)
- [Pi Camera Guide](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [GPIO Pinout](https://pinout.xyz/)

### Software Documentation
- [Pygame Docs](https://www.pygame.org/docs/)
- [Supabase Docs](https://supabase.com/docs)
- [python-telegram-bot](https://docs.python-telegram-bot.org/)

---

**Setup complete! Enjoy your smart door lock system! 🎉**
