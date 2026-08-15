#pragma once

#include <stddef.h>
#include <stdint.h>

void desktop_lcd_clear(uint16_t color);
void desktop_lcd_pixel(uint16_t x, uint16_t y, uint16_t color);
void desktop_lcd_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                      uint16_t color);
void desktop_lcd_rectangle(uint16_t x, uint16_t y, uint16_t width,
                           uint16_t height, uint16_t color);
void desktop_lcd_fill_rectangle(uint16_t x, uint16_t y, uint16_t width,
                                uint16_t height, uint16_t color);
void desktop_lcd_circle(uint16_t x, uint16_t y, uint16_t radius,
                        uint16_t color);
void desktop_lcd_fill_circle(uint16_t x, uint16_t y, uint16_t radius,
                             uint16_t color);
void desktop_lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2,
                               uint16_t y2, uint16_t x3, uint16_t y3,
                               uint16_t color);
void desktop_lcd_text(uint16_t x, uint16_t y, const char *text,
                      uint16_t color, int font_size);
void desktop_lcd_swap(void);

void desktop_log_message(const char *message);
size_t desktop_storage_file_size(const char *path);
size_t desktop_storage_file_read(const char *path, void *buffer,
                                 size_t buffer_size);
