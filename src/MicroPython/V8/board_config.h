#pragma once

#include "driver/gpio.h"

// LCD (ILI9341, 240x320 portrait). The panel, the SD card and the XPT2046 touch
// controller all share SPI2_HOST and differ only by chip select.
#define V8_LCD_HOST SPI2_HOST
#define V8_LCD_BL_GPIO GPIO_NUM_8
#define V8_LCD_RST_GPIO GPIO_NUM_NC // reset tied to EN in hardware, no GPIO
#define V8_LCD_DC_GPIO GPIO_NUM_24
#define V8_LCD_MOSI_GPIO GPIO_NUM_7
#define V8_LCD_SCLK_GPIO GPIO_NUM_6
#define V8_LCD_CS_GPIO GPIO_NUM_23

// MISO is used by the SD card and the touch controller, so the LCD must claim
// it too when it initializes the shared bus.
#define V8_LCD_MISO_GPIO GPIO_NUM_2

// Battery fuel gauge I2C bus (touch is on SPI, not here)
#define V8_I2C_PORT I2C_NUM_0
#define V8_I2C_SDA_GPIO GPIO_NUM_5
#define V8_I2C_SCL_GPIO GPIO_NUM_4
#define V8_I2C_FREQ_HZ 400000

// Battery fuel gauge (MAX17048)
#define V8_BATTERY_I2C_ADDR 0x36

// Touch (XPT2046 resistive, on the shared SPI bus)
#define V8_TOUCH_HOST V8_LCD_HOST
#define V8_TOUCH_CS_GPIO GPIO_NUM_3
#define V8_TOUCH_IRQ_GPIO GPIO_NUM_NC // IRQ not wired; touch is polled

// SD card (SDSPI, shares the LCD's bus). sdcard.c mounts via machine.SDCard
// slot 2, which is SPI2_HOST on this chip.
#define V8_SD_HOST V8_LCD_HOST
#define V8_SD_CS_GPIO GPIO_NUM_10
#define V8_SD_MOSI_GPIO V8_LCD_MOSI_GPIO
#define V8_SD_SCLK_GPIO V8_LCD_SCLK_GPIO
#define V8_SD_MISO_GPIO V8_LCD_MISO_GPIO

// Addressable status LED
#define V8_RGB_LED_GPIO GPIO_NUM_27
