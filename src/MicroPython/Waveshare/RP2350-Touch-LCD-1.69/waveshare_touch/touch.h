// original author: Waveshare Team, translated from https://github.com/waveshareteam/RP2040-Touch-LCD-1.28/blob/main/c/lib/Touch/CST816S.h
// CST816 driver: High performance self-capacitance touch chip
// Driven in point mode here: the 1.69" panel is rectangular, so Picoware maps
// touch coordinates to buttons instead of relying on the chip's gestures.
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "hardware/sync.h"

#define TOUCH_ADDR (0x15)
#define SENSOR_I2C_PORT (i2c1)
#define TOUCH_SDA_PIN (6)
#define TOUCH_SCL_PIN (7)
#define TOUCH_INT_PIN (21)
#define TOUCH_RST_PIN (22)
#define TOUCH_BAUDRATE (400000)

typedef enum
{

	TOUCH_GESTURE_ID = 0x01,
	TOUCH_FINGER_NUM,
	TOUCH_X_POSITION_H,
	TOUCH_X_POSITION_L,
	TOUCH_Y_POSITION_H,
	TOUCH_Y_POSITION_L,

	TOUCH_CHIP_ID = 0xA7,
	TOUCH_PROJ_ID,
	TOUCH_FW_VERSION,
	TOUCH_MOTION_MASK,

	TOUCH_BPC0H = 0xB0,
	TOUCH_BPC0L,
	TOUCH_BPC1H,
	TOUCH_BPC1L,

	TOUCH_IRQ_PLUSE_WIDTH = 0xED,
	TOUCH_NOR_SCAN_PER,
	TOUCH_MOTION_SL_ANGLE,
	TOUCH_LP_SCAN_RAW1H = 0XF0,
	TOUCH_LP_SCAN_RAW1L,
	TOUCH_LP_SCAN_RAW2H,
	TOUCH_LP_SCAN_RAW2L,
	TOUCH_LP_AUTO_WAKE_TIME,
	TOUCH_LP_SCAN_TH,
	TOUCH_LP_SCAN_WIN,
	TOUCH_LP_SCAN_FREQ,
	TOUCH_LP_SCAN_IDAC,
	TOUCH_AUTO_SLEEP_TIME,
	TOUCH_IRQ_CTL,
	TOUCH_AUTO_RESET,
	TOUCH_LONG_PRESS_TIME,
	TOUCH_IO_CTL,
	TOUCH_DIS_AUTO_SLEEP
} TOUCH_Register;

typedef struct
{
	uint16_t x;
	uint16_t y;
} TouchVector;

#ifdef __cplusplus
extern "C"
{
#endif

	TouchVector touch_get_point();
	bool touch_init(void);

	uint8_t touch_read(uint8_t reg);
	void touch_read_data(bool force);
	void touch_reset();
	void touch_reset_state();
	void touch_set_callback(gpio_irq_callback_t callback);
	void touch_write(uint8_t reg, uint8_t value);

#ifdef __cplusplus
}
#endif
