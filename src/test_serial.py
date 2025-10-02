import serial

for port in ["/dev/tty.debug-console", "/dev/tty.usbmodem11303"]:
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"✅ Opened OK on {port}")
        ser.close()
        break
    except Exception as e:
        print(f"❌ Could not open {port}: {e}")
