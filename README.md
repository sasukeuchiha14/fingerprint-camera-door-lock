# 🔐 Smart Door Lock System# 🔐 Cloud-Enabled Fingerprint & Face Recognition Door Lock System



A cloud-enabled biometric door lock with touchscreen GUI, face recognition, fingerprint authentication, and Telegram notifications.An advanced IoT security system with cloud integration, featuring fingerprint, facial recognition, and PIN authentication with real-time Telegram notifications.



![Door Lock System](assets/banner.png)![System Architecture](assets/demo.gif)



## ✨ Features## 🏗️ Architecture Overview



- 🖥️ **Touch-Friendly GUI** - Pygame interface optimized for 7-inch screens### **3-Layer Cloud Architecture**

- 👤 **Face Recognition** - dlib-based facial identification

- 🔍 **Fingerprint Auth** - R307 sensor with 200+ template storage```

- 🔐 **PIN Security** - 4-digit code via on-screen keyboard┌─────────────────────────────────────────────────────────────┐

- ☁️ **Cloud Sync** - Supabase database + VPS backend│                    LAYER 1: Edge Device                     │

- 📱 **Telegram Bot** - Real-time notifications & admin controls│                     (Raspberry Pi)                          │

- 🔄 **Auto Updates** - Face model retraining and sync│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐      │

- 👨‍💼 **Admin System** - Database-managed privileges│  │ Fingerprint│  │ Face Recog  │  │  PIN Input       │      │

- 📊 **Access Logs** - Complete audit trail│  │  Sensor    │  │  + Camera   │  │  (Keypad)        │      │

- 🌐 **REST API** - Full backend integration│  └────────────┘  └─────────────┘  └──────────────────┘      │

│         │               │                    │              │

## 🏗️ System Architecture│         └───────────────┴────────────────────┘              │

│                         │                                   │

```│                 Local Fallback Auth                         │

┌──────────────────────┐│                         │                                   │

│   Raspberry Pi       │└─────────────────────────┼───────────────────────────────────┘

│   Touch GUI          │ ← Main Interface                          │

│   (Pygame)           │                     HTTPS / REST API

└─────────┬────────────┘                          │

          │┌─────────────────────────┼──────────────────────────────── ──┐

          ├─► R307 Fingerprint Sensor│                    LAYER 2: Cloud Backend                   │

          ├─► Pi Camera (Face Recognition)│                  (VPS + Supabase)                           │

          └─► Servo Motor (Door Lock)│  ┌──────────────────────────────────────────────────┐       │

          ││  │          Supabase (PostgreSQL + Storage)         │       │

          ├─► VPS Backend (Flask API)│  │  • User Management  • Face Images                │       │

          │   └─► Supabase PostgreSQL│  │  • Access Logs      • Model Metadata             │       │

          ││  └──────────────────────────────────────────────────┘       │

          └─► Telegram Bot (Notifications)│                          │                                  │

```│  ┌──────────────────────────────────────────────────┐       │

│  │        Flask Backend (oracle-apis:7000)          │       │

## 🚀 Quick Start│  │  • Authentication   • Model Training             │       │

│  │  • User CRUD        • Model Hosting              │       │

### Hardware Required│  └──────────────────────────────────────────────────┘       │

└─────────────────────────┬───────────────────────────────────┘

- Raspberry Pi 4/5                          │

- 7-inch touchscreen (800x480)┌─────────────────────────┼───────────────────────────────────┐

- R307 Fingerprint Sensor│                LAYER 3: Notification Layer                  │

- Pi Camera Module v2│                    (Telegram Bot)                           │

- SG90 Servo Motor│  📱 Real-time Notifications:                                 │

- Jumper wires│  • Door Unlock Alerts   • Break-in Warnings                 │

│  • Model Updates        • System Status                     │

### Software Setup│  • Admin Commands       • Access Logs                       │

└─────────────────────────────────────────────────────────────┘

1. **Clone Repository**```

   ```bash

   git clone https://github.com/sasukeuchiha14/fingerprint-camera-door-lock.git## ✨ Features

   cd fingerprint-camera-door-lock

   ```### 🔒 **Triple-Layer Authentication**

