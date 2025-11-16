// original author: Waveshare Team, translated from https://files.waveshare.com/wiki/RP2350-Touch-AMOLED-1.43/RP2350-Touch-AMOLED-1.43-Demo-V2.0.zip
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/adc.h"

#define BAT_ADC_PIN (26)
#define BATTERY_ADC_SIZE 9

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