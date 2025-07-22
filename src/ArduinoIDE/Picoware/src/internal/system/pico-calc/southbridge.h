#pragma once

#include "pico/stdlib.h"

#define SB_I2C              (i2c1)      // I2C interface for the south bridge

// Raspberry Pi Pico board GPIO pins
#define SB_SDA              (6)
#define SB_SCL              (7)


// Keyboard interface definitions
#define SB_BAUDRATE       (10000)
#define SB_ADDR            (0x1F)


// Keyboard register definitions
#define SB_REG_VER         (0x01)      // fw version
#define SB_REG_CFG         (0x02)      // config
#define SB_REG_INT         (0x03)      // interrupt status
#define SB_REG_KEY         (0x04)      // key status
#define SB_REG_BKL         (0x05)      // backlight
#define SB_REG_DEB         (0x06)      // debounce cfg
#define SB_REG_FRQ         (0x07)      // poll freq cfg
#define SB_REG_RST         (0x08)      // reset
#define SB_REG_FIF         (0x09)      // fifo
#define SB_REG_BK2         (0x0A)      // keyboard backlight
#define SB_REG_BAT         (0x0b)      // battery

#ifdef __cplusplus
extern "C"
{
#endif

// Function prototypes
bool sb_available();
void sb_acquire();
void sb_release();
void sb_write(const uint8_t *src, size_t len);
void sb_read(uint8_t *dst, size_t len);
void sb_init();

uint16_t sb_read_keyboard(void);
uint8_t sb_read_battery(void);
uint8_t sb_read_lcd_backlight(void);
void sb_write_lcd_backlight(uint8_t brightness);
uint8_t sb_read_keyboard_backlight(void);
void sb_write_keyboard_backlight(uint8_t brightness);

#ifdef __cplusplus
}
#endif
