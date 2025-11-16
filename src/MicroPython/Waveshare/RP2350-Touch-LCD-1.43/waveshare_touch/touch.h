// original author: Waveshare Team, translated from https://files.waveshare.com/wiki/RP2350-Touch-AMOLED-1.43/RP2350-Touch-AMOLED-1.43-Demo-V2.0.zip
// Ported from CST816S (1.28 LCD) to FT6146 (1.49 LCD)
// FT6146 driver: Capacitive touch panel controller
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"

// FT6146 chip configuration for 1.49" LCD
#define TOUCH_ADDR (0x38)
#define SENSOR_I2C_PORT (i2c1)
#define TOUCH_SDA_PIN (6)
#define TOUCH_SCL_PIN (7)
#define TOUCH_INT_PIN (20)
#define TOUCH_RST_PIN (17)
#define TOUCH_BAUDRATE (400000)

// FT6146 Register definitions
#define TOUCH_REG_NUM_TOUCHES 0x02

typedef struct
{
	uint16_t x;
	uint16_t y;
} TouchVector;

#ifdef __cplusplus
extern "C"
{
#endif

	// void touch_callback(uint gpio, uint32_t events)

	TouchVector touch_get_point();
	void touch_init(void);

	uint8_t touch_read(uint8_t reg);
	void touch_read_data(bool force);
	void touch_reset();
	void touch_reset_state();
	void touch_set_callback(gpio_irq_callback_t callback);
	void touch_write(uint8_t reg, uint8_t value);

#ifdef __cplusplus
}
#endif