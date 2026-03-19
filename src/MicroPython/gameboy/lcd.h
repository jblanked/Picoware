#pragma once
#include <stdint.h>

// blit a line of pixels to the LCD (handles windowing and DMA)
// pixels: RGB565 pixel data buffer, gb_width pixels wide (doubled horizontally)
// line: line number (0 = first line opens window, LCD_HEIGHT = close window)
// gb_width: Game Boy LCD width (e.g. 160)
// gb_height: Game Boy LCD height (e.g. 144)
void lcd_blit_gb(const uint8_t *pixels, uint_fast8_t line, int gb_width, int gb_height);
void lcd_char(uint16_t x, uint16_t y, char c, uint16_t color);
void lcd_string(uint16_t x, uint16_t y, const char *str, uint16_t color);
void lcd_swap_gb(void);
void lcd_clear_gb(void);