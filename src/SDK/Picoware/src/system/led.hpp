#pragma once
#include <cstdint>

class LED
{
public:
    LED();
    ~LED();

    void blink(uint32_t period = 250) const noexcept; // Blink the LED on/off with the given period (ms).
    void off() const noexcept;                        // Turn the LED fully off.
    void on() const noexcept;                         // Turn the LED fully on.
};
