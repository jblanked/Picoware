/*
 * LCD Driver for the Waveshare ESP32-C5-Touch-LCD-3.5 (ESP32-C5, ST7796 320x480 SPI).
 *
 * 8-bit RGB332 framebuffer expanded through a palette to RGB565 on swap, as on
 * the Cardputer. At 320x480 it is 150 KB, so it lives in PSRAM. Panel reset and
 * backlight are driven through the I/O expander.
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "../../font/font_mp.h"

#define LCD_WIDTH 320    // Horizontal resolution
#define LCD_HEIGHT 480   // Vertical resolution
#define BITS_PER_PIXEL 8 // Number of image display bits of the display screen

// Backlight is PWM on the I/O expander (0x24), not a GPIO.

#define LCD_DEFAULT_BRIGHTNESS 100 // Default brightness (0-100)

#ifdef __cplusplus
extern "C"
{
#endif

    void lcd_deinit(void);                       // De-initialize LCD and free resources
    bool lcd_init(void);                         // Initialize LCD and set up necessary configurations
    bool lcd_is_ready(void); // true once the panel is initialized (it then owns its chip select)
    bool lcd_set_backlight(uint32_t brightness); // Set the screen backlight
    void lcd_swap(void);                         // Transfer the entire frame buffer to the LCD

    // Framebuffer drawing functions
    void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color);                                          // Draw a single pixel at (x, y) with specified RGB332 color
    void lcd_fill(uint16_t color);                                                                        // Fill the entire frame buffer with a solid RGB332 color
    void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer);        // Copy an external 8-bit image buffer into the frame buffer at specified position
    void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer); // Copy a 16-bit RGB565 image buffer into the frame buffer
    void lcd_blit_mask(int16_t dst_x, int16_t dst_y, uint16_t dst_w, uint16_t dst_h,
                       uint16_t src_w, uint16_t src_h, const uint8_t *buffer, const uint8_t *mask);
    void lcd_read_row(uint16_t y, uint8_t *out_buffer);                                                   // Copy a framebuffer row to out_buffer

    // Shape drawing functions
    void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);                                                    // Draw a line from (x1, y1) to (x2, y2) with specified RGB332 color
    void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);                                               // Draw a rectangle outline at (x, y) with specified width, height and color
    void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);                                               // Fill a rectangle at (x, y) with specified width, height and color
    void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color);                   // Fill a rounded rectangle (radius is currently a compatibility no-op)
    void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);                                               // Draw a circle outline with center at (center_x, center_y) and specified radius and color
    void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);                                               // Draw a filled circle with center at (center_x, center_y) and specified radius and color
    void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);                      // Draw a triangle outline with vertices at (x1, y1), (x2, y2), (x3, y3)
    void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color);                      // Draw a filled triangle with vertices at (x1, y1), (x2, y2), (x3, y3) and specified color
    void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color, uint8_t alpha); // Draw a filled triangle blended over what is already there

    // Polygon drawing functions
    void lcd_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color);
    void lcd_fill_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color);
    void lcd_fill_polygon_alpha(uint16_t x[], uint16_t y[], int count,
                                uint16_t color, uint8_t alpha);

    // Text rendering functions
    void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size);           // Draw a single character at (x, y) with specified RGB332 color using current font
    void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size); // Draw a string of text starting at (x, y) with specified RGB332 color using current font
    uint8_t lcd_get_font_height(void);                                                           // Get the height of the current font in pixels
    uint8_t lcd_get_font_width(void);                                                            // Get the width of the current font in pixels
    void lcd_set_font(FontSize size);                                                            // Set the current font size for text rendering

#ifdef __cplusplus
}
#endif
