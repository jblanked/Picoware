// original author: Waveshare Team, translated from https://github.com/waveshareteam/RP2040-Touch-LCD-1.28/blob/main/c/lib/LCD/LCD_1in28.h
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "hardware/pwm.h"

#include "../../../font/font_mp.h"

#define LCD_HEIGHT 240
#define LCD_WIDTH 240

extern uint8_t framebuffer[LCD_WIDTH * LCD_HEIGHT]; // Framebuffer for 8-bit indexed color

#define LCD_SPI_PORT (spi1) // SPI interface for the LCD display

#define LCD_BAUDRATE (40000000) // 40MHz

#define LCD_DC_PIN (8)    // Data/Command control pin (D/CX)
#define LCD_CS_PIN (9)    // Chip Select pin (CSX)
#define LCD_CLK_PIN (10)  // serial clock pin (SCL)
#define LCD_MOSI_PIN (11) // Master Out Slave In pin (SDA)
#define LCD_RST_PIN (13)  // reset pin
#define LCD_BL_PIN (25)   // backlight control pin

#define LCD_DEFAULT_BRIGHTNESS 30 // Default backlight brightness (0-100)

// RGB565 Color definitions
#ifndef COLOR_WHITE
#define COLOR_WHITE 0xFFFF
#endif

#ifndef COLOR_BLACK
#define COLOR_BLACK 0x0000
#endif

#ifndef COLOR_BLUE
#define COLOR_BLUE 0x001F
#endif

#ifndef COLOR_CYAN
#define COLOR_CYAN 0x07FF
#endif

#ifndef COLOR_RED
#define COLOR_RED 0xF800
#endif

#ifndef COLOR_LIGHTGREY
#define COLOR_LIGHTGREY 0xD69A
#endif

#ifndef COLOR_DARKGREY
#define COLOR_DARKGREY 0x7BEF
#endif

#ifndef COLOR_GREEN
#define COLOR_GREEN 0x07E0
#endif

#ifndef COLOR_DARKCYAN
#define COLOR_DARKCYAN 0x03EF
#endif

#ifndef COLOR_DARKGREEN
#define COLOR_DARKGREEN 0x03E0
#endif

#ifndef COLOR_SKYBLUE
#define COLOR_SKYBLUE 0x867D
#endif

#ifndef COLOR_VIOLET
#define COLOR_VIOLET 0x915C
#endif

#ifndef COLOR_BROWN
#define COLOR_BROWN 0x9A60
#endif

#ifndef COLOR_TRANSPARENT
#define COLOR_TRANSPARENT 0x0120
#endif

#ifndef COLOR_YELLOW
#define COLOR_YELLOW 0xFFE0
#endif

#ifndef COLOR_ORANGE
#define COLOR_ORANGE 0xFDA0
#endif

#ifndef COLOR_PINK
#define COLOR_PINK 0xFE19
#endif

#ifdef __cplusplus
extern "C"
{
#endif
    // Core display functions
    uint8_t lcd_get_backlight_level(void);
    void lcd_init(bool horizontal);
    void lcd_reset(void);
    void lcd_set_backlight_level(uint8_t brightness); // brightness: 0 (off) to 100 (full)
    void lcd_swap(void);

    // Framebuffer drawing functions
    void lcd_draw_pixel(uint8_t x, uint8_t y, uint16_t color);
    void lcd_fill(uint16_t color);
    void lcd_blit(uint8_t x, uint8_t y, uint8_t width, uint8_t height, const uint8_t *buffer);

    // Shape drawing functions
    void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);
    void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);
    void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color);

    // Text rendering functions
    void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size);
    void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size);

    // Low-level LCD communication functions
    void lcd_write_cmd(uint8_t cmd);
    void lcd_write_data(uint8_t data);
    void lcd_write_data_16bit(uint16_t data);

#ifdef __cplusplus
}
#endif