- **Fingerprint Recognition** - R307 sensor with 200+ template storage

2. **Install Dependencies**- **Facial Recognition** - dlib-based face encoding with 99.38% accuracy

   ```bash- **PIN Code** - 4-digit password via 4x4 matrix keypad

   cd "Rasberry pi"

   pip3 install -r requirements.txt### ☁️ **Cloud Integration**

   ```- **Supabase Backend** - PostgreSQL database with real-time sync

- **VPS Server** - Flask API for model training and user management

3. **Configure Environment**- **Automatic Model Updates** - Pi downloads retrained models automatically

   ```bash- **Local Fallback** - Works offline when cloud is unavailable

   cp ../.env.example .env

   nano .env### 📲 **Telegram Notifications**

   ```- Real-time door unlock alerts with user info

   Fill in your Supabase URL, backend URL, and Telegram bot details.- Break-in attempt warnings after failed auth

- System status and health monitoring

4. **Run GUI**- Admin commands for remote management

   ```bash

   python3 gui_app.py### 🧠 **Smart Model Management**

   ```- Automatic face model retraining when users change

- Hash-based model versioning

For complete setup instructions, see **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.- Efficient download only when needed

- Periodic sync with 24-hour intervals

## 🎯 Main Functions

## 🛠️ Hardware Requirements

### 1. Unlock Door

- Enter PIN on touchscreen| Component | Specification | Description |

- Automatic face scan|-----------|--------------|-------------|

- Fingerprint verification| **Raspberry Pi** | Pi 5 (or Pi 4) | Main processing unit |

- Cloud authentication| **Power Supply** | Official Pi Adapter | 5V 3A recommended |

- Door unlocks!| **Keypad** | 4x4 Matrix Keypad | PIN code entry |

| **Camera** | Pi Camera v1.3 (5MP) | Facial recognition |

### 2. Create New User| **Fingerprint Sensor** | R307 | Biometric authentication |

- Fill user details with on-screen keyboard| **Servo Motor** | SG90 | Door lock mechanism |

- Enroll fingerprint (guided)| **Jumper Wires** | 20x M-F | GPIO connections |

- Capture 5 face images| **MicroSD Card** | 64GB Class 10 | OS & storage |

- System auto-trains model

- User created & synced to cloud### 📌 **GPIO Pin Connections**



### 3. Link Telegram**Fingerprint Sensor (UART)**

- Generate 4-digit PIN in GUI- VCC → 5V (Pin 4)

- Send `/register` to Telegram bot- GND → GND (Pin 6)

- Enter PIN from bot- TX → GPIO 15 (RX) (Pin 10)

- Account linked - receive notifications!- RX → GPIO 14 (TX) (Pin 8)



## 👨‍💼 Admin Management**4x4 Keypad**

- Rows: GPIO 5, 6, 13, 19

Admins are managed via Supabase dashboard:- Cols: GPIO 12, 16, 20, 21



