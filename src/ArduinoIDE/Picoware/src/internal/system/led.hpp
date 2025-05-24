#pragma once
#include <Arduino.h>
namespace Picoware
{
    class LED
    {
    public:
        /// Create an LED on the given pin (defaults to LED_BUILTIN) and set it as OUTPUT.
        explicit LED(uint8_t pin = LED_BUILTIN)
            : _pin(pin)
        {
            // pin 25 is the LED for PicoCalc
            pinMode(_pin, OUTPUT);
        }

        /// Blink the LED on/off with the given period (ms).
        void blink(uint32_t period = 250) const noexcept
        {
            on();
            delay(period);
            off();
            delay(period);
        }

        /// “Startup” sequence: three quick blinks.
        void start() const noexcept
        {
            blink();
            blink();
            blink();
        }

        /// Turn the LED fully on.
        void on() const noexcept
        {
            digitalWrite(_pin, HIGH);
        }

        /// Turn the LED fully off.
        void off() const noexcept
        {
            digitalWrite(_pin, LOW);
        }

    private:
        uint8_t _pin;
    };
}
