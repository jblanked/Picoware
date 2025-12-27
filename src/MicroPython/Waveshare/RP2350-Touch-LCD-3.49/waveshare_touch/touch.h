// original author: Waveshare Team, translated from https://files.waveshare.com/wiki/RP2350-Touch-LCD-3.49/RP2350-Touch-LCD-3.49-LVGL.zip
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"

#define LCD_HEIGHT 640
#define LCD_WIDTH 172

#define TOUCH_ADDR (0x3B)
#define I2C_PORT i2c1
#define TOUCH_I2C_PORT i2c0

#define TOUCH_SDA_PIN (32)
#define TOUCH_SCL_PIN (33)
#define TOUCH_INT_PIN (11)

#define DEV_SDA_PIN 6
#define DEV_SCL_PIN 7

#define TOUCH_BAUDRATE (400000)

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
	void touch_read_data(void);
	void touch_reset(void);
	void touch_reset_state(void);
	void touch_set_callback(gpio_irq_callback_t callback);
	void touch_write(uint8_t reg, uint8_t value);

#ifdef __cplusplus
}
#endif