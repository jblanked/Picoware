class LED:
    """Class to control an LED on a Raspberry Pi Pico device."""

    def __init__(self, pin: int = -1):
        from machine import Pin

        self.led = Pin(pin if pin != -1 else "LED", Pin.OUT)

    def blink(self, duration=0.5):
        """Blink the LED on and off for a specified duration."""
        from time import sleep

        self.on()
        sleep(duration)
        self.off()
        sleep(duration)

    def off(self):
        """Turn the LED off."""
        self.led.off()

    def on(self):
        """Turn the LED on."""
        self.led.on()

    def toggle(self):
        """Toggle the LED state."""
        self.led.toggle()
