"""LED - On-board LED control."""

class LED:
    """Class to control an LED on a Raspberry Pi Pico device.
    
    Attributes:
        led (machine.Pin): The Pin object representing the LED.
    """

    def __init__(self, pin: int = -1):
        """Initialize the LED on the default or given pin.

        Args:
            pin (int): Pin number to use, or -1 for the board LED. Defaults to -1.
        """
        from machine import Pin

        self.led = Pin(pin if pin != -1 else "LED", Pin.OUT) 

    def __del__(self):
        """Release the LED pin."""
        del self.led
        self.led = None

    def blink(self, duration=0.5):
        """Blink the LED on and off for a specified duration.

        Args:
            duration (float): How long the LED stays on or off in seconds. Defaults to 0.5.
        """
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
