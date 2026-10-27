#pragma once

#include "driver/gpio.h"

// Waveshare ESP32-C5-Touch-LCD-3.5 (ESP32-C5HR8, 8 MB PSRAM, 32 MB flash).
//
// GPIO 13/14 are the native USB D-/D+ and GPIO 16/17 are the internal
// flash/PSRAM lines; none of them may be driven.

// LCD (ST7796, 320x480 portrait). The panel and the SD card share SPI2_HOST
// and differ only by chip select. Reset and backlight are not GPIOs: they hang
// off the I/O expander (see expander/expander.h).
#define WS_C5_35_LCD_HOST SPI2_HOST
#define WS_C5_35_LCD_DC_GPIO GPIO_NUM_5
#define WS_C5_35_LCD_MOSI_GPIO GPIO_NUM_7
#define WS_C5_35_LCD_SCLK_GPIO GPIO_NUM_6
#define WS_C5_35_LCD_CS_GPIO GPIO_NUM_8

// Only the SD card uses MISO, but whichever driver initializes the bus fixes
// its pin map, so the LCD must claim it too.
#define WS_C5_35_LCD_MISO_GPIO GPIO_NUM_2

// Shared I2C bus: I/O expander, touch, PMU, codec, IMU, RTC, GPS.
#define WS_C5_35_I2C_PORT I2C_NUM_0
#define WS_C5_35_I2C_SDA_GPIO GPIO_NUM_27
#define WS_C5_35_I2C_SCL_GPIO GPIO_NUM_26
#define WS_C5_35_I2C_FREQ_HZ 400000

// I/O expander (a CH32V006 running Waveshare firmware, not a datasheet part).
#define WS_C5_35_EXPANDER_I2C_ADDR 0x24
#define WS_C5_35_EXIO_TOUCH_RST 0 // FT6336 reset, active low
#define WS_C5_35_EXIO_LCD_RST 1   // ST7796 reset, active low
#define WS_C5_35_EXIO_POWER 5     // panel power / backlight enable

// Touch (FT6336U capacitive). TP_INT has an external 10K pull-up and holds low
// while a finger is down (with G_MODE = 0).
#define WS_C5_35_TOUCH_I2C_ADDR 0x38
#define WS_C5_35_TOUCH_INT_GPIO GPIO_NUM_3

// Battery (AXP2101 PMU fuel gauge)
#define WS_C5_35_BATTERY_I2C_ADDR 0x34

// SD card (SDSPI, shares the LCD's bus). sdcard.c mounts via machine.SDCard
// slot 2, which is SPI2_HOST on this chip.
#define WS_C5_35_SD_HOST WS_C5_35_LCD_HOST
#define WS_C5_35_SD_CS_GPIO GPIO_NUM_9
#define WS_C5_35_SD_MOSI_GPIO WS_C5_35_LCD_MOSI_GPIO
#define WS_C5_35_SD_SCLK_GPIO WS_C5_35_LCD_SCLK_GPIO
#define WS_C5_35_SD_MISO_GPIO WS_C5_35_LCD_MISO_GPIO

// No addressable LED: GPIO 27 is I2C SDA on this board.
