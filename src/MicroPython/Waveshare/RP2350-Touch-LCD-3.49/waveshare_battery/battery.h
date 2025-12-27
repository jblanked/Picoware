// original author: Waveshare Team, translated from https://files.waveshare.com/wiki/RP2350-Touch-LCD-3.49/RP2350-Touch-LCD-3.49-LVGL.zip
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/adc.h"

#define BAT_ADC_PIN (40)
#define BAR_CHANNEL (0)

#ifdef __cplusplus
extern "C"
{
#endif

    uint8_t battery_get_percentage();
    float battery_get_voltage();
    void battery_init(void);
    uint16_t battery_read(void);

#ifdef __cplusplus
}
#endif