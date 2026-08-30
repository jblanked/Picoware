#include "lib.h"
#include "../lcd/lcd_config.h"

#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif

void c_mp_lcd_char(uint16_t x, uint16_t y, char c, uint16_t color)
{
    LCD_MP_CHAR(x, y, c, color, FONT_DEFAULT);
}

void c_mp_lcd_circle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color)
{
    LCD_MP_CIRCLE(x, y, radius, color);
}

void c_mp_lcd_fill(uint16_t color)
{
    LCD_MP_CLEAR(color);
}

void c_mp_lcd_fill_circle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color)
{
    LCD_MP_FILL_CIRCLE(x, y, radius, color);
}

void c_mp_lcd_fill_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    LCD_MP_FILL_RECTANGLE(x, y, width, height, color);
}

void c_mp_lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color)
{
    LCD_MP_FILL_ROUND_RECTANGLE(x, y, width, height, radius, color);
}

void c_mp_lcd_fill_triangle(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    LCD_MP_FILL_TRIANGLE(x0, y0, x1, y1, x2, y2, color);
}

void c_mp_lcd_fill_triangle_alpha(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color, uint8_t alpha)
{
    LCD_MP_FILL_TRIANGLE_ALPHA(x0, y0, x1, y1, x2, y2, color, alpha);
}

void c_mp_lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
{
    LCD_MP_BLIT(x, y, width, height, buffer);
}

void c_mp_lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer)
{
    LCD_MP_BLIT_16BIT(x, y, width, height, buffer);
}

void c_mp_lcd_line(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t color)
{
    LCD_MP_LINE(x0, y0, x1, y1, color);
}

void c_mp_lcd_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    LCD_MP_PIXEL(x, y, color);
}

void c_mp_lcd_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    LCD_MP_RECTANGLE(x, y, width, height, color);
}

void c_mp_lcd_swap(void)
{
    LCD_MP_SWAP();
}

void c_mp_lcd_text(uint16_t x, uint16_t y, const char *text, uint16_t color)
{
    LCD_MP_TEXT(x, y, text, color, FONT_DEFAULT);
}

void c_mp_lcd_triangle(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    LCD_MP_TRIANGLE(x0, y0, x1, y1, x2, y2, color);
}