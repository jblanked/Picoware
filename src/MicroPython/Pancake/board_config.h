#pragma once

#include "driver/gpio.h"

// LCD (ST7796, 320x480 portrait). The panel and the SD card share SPI2_HOST
// and differ only by chip select.
#define PANCAKE_LCD_HOST SPI2_HOST
#define PANCAKE_LCD_BL_GPIO GPIO_NUM_26
#define PANCAKE_LCD_RST_GPIO GPIO_NUM_2
#define PANCAKE_LCD_DC_GPIO GPIO_NUM_3
#define PANCAKE_LCD_MOSI_GPIO GPIO_NUM_24
#define PANCAKE_LCD_SCLK_GPIO GPIO_NUM_23
#define PANCAKE_LCD_CS_GPIO GPIO_NUM_5

// Only the SD card uses MISO, but whichever driver initializes the bus fixes
// its pin map, so the LCD must claim it too.
#define PANCAKE_LCD_MISO_GPIO GPIO_NUM_4

// Touch + fuel gauge I2C bus
#define PANCAKE_I2C_PORT I2C_NUM_0
#define PANCAKE_I2C_SDA_GPIO GPIO_NUM_9
#define PANCAKE_I2C_SCL_GPIO GPIO_NUM_10
#define PANCAKE_I2C_FREQ_HZ 400000

// Touch (FT6336U capacitive)
#define PANCAKE_TOUCH_I2C_ADDR 0x38
#define PANCAKE_TOUCH_RST_GPIO GPIO_NUM_8

// Battery fuel gauge (MAX17048)
#define PANCAKE_BATTERY_I2C_ADDR 0x36

// SD card (SDSPI, shares the LCD's bus). sdcard.c mounts via machine.SDCard
// slot 2, which is SPI2_HOST on this chip.
#define PANCAKE_SD_HOST PANCAKE_LCD_HOST
#define PANCAKE_SD_CS_GPIO GPIO_NUM_7
#define PANCAKE_SD_MOSI_GPIO PANCAKE_LCD_MOSI_GPIO
#define PANCAKE_SD_SCLK_GPIO PANCAKE_LCD_SCLK_GPIO
#define PANCAKE_SD_MISO_GPIO PANCAKE_LCD_MISO_GPIO

// Addressable status LED
#define PANCAKE_RGB_LED_GPIO GPIO_NUM_27
