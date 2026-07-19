#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "../../font/font_mp.h"

#define LCD_WIDTH 128
#define LCD_HEIGHT 64
#define BITS_PER_PIXEL 8

#define LCD_DEFAULT_BRIGHTNESS 50

#ifdef FONT_DEFAULT
#undef FONT_DEFAULT
#define FONT_DEFAULT FONT_SIZE_XTRA_SMALL
#endif

#define LCD_FONT_SCALE_NUM_DEFAULT 1
#define LCD_FONT_SCALE_DEN_DEFAULT 1

#ifdef __cplusplus
extern "C"
{
#endif

    void lcd_deinit(void);
    bool lcd_init(void);
    bool lcd_set_backlight(uint32_t brightness);
    void lcd_swap(void);

    void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color);
    void lcd_fill(uint16_t color);
    void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer);
    void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer);
    void lcd_read_row(uint16_t y, uint8_t *out_buffer);

    void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);
    void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color);
    void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);
    void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);
    void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color, uint8_t alpha);

    void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size);
    void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size);
    uint8_t lcd_get_font_height(void);
    uint8_t lcd_get_font_width(void);
    void lcd_set_font(FontSize size);
    void lcd_set_font_scale(uint8_t num, uint8_t den);

#ifdef __cplusplus
}
#endif
