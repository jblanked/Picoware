from picoware.system.drivers.espflasher import ESPFlasher
from machine import Pin
from picoware.system.uart import UART
from picoware.system.view_manager import ViewManager
from gc import mem_free, collect
from flipper_battery import init, shutdown

def clean(num):
    collect()
    print(f"mem_free({mem_free()})-{num}")

def main():
    # devboard docs: https://developer.flipper.net/flipperzero/doxygen/dev_board.html
    clean(1)
    #init()
    #vm = ViewManager()
    clean(2)
    uart = UART()
    reset = Pin(Pin.cpu.B2, Pin.OUT) # on devboard, its the 6th pin from the left (RTS/EN)
    gpio0 = Pin(Pin.cpu.C3, Pin.OUT) # on devboard, its the 7th pin from the left (DTR/BOOT)
    clean(3)

    path = "/sd/flipper_http_merged.bin"

    esp = ESPFlasher(reset, gpio0, uart, chip="esp32s2")
    clean(4)
    # Enter bootloader download mode, at 115200
    attempts = 10
    esp.bootloader(attempts)
    clean(5)

    # Can now change to higher/lower baudrate
    esp.set_baudrate(460800)
    # Must call this first before any flash functions.
    esp.flash_attach()
    clean(6)
    # Read flash size
    size = esp.flash_read_size()
    # Configure flash parameters.
    esp.flash_config(size)
    clean(7)
    # Write firmware image from internal storage.
    esp.flash_write_file(path, blksize=0x400, progress_interval=128)
    clean(8)
    # Resets the ESP32 chip.
    esp.reboot()
    clean(9)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
    clean(11)