#!/usr/bin/env python3
"""
Raw Sensor Data Collector for IoT Fingerprint Camera Door Lock
=====================================

This script collects raw, unprocessed data from all sensors in the project:
1. Fingerprint Sensor (R307) - Raw fingerprint detection and matching data
2. Camera Module (5MP v1.3) - Face detection and recognition logs
3. 4x4 Matrix Keypad - Raw keypress input data

Usage: python3 raw_data.py
Author: Hardik
Date: October 26, 2025
"""

import time
import datetime
import sys
import json
import threading
import traceback
from queue import Queue

# Import sensor modules
try:
    import serial
    import adafruit_fingerprint
    import face_recognition
    import cv2
    import numpy as np
    from picamera2 import Picamera2
    import pickle
    from gpiozero import DigitalOutputDevice, Button
    import os
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please install required packages:")
    print("pip install pyserial adafruit-circuitpython-fingerprint face-recognition opencv-python picamera2 gpiozero")
    sys.exit(1)

class RawDataCollector:
    def __init__(self):
        """Initialize raw data collector for all sensors"""
        self.running = True
        self.data_queue = Queue()
        
        # Sensor status
        self.fingerprint_active = False
        self.camera_active = False
        self.keypad_active = False
        
        print("=" * 60)
        print("🔍 IOT RAW SENSOR DATA COLLECTOR")
        print("=" * 60)
        print(f"⏰ Start Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📊 Collecting raw data from:")
        print("   1. Fingerprint Sensor (R307)")
        print("   2. Camera Module (Face Recognition)")
        print("   3. 4x4 Matrix Keypad")
        print("=" * 60)
        
    def log_data(self, sensor_type, raw_data, status="INFO"):
        """Log raw sensor data with timestamp"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = {
            "timestamp": timestamp,
            "sensor": sensor_type,
            "status": status,
            "raw_data": raw_data
        }
        
        # Print to console for video recording
        print(f"[{timestamp}] {sensor_type}: {raw_data}")
        
        # Store for later analysis if needed
        self.data_queue.put(log_entry)

    def fingerprint_raw_data(self):
        """Collect raw data from fingerprint sensor"""
        print("\n🔐 FINGERPRINT SENSOR - Raw Data Collection")
        print("-" * 50)
        
        try:
            # Initialize fingerprint sensor
            uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
            finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
            
            self.log_data("FINGERPRINT", "Sensor initialized successfully")
            self.log_data("FINGERPRINT", f"Baudrate: 57600, Port: /dev/ttyAMA0")
            
            # Get sensor parameters
            if finger.read_sysparam() == adafruit_fingerprint.OK:
                self.log_data("FINGERPRINT", f"Sensor capacity: {finger.capacity}")
                self.log_data("FINGERPRINT", f"Security level: {finger.security_level}")
                self.log_data("FINGERPRINT", f"Template count: {finger.template_count}")
            
            self.fingerprint_active = True
            print("👆 Place finger on sensor to capture raw data...")
            
            scan_count = 0
            while self.running and scan_count < 10:  # Limit to 10 scans for demo
                try:
                    self.log_data("FINGERPRINT", f"Scan attempt #{scan_count + 1}")
                    
                    # Wait for finger placement
                    self.log_data("FINGERPRINT", "Waiting for finger placement...")
                    
                    # Get raw image data
                    result = finger.get_image()
                    if result == adafruit_fingerprint.OK:
                        self.log_data("FINGERPRINT", "✅ Image captured successfully")
                        
                        # Convert to template
                        if finger.image_2_tz(1) == adafruit_fingerprint.OK:
                            self.log_data("FINGERPRINT", "✅ Template conversion successful")
                            
                            # Attempt search
                            search_result = finger.finger_search()
                            if search_result == adafruit_fingerprint.OK:
                                self.log_data("FINGERPRINT", f"✅ MATCH FOUND - ID: {finger.finger_id}, Confidence: {finger.confidence}")
                            else:
                                self.log_data("FINGERPRINT", "❌ No match found in database")
                        else:
                            self.log_data("FINGERPRINT", "❌ Template conversion failed")
                    elif result == adafruit_fingerprint.NOFINGER:
                        self.log_data("FINGERPRINT", "No finger detected")
                    elif result == adafruit_fingerprint.IMAGEFAIL:
                        self.log_data("FINGERPRINT", "❌ Image capture failed")
                    else:
                        self.log_data("FINGERPRINT", f"❌ Error code: {result}")
                    
                    scan_count += 1
                    time.sleep(2)  # Wait between scans
                    
                except Exception as e:
                    self.log_data("FINGERPRINT", f"❌ Exception: {str(e)}", "ERROR")
                    
        except Exception as e:
            self.log_data("FINGERPRINT", f"❌ Initialization failed: {str(e)}", "ERROR")
        finally:
            self.fingerprint_active = False
            self.log_data("FINGERPRINT", "Sensor disconnected")

    def camera_raw_data(self):
        """Collect raw data from camera module"""
        print("\n📷 CAMERA MODULE - Raw Data Collection")
        print("-" * 50)
        
        try:
            # Load encodings
            script_dir = os.path.dirname(os.path.abspath(__file__))
            encodings_path = os.path.join(script_dir, "face_recognition_folder", "encodings.pickle")
            
            self.log_data("CAMERA", f"Loading encodings from: {encodings_path}")
            
            if os.path.exists(encodings_path):
                with open(encodings_path, "rb") as f:
                    data = pickle.loads(f.read())
                known_face_encodings = data["encodings"]
                known_face_names = data["names"]
                self.log_data("CAMERA", f"✅ Loaded {len(known_face_encodings)} face encodings")
                self.log_data("CAMERA", f"Known names: {known_face_names}")
            else:
                self.log_data("CAMERA", "❌ Encodings file not found", "ERROR")
                return
            
            # Initialize camera
            self.log_data("CAMERA", "Initializing Picamera2...")
            picam2 = Picamera2()
            picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
            picam2.start()
            self.log_data("CAMERA", "✅ Camera initialized (640x480 XRGB8888)")
            
            self.camera_active = True
            
            frame_count = 0
            detection_count = 0
            
            while self.running and frame_count < 50:  # Limit frames for demo
                try:
                    # Capture frame
                    frame = picam2.capture_array()
                    frame_count += 1
                    
                    if frame_count % 10 == 0:  # Log every 10th frame
                        self.log_data("CAMERA", f"Frame #{frame_count} captured - Shape: {frame.shape}")
                    
                    # Convert color format
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Resize for faster processing
                    small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
                    
                    # Find face locations
                    face_locations = face_recognition.face_locations(small_frame)
                    
                    if face_locations:
                        detection_count += 1
                        self.log_data("CAMERA", f"✅ {len(face_locations)} face(s) detected at frame #{frame_count}")
                        
                        # Get face encodings
                        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
                        
                        for i, face_encoding in enumerate(face_encodings):
                            self.log_data("CAMERA", f"Face #{i+1} encoding shape: {face_encoding.shape}")
                            
                            # Compare with known faces
                            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
                            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                            
                            if True in matches:
                                best_match_index = np.argmin(face_distances)
                                if matches[best_match_index]:
                                    name = known_face_names[best_match_index]
                                    confidence = 1 - face_distances[best_match_index]
                                    self.log_data("CAMERA", f"✅ FACE RECOGNIZED: {name}, Confidence: {confidence:.3f}")
                                else:
                                    self.log_data("CAMERA", "❌ Face not recognized")
                            else:
                                self.log_data("CAMERA", "❌ No matching face found")
                    else:
                        if frame_count % 20 == 0:  # Log every 20th frame when no face
                            self.log_data("CAMERA", f"No faces detected in frame #{frame_count}")
                    
                    time.sleep(0.1)  # Small delay
                    
                except Exception as e:
                    self.log_data("CAMERA", f"❌ Frame processing error: {str(e)}", "ERROR")
            
            self.log_data("CAMERA", f"📊 Total frames: {frame_count}, Face detections: {detection_count}")
            
        except Exception as e:
            self.log_data("CAMERA", f"❌ Camera initialization failed: {str(e)}", "ERROR")
        finally:
            try:
                picam2.stop()
                picam2.close()
            except:
                pass
            self.camera_active = False
            self.log_data("CAMERA", "Camera released")

    def keypad_raw_data(self):
        """Collect raw data from matrix keypad"""
        print("\n⌨️  MATRIX KEYPAD - Raw Data Collection")
        print("-" * 50)
        
        try:
            # Keypad configuration
            rows_pins = [5, 6, 13, 19]  # BCM pins
            cols_pins = [12, 16, 20, 21]  # BCM pins
            keys = ["1", "2", "3", "A",
                   "4", "5", "6", "B", 
                   "7", "8", "9", "C",
                   "*", "0", "#", "D"]
            
            self.log_data("KEYPAD", f"Initializing 4x4 matrix keypad")
            self.log_data("KEYPAD", f"Row pins (BCM): {rows_pins}")
            self.log_data("KEYPAD", f"Column pins (BCM): {cols_pins}")
            
            # Initialize GPIO
            rows = [DigitalOutputDevice(pin) for pin in rows_pins]
            cols = [Button(pin, pull_up=False) for pin in cols_pins]
            
            self.log_data("KEYPAD", "✅ GPIO pins initialized")
            self.keypad_active = True
            
            print("🔤 Press keys on the keypad to see raw input data...")
            
            last_pressed = []
            key_count = 0
            
            while self.running and key_count < 20:  # Limit to 20 keypresses for demo
                try:
                    pressed_keys = []
                    
                    # Set all rows low initially
                    for row in rows:
                        row.off()
                    
                    # Scan keypad matrix
                    for i, row in enumerate(rows):
                        row.on()  # Activate current row
                        time.sleep(0.001)  # Small stabilization delay
                        
                        for j, col in enumerate(cols):
                            if col.is_pressed:
                                key_index = i * len(cols) + j
                                pressed_keys.append(keys[key_index])
                                
                        row.off()  # Deactivate current row
                    
                    # Log new keypresses
                    if pressed_keys and pressed_keys != last_pressed:
                        for key in pressed_keys:
                            key_count += 1
                            self.log_data("KEYPAD", f"✅ KEY PRESSED: '{key}' (Raw matrix position: Row {(keys.index(key)//4)}, Col {(keys.index(key)%4)})")
                            
                            # Special key actions
                            if key == "*":
                                self.log_data("KEYPAD", "🔄 CLEAR key detected")
                            elif key == "#":
                                self.log_data("KEYPAD", "✔️ SUBMIT key detected")
                            elif key in "ABCD":
                                self.log_data("KEYPAD", f"🔧 FUNCTION key detected: {key}")
                            else:
                                self.log_data("KEYPAD", f"🔢 NUMERIC key detected: {key}")
                        
                        last_pressed = pressed_keys
                    
                    time.sleep(0.05)  # Scan rate: ~20Hz
                    
                except Exception as e:
                    self.log_data("KEYPAD", f"❌ Scan error: {str(e)}", "ERROR")
            
            self.log_data("KEYPAD", f"📊 Total keypresses recorded: {key_count}")
            
        except Exception as e:
            self.log_data("KEYPAD", f"❌ Keypad initialization failed: {str(e)}", "ERROR")
        finally:
            try:
                for row in rows:
                    row.close()
                for col in cols:
                    col.close()
            except:
                pass
            self.keypad_active = False
            self.log_data("KEYPAD", "GPIO pins released")

    def run_sensor_test(self, sensor_choice):
        """Run specific sensor test"""
        if sensor_choice == "1":
            self.fingerprint_raw_data()
        elif sensor_choice == "2":
            self.camera_raw_data()
        elif sensor_choice == "3":
            self.keypad_raw_data()
        elif sensor_choice == "4":
            # Run all sensors sequentially
            print("\n🚀 RUNNING ALL SENSORS SEQUENTIALLY")
            print("=" * 60)
            
            self.fingerprint_raw_data()
            time.sleep(2)
            self.camera_raw_data()
            time.sleep(2)
            self.keypad_raw_data()

    def display_menu(self):
        """Display sensor selection menu"""
        print("\n" + "=" * 60)
        print("🎯 SELECT SENSOR FOR RAW DATA COLLECTION")
        print("=" * 60)
        print("1. 🔐 Fingerprint Sensor (R307)")
        print("2. 📷 Camera Module (Face Recognition)")
        print("3. ⌨️  4x4 Matrix Keypad")
        print("4. 🚀 All Sensors (Sequential)")
        print("5. ❌ Exit")
        print("=" * 60)

def main():
    """Main function"""
    collector = RawDataCollector()
    
    try:
        while True:
            collector.display_menu()
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == "5":
                print("\n👋 Exiting raw data collector...")
                break
            elif choice in ["1", "2", "3", "4"]:
                print(f"\n🎬 RECORDING RAW DATA - Sensor Choice: {choice}")
                print("📹 Start recording your screen now!")
                print("⏱️  Waiting 3 seconds before starting...")
                
                for i in range(3, 0, -1):
                    print(f"Starting in {i}...")
                    time.sleep(1)
                
                collector.run_sensor_test(choice)
                
                print("\n✅ RAW DATA COLLECTION COMPLETE")
                print("🛑 You can stop recording now!")
                
                continue_choice = input("\nCollect more data? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    break
            else:
                print("❌ Invalid choice. Please select 1-5.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
    finally:
        collector.running = False
        print("\n🧹 Cleaning up...")
        print("📊 Raw data collection session ended.")
        print(f"⏰ End Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
