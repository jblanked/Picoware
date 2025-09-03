import time
from picoware.gui.draw import Draw
from picoware.system.colors import TFT_BLUE, TFT_RED
from picoware.system.vector import Vector
from picoware.system.drivers.EasySD import EasySD
from picoware.system.drivers.PicoKeyboard import PicoKeyboard

display = Draw()
display.println("Picoware Screen test")
display.circle(Vector(160, 160), 30)
display.line(Vector(150, 100), Vector(50, 0))
display.rect(Vector(30, 30), Vector(100, 100), TFT_BLUE)
display.fill_rectangle(Vector(30, 210), Vector(100, 100), TFT_RED)


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
