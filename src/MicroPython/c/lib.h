#pragma once
#include <stdint.h>

void c_mp_lcd_char(uint16_t x, uint16_t y, char c, uint16_t color);
void c_mp_lcd_circle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color);
void c_mp_lcd_fill(uint16_t color);
void c_mp_lcd_fill_circle(uint16_t x, uint16_t y, uint16_t radius, uint16_t color);
void c_mp_lcd_fill_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
void c_mp_lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color);
void c_mp_lcd_fill_triangle(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);
void c_mp_lcd_fill_triangle_alpha(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color, uint8_t alpha);
void c_mp_lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer);
void c_mp_lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer);
void c_mp_lcd_line(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t color);
void c_mp_lcd_pixel(uint16_t x, uint16_t y, uint16_t color);
void c_mp_lcd_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
void c_mp_lcd_swap(void);
void c_mp_lcd_text(uint16_t x, uint16_t y, const char *text, uint16_t color);
void c_mp_lcd_triangle(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);
