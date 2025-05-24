from time import sleep
from board import LED as PicoLED
from digitalio import Direction, DigitalInOut


class LED:
    """Class to control an LED on a Raspberry Pi Pico device."""

    def __init__(self, pin=PicoLED):
        self.led = DigitalInOut(pin)
        self.led.direction = Direction.OUTPUT

    def on(self):
        """Turn the LED on."""
        self.led.value = True

    def off(self):
        """Turn the LED off."""
        self.led.value = False

    def blink(self, duration=0.5):
        """Blink the LED on and off for a specified duration."""
        self.on()
        sleep(duration)
        self.off()
        sleep(duration)
