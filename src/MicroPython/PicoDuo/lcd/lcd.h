#pragma once

#include <stdio.h>
#include "pico/stdlib.h"
#include "../../font/font_mp.h"

#define DISPLAY_HEIGHT LCD_NATIVE_WIDTH
#define DISPLAY_WIDTH LCD_NATIVE_HEIGHT
#define LCD_BAUDRATE (60000000)
#define LCD_CMD_CASET (0x2A)
#define LCD_CMD_COLMOD (0x3A)
#define LCD_CMD_DISPOFF (0x28)
#define LCD_CMD_DISPON (0x29)
#define LCD_CMD_INVON (0x21)
#define LCD_CMD_MADCTL (0x36)
#define LCD_CMD_RASET (0x2B)
#define LCD_CMD_RAMWR (0x2C)
#define LCD_CMD_SLPOUT (0x11)
#define LCD_CMD_SWRESET (0x01)
#define LCD_CSX (5)
#define LCD_DCX (11)
#define LCD_NATIVE_HEIGHT 320
#define LCD_NATIVE_WIDTH 240
#define LCD_RST (10)
#define LCD_SCL (6)
#define LCD_SDI (7)
#define LCD_SDO (4)
#define RGB(r, g, b) ((uint16_t)(((r) >> 3) << 11 | ((g) >> 2) << 5 | ((b) >> 3)))

// Function prototypes

#ifdef __cplusplus
extern "C"
{
#endif

    void lcd_acquire(void);
    bool lcd_available(void);
    void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer);
    void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer);
    void lcd_deinit(void);
    void lcd_display_off(void);
    void lcd_display_on(void);
    void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size);
    void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);
    void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color);
    void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size);
    void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);
    void lcd_erase(void);
    void lcd_fill(uint16_t color);
    void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
    void lcd_fill_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color);
    void lcd_fill_polygon_alpha(uint16_t x[], uint16_t y[], int count, uint16_t color, uint8_t alpha);
    void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
    void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color);
    void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);
    void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color, uint8_t alpha);
    void lcd_init(void);
    void lcd_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color);
    bool lcd_read_row(uint16_t row, uint8_t *dst);
    void lcd_release(void);
    void lcd_reset(void);
    void lcd_solid_rectangle(uint16_t colour, uint16_t x, uint16_t y, uint16_t width, uint16_t height);
    void lcd_swap(void);
    void lcd_swap_region(uint16_t x, uint16_t y, uint16_t width, uint16_t height);
    void lcd_write16_buf(const uint16_t *buffer, size_t len);
    void lcd_write_cmd(uint8_t cmd);
    void lcd_write_data(uint8_t len, ...);

#ifdef __cplusplus
}
#endif
