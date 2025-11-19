// original author: Waveshare Team, translated from https://github.com/waveshareteam/RP2040-Touch-LCD-1.28/blob/main/c/lib/Config/DEV_Config.h
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/adc.h"

#define BAT_ADC_PIN (29)
#define BAR_CHANNEL (3)

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