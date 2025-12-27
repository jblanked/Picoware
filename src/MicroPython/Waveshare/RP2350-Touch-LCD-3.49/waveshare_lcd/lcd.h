// original author: Waveshare Team, translated from https://files.waveshare.com/wiki/RP2350-Touch-LCD-3.49/RP2350-Touch-LCD-3.49-LVGL.zip
#pragma once

#include "stdio.h"
#include <stdlib.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "fonts.h"

#define LCD_HEIGHT 640
#define LCD_WIDTH 172

#define LCD_CHUNK_LINES 8
#define LCD_X_OFFSET 0

#define LCD_DEFAULT_BRIGHTNESS 50 // Default brightness (0-100)
#define LCD_DEFAULT_FONT_SIZE FONT_MEDIUM

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
    void lcd_init();
    void lcd_set_backlight_level(uint8_t brightness); // brightness: 0 (off) to 100 (full)
    void lcd_swap(void);

    // Framebuffer drawing functions
    void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color);
    void lcd_fill(uint16_t color);
    void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer);

    // Shape drawing functions
    void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);
    void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);

    // Text rendering functions
    void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color);
    void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color);
    uint8_t lcd_get_font_height(void);
    uint8_t lcd_get_font_width(void);
    void lcd_set_font(FontSize size);

    // Low-level LCD communication functions
    void lcd_write_cmd(uint8_t cmd);
    void lcd_write_data(uint8_t data);
    void lcd_write_data_16bit(uint16_t data);

#ifdef __cplusplus
}
#endif