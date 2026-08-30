from gc import collect

from picoware.system.ducky import Ducky
from picoware.system.usb import USBKeyboard
from picoware.system.view_manager import ViewManager


view_manager = ViewManager()
usb_keyboard = USBKeyboard(
    manufacturer="MicroPython",
    product="Picoware Ducky Test",
    serial="000003",
)
ducky = Ducky(usb_keyboard, storage=view_manager.storage)
usb_ready = False
try:
    usb_keyboard.init()
    usb_ready = True
    ducky.run("STRING Picoware Ducky run test")
    ducky.exec("demo_macos.txt") # from https://github.com/flipperdevices/flipperzero-firmware/blob/dev/applications/main/bad_usb/resources/badusb/demo_macos.txt
finally:
    if usb_ready:
        usb_keyboard.release()
    del ducky, usb_keyboard, view_manager
    collect()