1. Login to [Supabase Dashboard](https://app.supabase.com)**Servo Motor**

2. Go to Table Editor → `users`- Signal → GPIO 18 (Pin 12)

3. Set `is_admin = true` for admin users- VCC → 5V (Pin 2)

- GND → GND (Pin 14)

**Admin Commands (Telegram):**

- `/status` - System health**Camera**

- `/logs` - Recent access logs- Connect to CSI port

- `/users` - All registered users

- `/stats` - Usage statistics## 📦 Installation & Setup

- `/retrain` - Trigger model retraining

### 1️⃣ **Supabase Setup**

## 📁 Project Structure

```bash

```# 1. Create a new Supabase project at https://supabase.com

fingerprint-camera-door-lock/# 2. Run the database schema

├── Rasberry pi/cd supabase

│   ├── gui_app.py              # Main touchscreen application# Copy the contents of setup.sql and run in Supabase SQL Editor

│   ├── face_recognition_folder/ # Face recognition modules

│   ├── fingerprint/            # Fingerprint sensor interface# 3. Create storage buckets in Supabase Dashboard:

│   └── servo/                  # Door lock control#    - face-images (private)

├── Backend/#    - access-captures (private)

│   ├── server.py               # Flask API server#    - face-models (public)

│   ├── nginx.conf              # Nginx reverse proxy config

│   └── requirements.txt# 4. Get your credentials:

├── Telegram bot/#    - Project URL

│   ├── main.py                 # Telegram notification bot#    - Anon key

│   └── requirements.txt#    - Service role key

├── supabase/```

│   └── setup.sql               # Database schema

├── .env.example                # Environment template### 2️⃣ **VPS Backend Setup**

├── README.md                   # This file

└── SETUP_GUIDE.md             # Complete deployment guide```bash

```# SSH into your VPS

ssh user@oracle-apis.hardikgarg.me

## 🔐 Security Features

# Clone repository

- **Triple Authentication** - PIN + Face + Fingerprintgit clone https://github.com/sasukeuchiha14/fingerprint-camera-door-lock.git

- **Encrypted Database** - Supabase with RLS policiescd fingerprint-camera-door-lock/Backend

- **Temporary PINs** - 10-minute expiration for Telegram linking

- **Access Logging** - All attempts recorded with timestamps# Install dependencies

- **Local Fallback** - Works offline if cloud unavailablepip install -r requirements.txt

- **Admin Controls** - Database-managed permissions

# Create .env file

## 📱 Telegram Integrationcp ../.env.example .env

nano .env  # Fill in your Supabase credentials

Users receive real-time notifications for:

- ✅ Successful door unlocks# Run backend server

- ⚠️ Failed authentication attemptspython server.py

- 👤 New user registrations

- 🔄 System model updates# Or use PM2 for production

pm2 start server.py --name doorlock-backend --interpreter python3

Admins get additional controls via bot commands.pm2 save

pm2 startup

## 🛠️ Technology Stack```



**Hardware:**### 3️⃣ **Telegram Bot Setup**

- Raspberry Pi 5 (Debian-based OS)

- R307 Optical Fingerprint Sensor (UART)```bash

- Pi Camera Module v2 (5MP)# On VPS (same or different server)

- 7-inch Capacitive Touchscreencd Telegram\ bot



**Software:**# Install dependencies

- **GUI:** Pygame 2.5.2pip install -r requirements.txt

- **Face Recognition:** dlib + face_recognition

- **Backend:** Flask (Python 3.11)# Create .env file with:

- **Database:** Supabase PostgreSQL# TELEGRAM_BOT_TOKEN=your_bot_token

- **Bot:** python-telegram-bot# TELEGRAM_ADMIN_CHAT_IDS=your_chat_id

- **Reverse Proxy:** Nginx# SUPABASE_URL=...

# SUPABASE_SERVICE_ROLE_KEY=...

## 📊 Database Schema

# Run bot

- **users** - User accounts with biometric datapython main.py

- **face_images** - Face training images

- **access_logs** - Door access history# Or use PM2

- **model_metadata** - Face recognition model versionspm2 start main.py --name doorlock-telegram --interpreter python3

- **system_settings** - Configuration & temp data```

- **notifications** - Telegram notification queue

**Get Telegram Bot Token:**

## 🌐 Cloud Backend1. Message @BotFather on Telegram

2. Send `/newbot` and follow instructions

Deployed on VPS at: `https://oracle-apis.hardikgarg.me/doorlock`3. Copy the token



**API Endpoints:****Get Your Chat ID:**

- `POST /api/add-user` - Create user1. Message @userinfobot on Telegram

- `POST /api/verify-user` - Authenticate2. Copy your chat ID

- `POST /api/link-telegram` - Link Telegram account

- `POST /api/retrain-model` - Trigger model training### 4️⃣ **Raspberry Pi Setup**

- `GET /api/get-users` - List all users

- `POST /api/log-access` - Log access attempt```bash

# SSH or directly on Pi

## 📖 Documentationssh pi@raspberrypi.local



- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete deployment instructions# Install system dependencies

- **[.env.example](.env.example)** - Environment configuration templatesudo apt update

- **[Backend/NGINX_SETUP.md](Backend/NGINX_SETUP.md)** - Nginx configuration guidesudo apt install -y python3-opencv python3-pip cmake libopenblas-dev liblapack-dev



## 🤝 Contributing# Clone repository

cd ~/

This is a personal IoT project. Feel free to fork and adapt for your needs.git clone https://github.com/sasukeuchiha14/fingerprint-camera-door-lock.git

cd fingerprint-camera-door-lock/Rasberry\ pi

## 📄 License

# Install Python dependencies

MIT License - See [LICENSE](LICENSE) file for details.pip install -r requirements.txt



## 🆘 Support# Create .env file

cp ../.env.example .env

For setup help, see **[SETUP_GUIDE.md](SETUP_GUIDE.md)**.nano .env  # Add BACKEND_URL and other config



For issues, check:# Enable camera and serial interfaces

1. Hardware connectionssudo raspi-config

2. Environment variables in `.env`# Navigate to: Interface Options → Enable Camera

3. Backend connectivity# Navigate to: Interface Options → Enable Serial Port

4. Database schema is up to date# Disable serial console, enable serial hardware



## 🎯 Demo# Reboot

sudo reboot

**User Enrollment:** ~2 minutes```

**Door Unlock:** ~5 seconds

**Telegram Linking:** ~1 minute### 5️⃣ **Enroll Users**



---**Step 1: Register Fingerprint**

```bash

**Built with ❤️ for home automation and IoT security**cd ~/fingerprint-camera-door-lock/Rasberry\ pi/fingerprint

python edit_sensor.py
# Follow prompts to enroll fingerprints (note the ID number)
```

**Step 2: Capture Face Images**
```bash
cd ~/fingerprint-camera-door-lock/Rasberry\ pi/face_recognition_folder
python image_capture.py
# Take 20-30 photos from different angles
```

**Step 3: Add User to Database**
```bash
# Use the backend API or run SQL:
INSERT INTO users (name, email, phone, fingerprint_id, pin_code) 
VALUES ('Your Name', 'email@example.com', '+1234567890', 1, '1234');
```

**Step 4: Upload Face Images to Supabase**
```python
# Use the backend API endpoint:
curl -X POST https://oracle-apis.hardikgarg.me:7000/api/upload-face-image \
  -F "user_id=YOUR_USER_ID" \
  -F "image=@path/to/image.jpg"
```

**Step 5: Train Model**
```bash
# Trigger model retraining via Telegram bot:
/retrain

# Or use API:
curl -X POST https://oracle-apis.hardikgarg.me:7000/api/retrain-model
```

### 6️⃣ **Run the System**

```bash
cd ~/fingerprint-camera-door-lock/Rasberry\ pi
python main.py
```

**Expected Flow:**
1. ✅ Cloud connectivity check
2. 📥 Model update (if needed)
3. 🔢 PIN entry prompt
4. 📷 Face recognition
5. 👆 Fingerprint scan
6. ☁️ Cloud verification
7. 🔓 Door unlock!

## 📱 Telegram Bot Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Welcome message & commands | All |
| `/status` | System health & statistics | All |
| `/logs [n]` | Recent access logs (default 10) | Admin |
| `/users` | List all registered users | Admin |
| `/stats` | Detailed system statistics | Admin |
| `/retrain` | Trigger model retraining | Admin |
| `/help` | Show all commands | All |

## 🔄 Auto-Sync & Cron Jobs

**On Raspberry Pi** (optional - for periodic model updates):
```bash
crontab -e

# Add this line to check for model updates every 6 hours:
0 */6 * * * cd ~/fingerprint-camera-door-lock/Rasberry\ pi && python -c "from main import update_model_if_needed; update_model_if_needed()"
```

**On VPS** (optional - for auto-cleanup):
```bash
crontab -e

# Clean old images after 7 days:
0 2 * * * python /path/to/cleanup_script.py
```

## 🌐 API Endpoints

### **Backend Server (`https://oracle-apis.hardikgarg.me:7000`)**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/verify-user` | POST | Verify user credentials |
| `/api/log-access` | POST | Log access attempt |
| `/api/get-users` | GET | Get all users |
| `/api/add-user` | POST | Add new user |
| `/api/upload-face-image` | POST | Upload face image |
| `/api/retrain-model` | POST | Trigger model retraining |
| `/api/get-model-info` | GET | Get current model info |
| `/models/trained_model.pkl` | GET | Download trained model |
| `/api/get-access-logs` | GET | Get access logs |
| `/api/sync-status` | POST | Pi status sync |

## 🗄️ Database Schema

**Tables:**
- `users` - User profiles with PIN and fingerprint ID
- `face_images` - URLs to face images in Supabase storage
- `access_logs` - All authentication attempts
- `model_metadata` - Face model versions and hashes
- `system_settings` - Configuration
- `notifications` - Telegram notification queue

## 🔐 Security Best Practices

✅ **Never commit `.env` files** - Contains sensitive credentials  
✅ **Use HTTPS** - Encrypt data in transit  
✅ **Enable Supabase RLS** - Row-level security policies  
✅ **Rotate keys regularly** - Update API keys periodically  
✅ **Monitor access logs** - Check for suspicious activity  
✅ **Enable local fallback** - System works offline  
✅ **Use strong PINs** - Avoid 0000, 1234, etc.

## 🐛 Troubleshooting

### **Fingerprint sensor not detected**
```bash
# Check serial ports
ls /dev/ttyAMA* /dev/serial*

# Test connection
python fingerprint/test_serial.py
```

### **Camera not working**
```bash
# Test camera
libcamera-hello

# Check if enabled
sudo raspi-config  # Interface Options → Camera
```

### **Cloud connection failed**
- Check `.env` file has correct `BACKEND_URL`
- Test with: `curl https://oracle-apis.hardikgarg.me:7000/health`
- System will use local fallback automatically

### **Model training fails**
- Ensure face images are uploaded to Supabase
- Check backend logs for errors
- Verify dlib is installed correctly

## 📊 System Performance

- **Authentication Time:** ~5-8 seconds (all 3 methods)
- **Face Recognition Accuracy:** 99.38%
- **Fingerprint False Accept Rate:** < 0.001%
- **Model Update Time:** 30-60 seconds
- **Cloud Sync:** < 2 seconds

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 References & Documentation

- [Face Recognition Library](https://github.com/ageitgey/face_recognition)
- [Adafruit Fingerprint Sensor](https://learn.adafruit.com/adafruit-optical-fingerprint-sensor)
- [Supabase Documentation](https://supabase.com/docs)
- [Raspberry Pi GPIO](https://pinout.xyz/)
- [python-telegram-bot](https://docs.python-telegram-bot.org/)

## 👨‍💻 Author

**Hardik Garg** ([@sasukeuchiha14](https://github.com/sasukeuchiha14))

## 🙏 Acknowledgments

- Face Recognition by Adam Geitgey
- Adafruit for fingerprint sensor libraries
- Supabase team for the amazing backend platform
- Raspberry Pi Foundation

---

**⚡ Powered by**: Raspberry Pi • Supabase • Python • Telegram

**🔗 Project Links**:
- GitHub: [github.com/sasukeuchiha14/fingerprint-camera-door-lock](https://github.com/sasukeuchiha14/fingerprint-camera-door-lock)
- Backend: oracle-apis.hardikgarg.me:7000
- Telegram Bot: @YourDoorLockBot

