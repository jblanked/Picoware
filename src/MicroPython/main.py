import time
from ILI9341 import ILI9341
from EasySD import EasySD
from PicoKeyboard import PicoKeyboard

display = ILI9341()
display.println("Picoware Screen test")
display.draw_circle(160, 160, 30)

time.sleep(1)

sd = EasySD()
sd.mount()  # mount SD card
print(sd.read("picoware/wifi/settings.json"))
print(sd.listdir("/sd"))
# unmount SD card (if you dont do this, Thonny will recognize it as mounted)
# and then you'll get an error trying to mount it again
sd.unmount()

kb = PicoKeyboard()

# Basic while loop to read keyboard input for 10 seconds
start_time = time.time()
timeout = 10  # 10 seconds

print("Waiting for keyboard input for 10 seconds...")
while time.time() - start_time < timeout:
    if kb.keyCount() > 0:  # Check if there are keys in the buffer
        key_event = kb.keyEvent()  # Get the key event
        if key_event:
            state = key_event[0]  # Key state (press/release)
            key = key_event[1]  # Key code
            if state == 1:
                print(f"Key pressed: {chr(key) if 32 <= key <= 126 else key}")
    time.sleep(0.1)  # Small delay to prevent excessive polling

print("Input timeout reached.")
