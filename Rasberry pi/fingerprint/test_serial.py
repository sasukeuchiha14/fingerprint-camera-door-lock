import serial

for port in ["/dev/ttyAMA0", "/dev/ttyAMA10", "/dev/serial0", "/dev/serial1"]:
    try:
        print(f"Trying {port}...")
        ser = serial.Serial(port, baudrate=57600, timeout=1)
        ser.write(b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x03\x01\x00\x05')
        response = ser.read(12)
        print(f"Response from {port}: {response}")
    except Exception as e:
        print(f"Error on {port}: {e}")
