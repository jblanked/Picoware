/*
 * LCD Driver for Crow Panel Advanced 10.1-inch ESP32-P4 HMI AI Display
 * Copyright © 2026 JBlanked
 * https://github.com/jblanked
 *
 * Adapted from https://github.com/Elecrow-RD/CrowPanel-Advanced-10.1inch-ESP32-P4-HMI-AI-Display-1024x600-IPS-Touch-Screen/blob/master/example/V1.0/idf-code/Lesson07-Turn_on_the_screen/peripheral/bsp_illuminate/bsp_illuminate.c
 */

#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "fonts.h"

#define LCD_WIDTH 1024    // Horizontal resolution
#define LCD_HEIGHT 600    // Vertical resolution
#define BITS_PER_PIXEL 16 // Number of image display bits of the display screen

#define LCD_BACKLIGHT_PIN 31       // LCD Backlight Pin
#define LCD_BACKLIGHT_PWM_HZ 30000 // LCD Backlight PWM Frequency

#define LCD_DEFAULT_BRIGHTNESS 50 // Default brightness (0-100)
#define LCD_DEFAULT_FONT_SIZE FONT_MEDIUM

#ifdef __cplusplus
extern "C"
{
#endif

    void lcd_deinit(void);                       // De-initialize LCD and free resources
    bool lcd_init(void);                         // Initialize LCD and set up necessary configurations
    bool lcd_set_backlight(uint32_t brightness); // Set the screen backlight
    void lcd_swap(void);                         // Transfer the entire frame buffer to the LCD

    // Framebuffer drawing functions
    void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color);                                    // Draw a single pixel at (x, y) with specified color
    void lcd_fill(uint16_t color);                                                                  // Fill the entire frame buffer with a solid color
    void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer); // Copy an external image buffer into the frame buffer at specified position

    // Shape drawing functions
    void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color);                               // Draw a line from (x1, y1) to (x2, y2) with specified color
    void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);                          // Draw a rectangle outline at (x, y) with specified width, height and color
    void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color);                          // Fill a rectangle at (x, y) with specified width, height and color
    void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);                          // Draw a circle outline with center at (center_x, center_y) and specified radius and color
    void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color);                          // Draw a filled circle with center at (center_x, center_y) and specified radius and color
    void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color); // Draw a filled triangle with vertices at (x1, y1), (x2, y2), (x3, y3) and specified color

    // Text rendering functions
    void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color);           // Draw a single character at (x, y) with specified color using current font
    void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color); // Draw a string of text starting at (x, y) with specified color using current font
    uint8_t lcd_get_font_height(void);                                            // Get the height of the current font in pixels
    uint8_t lcd_get_font_width(void);                                             // Get the width of the current font in pixels
    void lcd_set_font(FontSize size);                                             // Set the current font size for text rendering

#ifdef __cplusplus
}
#endif