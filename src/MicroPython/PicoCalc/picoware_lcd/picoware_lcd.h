#pragma once
#include "lcd.h"
#include "../picoware_psram/psram_qspi.h"
#include "../../font/font_mp.h"

// Display constants
#define DISPLAY_WIDTH 320
#define DISPLAY_HEIGHT 320
#define PALETTE_SIZE 256

// Core display functions
void picocalc_lcd_init(void);
void lcd_deinit(void);
void lcd_swap(void);

// Framebuffer drawing functions
void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color);
void lcd_fill(uint16_t color);
void picocalc_lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer);
void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer);

// Shape drawing functions
void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);
void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);
void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);
void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);
void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color);
void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);

// Text rendering functions
void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size);
void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size);

void lcd_set_mode(uint8_t mode);

// External PSRAM instance access
extern psram_qspi_inst_t *picoware_get_psram_instance(void);

// Inline helper to write pixel to PSRAM framebuffer
void picoware_write_pixel_fb(psram_qspi_inst_t *psram, int x, int y, uint8_t color_index);

// Batch write 16-bit RGB565 buffer to framebuffer (for LVGL) - converts to RGB332
void picoware_write_buffer_fb_16(psram_qspi_inst_t *psram, int x, int y, int width, int height, const uint16_t *buffer);

void picoware_lcd_swap_region(uint16_t x, uint16_t y, uint16_t width, uint16_t height);