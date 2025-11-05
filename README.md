# IoT Multi‑Factor Smart Door Lock

An advanced IoT door lock system with multi-factor authentication: PIN (4x4 keypad), fingerprint (R307), and facial recognition (Pi Camera), plus a cloud backend (Flask on VPS + Supabase) and Telegram notifications.

## 🎥 Demo

[![IoT Multi-Factor Smart Door Lock Demo](https://img.youtube.com/vi/_daMksG2Zuc/maxresdefault.jpg)](https://youtu.be/_daMksG2Zuc)

**Click the image above to watch the full demo on YouTube** 👆

## ✨ Features

- 🔒 Triple authentication: PIN + Fingerprint + Face
- 🖥️ Touch-friendly GUI (Pygame) for 7-inch displays
- ☁️ Cloud sync via Supabase + Flask backend (VPS)
- 📱 Telegram notifications (unlock events, failed attempts, admin commands)
- 🔄 Automatic face model retraining and sync
- 📊 Access logs and admin management

## 🏗️ Architecture Overview

Three layers:
1) Edge device (Raspberry Pi) — GUI, sensors, local auth fallback
2) Cloud backend (VPS + Supabase) — user management, model training/hosting, logs
3) Notifications (Telegram Bot)

## 🛠️ Hardware Requirements

- Raspberry Pi 4/5 and official power adapter
- 7-inch touchscreen (800x480)
- R307 Optical Fingerprint Sensor (UART)
- Pi Camera Module (v1.3/2)
- SG90 Servo Motor
- 4x4 Matrix Keypad (GPIO)
- Jumper wires, microSD card (≥32GB)

### GPIO Pin Connections (BCM)

- Fingerprint (UART): VCC 5V, GND, TX→GPIO15 (RX), RX→GPIO14 (TX)
- Keypad: Rows GPIO 5,6,13,19; Cols GPIO 12,16,20,21
- Servo: Signal GPIO 18; VCC 5V; GND
- Camera: CSI ribbon to Pi camera port

## 🚀 Quick Start

1. Clone repository
   ```bash
   git clone https://github.com/sasukeuchiha14/fingerprint-camera-door-lock.git
   cd fingerprint-camera-door-lock
   ```
2. Raspberry Pi dependencies
   ```bash
   cd "Rasberry pi"
   pip3 install -r requirements.txt
   ```
3. Configure environment
   ```bash
   cp ../.env.example .env
   nano .env
   # Fill in BACKEND_URL, Supabase keys, Telegram details
   ```
4. Run the Pi app
   ```bash
   python3 main.py
   ```

Backend setup, Telegram bot setup, and full deployment are documented in SETUP_GUIDE.md.

## 📦 Project Structure

```
fingerprint-camera-door-lock/
├── Rasberry pi/
│   ├── main.py                   # Main Pi flow (PIN → Face → Fingerprint)
│   ├── raw_data.py               # Raw sensor reads logger (week 1a)
│   ├── face_recognition_folder/  # Face recognition modules
│   ├── fingerprint/              # R307 fingerprint interface
│   ├── numpad/                   # Keypad input
│   └── servo/                    # Door lock control
├── Backend/
│   ├── server.py                 # Flask API (VPS)
│   └── requirements.txt
├── supabase/
│   └── setup.sql                 # Database schema
├── assets/
│   ├── banner.png
│   ├── gpio.png
│   └── raspberrypi5.jpg
├── README.md
└── LICENSE
```

## 🌐 API Endpoints (Backend)

Base URL: `<BACKEND_URL>` (for example: `https://your-domain.example.com/doorlock`)

- `GET /health` — Health check
- `POST /api/verify-user` — Verify user credentials
- `POST /api/log-access` — Log access attempt
- `GET /api/get-users` — List users
- `POST /api/add-user` — Add user
- `POST /api/upload-face-image` — Upload face image
- `POST /api/retrain-model` — Retrain face model
- `GET /api/get-model-info` — Get current model info
- `GET /models/trained_model.pkl` — Download current model
- `GET /api/get-access-logs` — Access logs
- `POST /api/sync-status` — Pi status sync

## 🧪 Raw Sensor Reads (Week 1a)

Use `Rasberry pi/raw_data.py` to record unprocessed sensor logs for PIN keypad, fingerprint, and camera recognition. The script prints timestamped logs suitable for screen recording.

## 🔐 Security Best Practices

- Never commit `.env` or secrets
- Use HTTPS for backend
- Enable Supabase RLS policies
- Rotate keys periodically
- Monitor access logs

## 📄 License

This project is licensed under the Boost Software License 1.0 — see the [LICENSE](LICENSE) file for details.

## 👤 Author

Hardik Garg ([@sasukeuchiha14](https://github.com/sasukeuchiha14))

## 🙏 Acknowledgments

- Face Recognition library (ageitgey)
- Adafruit Fingerprint Sensor resources
- Supabase team
- Raspberry Pi Foundation


