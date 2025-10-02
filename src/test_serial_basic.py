import serial
import time

# Replace with your actual serial port
PORT = "/dev/cu.usbmodem11303"
BAUD = 9600

try:
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        print(f"✅ Connected to {PORT} at {BAUD} baud.")
        time.sleep(2)  # Allow time for STM32 to reboot if needed

        while True:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"📄 {line}")
            else:
                # Optional: indicate waiting
                time.sleep(0.1)
except serial.SerialException as e:
    print(f"❌ SerialException: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
