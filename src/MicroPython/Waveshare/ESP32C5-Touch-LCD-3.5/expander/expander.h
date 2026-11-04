/*
 * I/O expander for the Waveshare ESP32-C5-Touch-LCD-3.5 (I2C 0x24).
 *
 * It owns the FT6336 reset (EXIO0), the ST7796 reset (EXIO1), the panel
 * power / backlight enable (EXIO5) and the backlight PWM.
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C"
{
#endif

    // Power the panel and pulse both resets. Runs once: a second LCD reset
    // after the ST7796 is initialized blanks the screen, so repeat calls are a
    // no-op that return the first result.
    esp_err_t expander_init(void);
    bool expander_ready(void);

    // Backlight PWM duty, 0 (off) to 255 (full).
    esp_err_t expander_set_backlight(uint8_t duty);

#ifdef __cplusplus
}
#endif
