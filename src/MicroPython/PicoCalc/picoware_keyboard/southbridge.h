/*
Author: Blair Leduc
License: MIT License
Source: https://github.com/BlairLeduc/picocalc-text-starter
*/

#pragma once

#include "pico/stdlib.h"

#define SB_I2C (i2c1) // I2C interface for the south bridge

// Raspberry Pi Pico board GPIO pins
#define SB_SDA (6)
#define SB_SCL (7)

// Keyboard interface definitions
#define SB_BAUDRATE (10000)
#define SB_ADDR (0x1F)
#define SB_I2C_TIMEOUT_US (10000)

// Keyboard register definitions
#define SB_REG_KEY (0x04) // *key status
#define SB_REG_BKL (0x05) // *backlight
#define SB_REG_RST (0x08) // *reset
#define SB_REG_FIF (0x09) // *fifo
#define SB_REG_BK2 (0x0A) // *keyboard backlight
#define SB_REG_BAT (0x0B) // *battery
#define SB_REG_OFF (0x0E) // *power off

#define SB_WRITE (0x80) // write to register

#ifdef __cplusplus
extern "C"
{
#endif

    // Function prototypes
    void sb_deinit(void);
    void sb_init(void);
    bool sb_available(void);

    uint16_t sb_read_keyboard(void);
    uint16_t sb_read_keyboard_state(void);
    uint8_t sb_read_battery(void);
    uint8_t sb_read_lcd_backlight(void);
    uint8_t sb_write_lcd_backlight(uint8_t brightness);
    uint8_t sb_read_keyboard_backlight(void);
    uint8_t sb_write_keyboard_backlight(uint8_t brightness);
    bool sb_is_power_off_supported(void);
    bool sb_write_power_off_delay(uint8_t delay_seconds);
    bool sb_reset(uint8_t delay_seconds);

#ifdef __cplusplus
}
#endif
