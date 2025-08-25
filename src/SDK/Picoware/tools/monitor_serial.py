#!/usr/bin/env python3
import serial
import sys
import time

try:
    ser = serial.Serial("/dev/cu.usbmodem101", 115200, timeout=1)
    print("Connected to serial port. Press Ctrl+C to exit.")
    print("=" * 50)

    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode("utf-8", errors="ignore").strip()
            if data:
                print(f"{time.strftime('%H:%M:%S.%f')[:-3]} -> {data}")
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nDisconnected")
except Exception as e:
    print(f"Error: {e}")
finally:
    if "ser" in locals():
        ser.close()
