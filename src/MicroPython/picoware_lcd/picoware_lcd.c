/*
 * Picoware LCD Native C Extension for MicroPython
 *
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "lcd.h"
#include <stdlib.h>
#include <string.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// Module constants
#define DISPLAY_WIDTH 320
#define DISPLAY_HEIGHT 320
#define PALETTE_SIZE 256
#define FONT_WIDTH 5
#define FONT_HEIGHT 8
#define CHAR_WIDTH 6 // Including spacing

// Module state
static bool module_initialized = false;

static const uint8_t *get_font_data(void)
{
    static const uint8_t font_data[] = {
        0x00, 0x00, 0x00, 0x00, 0x00, // char 0
        0x3e, 0x5b, 0x4f, 0x5b, 0x3e, // char 1
        0x3e, 0x6b, 0x4f, 0x6b, 0x3e, // char 2
        0x1c, 0x3e, 0x7c, 0x3e, 0x1c, // char 3
        0x18, 0x3c, 0x7e, 0x3c, 0x18, // char 4
        0x1c, 0x57, 0x7d, 0x57, 0x1c, // char 5
        0x1c, 0x5e, 0x7f, 0x5e, 0x1c, // char 6
        0x00, 0x18, 0x3c, 0x18, 0x00, // char 7
        0xff, 0xe7, 0xc3, 0xe7, 0xff, // char 8
        0x00, 0x18, 0x24, 0x18, 0x00, // char 9
        0xff, 0xe7, 0xdb, 0xe7, 0xff, // char 10
        0x30, 0x48, 0x3a, 0x06, 0x0e, // char 11
        0x26, 0x29, 0x79, 0x29, 0x26, // char 12
        0x40, 0x7f, 0x05, 0x05, 0x07, // char 13
        0x40, 0x7f, 0x05, 0x25, 0x3f, // char 14
        0x5a, 0x3c, 0xe7, 0x3c, 0x5a, // char 15
        0x7f, 0x3e, 0x1c, 0x1c, 0x08, // char 16
        0x08, 0x1c, 0x1c, 0x3e, 0x7f, // char 17
        0x14, 0x22, 0x7f, 0x22, 0x14, // char 18
        0x5f, 0x5f, 0x00, 0x5f, 0x5f, // char 19
        0x06, 0x09, 0x7f, 0x01, 0x7f, // char 20
        0x00, 0x66, 0x89, 0x95, 0x6a, // char 21
        0x60, 0x60, 0x60, 0x60, 0x60, // char 22
        0x94, 0xa2, 0xff, 0xa2, 0x94, // char 23
        0x08, 0x04, 0x7e, 0x04, 0x08, // char 24
        0x10, 0x20, 0x7e, 0x20, 0x10, // char 25
        0x08, 0x08, 0x2a, 0x1c, 0x08, // char 26
        0x08, 0x1c, 0x2a, 0x08, 0x08, // char 27
        0x1e, 0x10, 0x10, 0x10, 0x10, // char 28
        0x0c, 0x1e, 0x0c, 0x1e, 0x0c, // char 29
        0x30, 0x38, 0x3e, 0x38, 0x30, // char 30
        0x06, 0x0e, 0x3e, 0x0e, 0x06, // char 31
        0x00, 0x00, 0x00, 0x00, 0x00, // ' ' (space)
        0x00, 0x00, 0x5f, 0x00, 0x00, // '!'
        0x00, 0x07, 0x00, 0x07, 0x00, // '"'
        0x14, 0x7f, 0x14, 0x7f, 0x14, // '#'
        0x24, 0x2a, 0x7f, 0x2a, 0x12, // '$'
        0x23, 0x13, 0x08, 0x64, 0x62, // '%'
        0x36, 0x49, 0x56, 0x20, 0x50, // '&'
        0x00, 0x08, 0x07, 0x03, 0x00, // '\''
        0x00, 0x1c, 0x22, 0x41, 0x00, // '('
        0x00, 0x41, 0x22, 0x1c, 0x00, // ')'
        0x2a, 0x1c, 0x7f, 0x1c, 0x2a, // '*'
        0x08, 0x08, 0x3e, 0x08, 0x08, // '+'
        0x00, 0x80, 0x70, 0x30, 0x00, // ','
        0x08, 0x08, 0x08, 0x08, 0x08, // '-'
        0x00, 0x00, 0x60, 0x60, 0x00, // '.'
        0x20, 0x10, 0x08, 0x04, 0x02, // '/'
        0x3e, 0x51, 0x49, 0x45, 0x3e, // '0'
        0x00, 0x42, 0x7f, 0x40, 0x00, // '1'
        0x72, 0x49, 0x49, 0x49, 0x46, // '2'
        0x21, 0x41, 0x49, 0x4d, 0x33, // '3'
        0x18, 0x14, 0x12, 0x7f, 0x10, // '4'
        0x27, 0x45, 0x45, 0x45, 0x39, // '5'
        0x3c, 0x4a, 0x49, 0x49, 0x31, // '6'
        0x41, 0x21, 0x11, 0x09, 0x07, // '7'
        0x36, 0x49, 0x49, 0x49, 0x36, // '8'
        0x46, 0x49, 0x49, 0x29, 0x1e, // '9'
        0x00, 0x00, 0x14, 0x00, 0x00, // ':'
        0x00, 0x40, 0x34, 0x00, 0x00, // ';'
        0x00, 0x08, 0x14, 0x22, 0x41, // '<'
        0x14, 0x14, 0x14, 0x14, 0x14, // '='
        0x00, 0x41, 0x22, 0x14, 0x08, // '>'
        0x02, 0x01, 0x59, 0x09, 0x06, // '?'
        0x3e, 0x41, 0x5d, 0x59, 0x4e, // '@'
        0x7c, 0x12, 0x11, 0x12, 0x7c, // 'A'
        0x7f, 0x49, 0x49, 0x49, 0x36, // 'B'
        0x3e, 0x41, 0x41, 0x41, 0x22, // 'C'
        0x7f, 0x41, 0x41, 0x41, 0x3e, // 'D'
        0x7f, 0x49, 0x49, 0x49, 0x41, // 'E'
        0x7f, 0x09, 0x09, 0x09, 0x01, // 'F'
        0x3e, 0x41, 0x41, 0x51, 0x73, // 'G'
        0x7f, 0x08, 0x08, 0x08, 0x7f, // 'H'
        0x00, 0x41, 0x7f, 0x41, 0x00, // 'I'
        0x20, 0x40, 0x41, 0x3f, 0x01, // 'J'
        0x7f, 0x08, 0x14, 0x22, 0x41, // 'K'
        0x7f, 0x40, 0x40, 0x40, 0x40, // 'L'
        0x7f, 0x02, 0x1c, 0x02, 0x7f, // 'M'
        0x7f, 0x04, 0x08, 0x10, 0x7f, // 'N'
        0x3e, 0x41, 0x41, 0x41, 0x3e, // 'O'
        0x7f, 0x09, 0x09, 0x09, 0x06, // 'P'
        0x3e, 0x41, 0x51, 0x21, 0x5e, // 'Q'
        0x7f, 0x09, 0x19, 0x29, 0x46, // 'R'
        0x26, 0x49, 0x49, 0x49, 0x32, // 'S'
        0x03, 0x01, 0x7f, 0x01, 0x03, // 'T'
        0x3f, 0x40, 0x40, 0x40, 0x3f, // 'U'
        0x1f, 0x20, 0x40, 0x20, 0x1f, // 'V'
        0x3f, 0x40, 0x38, 0x40, 0x3f, // 'W'
        0x63, 0x14, 0x08, 0x14, 0x63, // 'X'
        0x03, 0x04, 0x78, 0x04, 0x03, // 'Y'
        0x61, 0x59, 0x49, 0x4d, 0x43, // 'Z'
        0x00, 0x7f, 0x41, 0x41, 0x41, // '['
        0x02, 0x04, 0x08, 0x10, 0x20, // '\'
        0x00, 0x41, 0x41, 0x41, 0x7f, // ']'
        0x04, 0x02, 0x01, 0x02, 0x04, // '^'
        0x40, 0x40, 0x40, 0x40, 0x40, // '_'
        0x00, 0x03, 0x07, 0x08, 0x00, // '`'
        0x20, 0x54, 0x54, 0x78, 0x40, // 'a'
        0x7f, 0x28, 0x44, 0x44, 0x38, // 'b'
        0x38, 0x44, 0x44, 0x44, 0x28, // 'c'
        0x38, 0x44, 0x44, 0x28, 0x7f, // 'd'
        0x38, 0x54, 0x54, 0x54, 0x18, // 'e'
        0x00, 0x08, 0x7e, 0x09, 0x02, // 'f'
        0x18, 0xa4, 0xa4, 0x9c, 0x78, // 'g'
        0x7f, 0x08, 0x04, 0x04, 0x78, // 'h'
        0x00, 0x44, 0x7d, 0x40, 0x00, // 'i'
        0x20, 0x40, 0x40, 0x3d, 0x00, // 'j'
        0x7f, 0x10, 0x28, 0x44, 0x00, // 'k'
        0x00, 0x41, 0x7f, 0x40, 0x00, // 'l'
        0x7c, 0x04, 0x78, 0x04, 0x78, // 'm'
        0x7c, 0x08, 0x04, 0x04, 0x78, // 'n'
        0x38, 0x44, 0x44, 0x44, 0x38, // 'o'
        0xfc, 0x18, 0x24, 0x24, 0x18, // 'p'
        0x18, 0x24, 0x24, 0x18, 0xfc, // 'q'
        0x7c, 0x08, 0x04, 0x04, 0x08, // 'r'
        0x48, 0x54, 0x54, 0x54, 0x24, // 's'
        0x04, 0x04, 0x3f, 0x44, 0x24, // 't'
        0x3c, 0x40, 0x40, 0x20, 0x7c, // 'u'
        0x1c, 0x20, 0x40, 0x20, 0x1c, // 'v'
        0x3c, 0x40, 0x30, 0x40, 0x3c, // 'w'
        0x44, 0x28, 0x10, 0x28, 0x44, // 'x'
        0x4c, 0x90, 0x90, 0x90, 0x7c, // 'y'
        0x44, 0x64, 0x54, 0x4c, 0x44, // 'z'
        0x00, 0x08, 0x36, 0x41, 0x00, // '{'
        0x00, 0x00, 0x77, 0x00, 0x00, // '|'
        0x00, 0x41, 0x36, 0x08, 0x00, // '}'
        0x02, 0x01, 0x02, 0x04, 0x02, // '~'
        0x3c, 0x26, 0x23, 0x26, 0x3c, // char 127
    };
    return font_data;
}

// Function to initialize the LCD
STATIC mp_obj_t picoware_lcd_init(size_t n_args, const mp_obj_t *args)
{
    // Arguments: background_color
    if (n_args != 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("init requires 1 argument: background_color"));
    }

    if (!module_initialized)
    {
        lcd_init();
        lcd_set_background(mp_obj_get_int(args[0]));
        lcd_set_underscore(false);
        lcd_enable_cursor(false);
        module_initialized = true;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_init_obj, 1, 1, picoware_lcd_init);

// Fast 8-bit to RGB565 conversion and blit function
STATIC mp_obj_t picoware_lcd_blit_8bit(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, palette_data, width, height, x_offset, y_offset
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("blit_8bit requires 6 arguments"));
    }

    // Get framebuffer data (8-bit indices)
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_READ);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    // Get palette data (RGB565 values)
    mp_buffer_info_t palette_info;
    mp_get_buffer_raise(args[1], &palette_info, MP_BUFFER_READ);
    uint16_t *palette = (uint16_t *)palette_info.buf;

    // Get dimensions and position
    int width = mp_obj_get_int(args[2]);
    int height = mp_obj_get_int(args[3]);
    int x_offset = mp_obj_get_int(args[4]);
    int y_offset = mp_obj_get_int(args[5]);

    // Validate arguments
    if (width <= 0 || height <= 0 || width > DISPLAY_WIDTH || height > DISPLAY_HEIGHT)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid dimensions"));
    }

    if (x_offset < 0 || y_offset < 0 ||
        x_offset + width > DISPLAY_WIDTH || y_offset + height > DISPLAY_HEIGHT)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid position"));
    }

    if (fb_info.len < (size_t)(width * height))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Framebuffer too small"));
    }

    if (palette_info.len < PALETTE_SIZE * 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Palette too small"));
    }

    // Use line-by-line conversion to avoid large buffer allocation
    uint16_t line_buffer[DISPLAY_WIDTH];

    for (int y = 0; y < height; y++)
    {
        // Convert one line at a time
        for (int x = 0; x < width; x++)
        {
            int fb_index = y * width + x;
            uint8_t color_index = fb_data[fb_index];
            if (color_index < PALETTE_SIZE)
            {
                line_buffer[x] = palette[color_index];
            }
            else
            {
                line_buffer[x] = 0; // Black for invalid indices
            }
        }

        // Blit one line at a time
        lcd_blit(line_buffer, x_offset, y_offset + y, width, 1);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_blit_8bit_obj, 6, 6, picoware_lcd_blit_8bit);

STATIC mp_obj_t picoware_lcd_blit_8bit_fullscreen(mp_obj_t fb_obj, mp_obj_t palette_obj)
{
    // Get framebuffer data (8-bit indices)
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(fb_obj, &fb_info, MP_BUFFER_READ);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    // Get palette data (RGB565 values)
    mp_buffer_info_t palette_info;
    mp_get_buffer_raise(palette_obj, &palette_info, MP_BUFFER_READ);
    uint16_t *palette = (uint16_t *)palette_info.buf;

    size_t total_pixels = DISPLAY_WIDTH * DISPLAY_HEIGHT;

    // Validate buffer sizes
    if (fb_info.len < total_pixels)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Framebuffer too small for fullscreen"));
    }

    if (palette_info.len < PALETTE_SIZE * 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Palette too small"));
    }

    // Use line-by-line conversion for memory efficiency
    uint16_t line_buffer[DISPLAY_WIDTH];

    for (int y = 0; y < DISPLAY_HEIGHT; y++)
    {
        // Convert one line from 8-bit to 16-bit
        for (int x = 0; x < DISPLAY_WIDTH; x++)
        {
            int fb_index = y * DISPLAY_WIDTH + x;
            uint8_t color_index = fb_data[fb_index];
            if (color_index < PALETTE_SIZE)
            {
                line_buffer[x] = palette[color_index];
            }
            else
            {
                line_buffer[x] = 0; // Black for invalid indices
            }
        }

        // Send to LCD - each line is sent immediately
        lcd_blit(line_buffer, 0, y, DISPLAY_WIDTH, 1);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lcd_blit_8bit_fullscreen_obj, picoware_lcd_blit_8bit_fullscreen);

STATIC mp_obj_t picoware_lcd_clear_screen(void)
{
    lcd_clear_screen();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_clear_screen_obj, picoware_lcd_clear_screen);

STATIC mp_obj_t picoware_lcd_display_on(void)
{
    lcd_display_on();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_display_on_obj, picoware_lcd_display_on);

STATIC mp_obj_t picoware_lcd_display_off(void)
{
    lcd_display_off();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_display_off_obj, picoware_lcd_display_off);

// Convert RGB565 to RGB332 index
STATIC uint8_t color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

// Draw pixel in 8-bit framebuffer
STATIC mp_obj_t picoware_lcd_draw_pixel(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, x, y, color565
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_pixel requires 4 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int x = mp_obj_get_int(args[1]);
    int y = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    // Bounds check
    if (x < 0 || x >= DISPLAY_WIDTH || y < 0 || y >= DISPLAY_HEIGHT)
    {
        return mp_const_none; // Silently ignore out-of-bounds
    }

    // Convert to 8-bit and store
    uint8_t color_index = color565_to_332(color);
    int buffer_index = y * DISPLAY_WIDTH + x;
    fb_data[buffer_index] = color_index;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_pixel_obj, 4, 4, picoware_lcd_draw_pixel);

// Fill rectangle in 8-bit framebuffer
STATIC mp_obj_t picoware_lcd_fill_rect(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, x, y, width, height, color565
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_rect requires 6 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int x = mp_obj_get_int(args[1]);
    int y = mp_obj_get_int(args[2]);
    int width = mp_obj_get_int(args[3]);
    int height = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);

    // Bounds clipping
    if (x < 0)
    {
        width += x;
        x = 0;
    }
    if (y < 0)
    {
        height += y;
        y = 0;
    }
    if (x + width > DISPLAY_WIDTH)
    {
        width = DISPLAY_WIDTH - x;
    }
    if (y + height > DISPLAY_HEIGHT)
    {
        height = DISPLAY_HEIGHT - y;
    }

    if (width <= 0 || height <= 0)
        return mp_const_none;

    uint8_t color_index = color565_to_332(color);

    // Fast fill using optimized loops
    for (int py = y; py < y + height; py++)
    {
        int line_start = py * DISPLAY_WIDTH + x;
        for (int px = 0; px < width; px++)
        {
            fb_data[line_start + px] = color_index;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_fill_rect_obj, 6, 6, picoware_lcd_fill_rect);

// Draw line
STATIC mp_obj_t picoware_lcd_draw_line(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, x, y, length, color565
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_line requires 5 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int x = mp_obj_get_int(args[1]);
    int y = mp_obj_get_int(args[2]);
    int length = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    // Bounds check
    if (y < 0 || y >= DISPLAY_HEIGHT)
        return mp_const_none;

    uint8_t color_index = color565_to_332(color);

    // Draw horizontal line with bounds checking
    for (int i = 0; i < length; i++)
    {
        int currentX = x + i;
        if (currentX >= 0 && currentX < DISPLAY_WIDTH)
        {
            int buffer_index = y * DISPLAY_WIDTH + currentX;
            fb_data[buffer_index] = color_index;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_line_obj, 5, 5, picoware_lcd_draw_line);

// Clear framebuffer
STATIC mp_obj_t picoware_lcd_clear_framebuffer(mp_obj_t fb_obj, mp_obj_t color_index_obj)
{
    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(fb_obj, &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    uint8_t color_index = mp_obj_get_int(color_index_obj);

    // Fast clear using memset
    memset(fb_data, color_index, DISPLAY_WIDTH * DISPLAY_HEIGHT);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lcd_clear_framebuffer_obj, picoware_lcd_clear_framebuffer);

STATIC mp_obj_t picoware_lcd_draw_char(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, x, y, char, color565
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_char requires 5 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int x = mp_obj_get_int(args[1]);
    int y = mp_obj_get_int(args[2]);
    int char_code = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    // Bounds check
    if (x < 0 || x + CHAR_WIDTH > DISPLAY_WIDTH ||
        y < 0 || y + FONT_HEIGHT > DISPLAY_HEIGHT)
    {
        return mp_const_none; // Character would be out of bounds
    }

    // Validate character code
    if (char_code < 0 || char_code > 127)
    {
        char_code = 127; // Use default character for out of range
    }

    uint8_t color_index = color565_to_332(color);
    const uint8_t *font_data = get_font_data();
    const uint8_t *char_data = &font_data[char_code * FONT_WIDTH];

    // Render character bitmap
    for (int col = 0; col < FONT_WIDTH; col++)
    {
        uint8_t column_data = char_data[col];
        for (int row = 0; row < FONT_HEIGHT; row++)
        {
            if (column_data & (1 << row))
            {
                int buffer_index = (y + row) * DISPLAY_WIDTH + (x + col);
                fb_data[buffer_index] = color_index;
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_char_obj, 5, 5, picoware_lcd_draw_char);

STATIC mp_obj_t picoware_lcd_draw_text(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, x, y, text_string, color565
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_text requires 5 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int start_x = mp_obj_get_int(args[1]);
    int start_y = mp_obj_get_int(args[2]);
    const char *text = mp_obj_str_get_str(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    uint8_t color_index = color565_to_332(color);
    const uint8_t *font_data = get_font_data();

    int current_x = start_x;
    int current_y = start_y;

    // Process each character in the string
    for (const char *p = text; *p != '\0'; p++)
    {
        char ch = *p;

        if (ch == '\n')
        {
            // Handle newline
            current_x = start_x;
            current_y += FONT_HEIGHT;
            continue;
        }
        else if (ch == ' ')
        {
            // Handle space - just advance position
            current_x += CHAR_WIDTH;
            continue;
        }

        // Check bounds
        if (current_y + FONT_HEIGHT > DISPLAY_HEIGHT)
        {
            break; // Text goes below screen
        }
        if (current_x + CHAR_WIDTH > DISPLAY_WIDTH)
        {
            // Wrap to next line
            current_x = start_x;
            current_y += FONT_HEIGHT;
            if (current_y + FONT_HEIGHT > DISPLAY_HEIGHT)
            {
                break;
            }
        }

        // Validate character
        int char_code = (int)ch;
        if (char_code < 0 || char_code > 127)
        {
            char_code = 127; // Default character
        }

        const uint8_t *char_data = &font_data[char_code * FONT_WIDTH];

        // Render character bitmap
        for (int col = 0; col < FONT_WIDTH; col++)
        {
            uint8_t column_data = char_data[col];
            for (int row = 0; row < FONT_HEIGHT; row++)
            {
                if (column_data & (1 << row))
                {
                    int px = current_x + col;
                    int py = current_y + row;
                    if (px < DISPLAY_WIDTH && py < DISPLAY_HEIGHT)
                    {
                        int buffer_index = py * DISPLAY_WIDTH + px;
                        fb_data[buffer_index] = color_index;
                    }
                }
            }
        }

        current_x += CHAR_WIDTH;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_text_obj, 5, 5, picoware_lcd_draw_text);

// Bresenham line algorithm
STATIC mp_obj_t picoware_lcd_draw_line_custom(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, x1, y1, x2, y2, color565
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_line_custom requires 6 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int x1 = mp_obj_get_int(args[1]);
    int y1 = mp_obj_get_int(args[2]);
    int x2 = mp_obj_get_int(args[3]);
    int y2 = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);

    uint8_t color_index = color565_to_332(color);

    // Bresenham's line algorithm (from draw.cpp)
    int dx = abs(x2 - x1);
    int dy = abs(y2 - y1);
    int sx = (x1 < x2) ? 1 : -1;
    int sy = (y1 < y2) ? 1 : -1;
    int err = dx - dy;

    while (true)
    {
        // Draw pixel if within bounds
        if (x1 >= 0 && x1 < DISPLAY_WIDTH && y1 >= 0 && y1 < DISPLAY_HEIGHT)
        {
            int buffer_index = y1 * DISPLAY_WIDTH + x1;
            fb_data[buffer_index] = color_index;
        }

        // Check if we've reached the end point
        if (x1 == x2 && y1 == y2)
            break;

        int e2 = 2 * err;
        if (e2 > -dy)
        {
            err -= dy;
            x1 += sx;
        }
        if (e2 < dx)
        {
            err += dx;
            y1 += sy;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_line_custom_obj, 6, 6, picoware_lcd_draw_line_custom);

STATIC mp_obj_t picoware_lcd_draw_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, center_x, center_y, radius, color565
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_circle requires 5 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int center_x = mp_obj_get_int(args[1]);
    int center_y = mp_obj_get_int(args[2]);
    int radius = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    if (radius <= 0 || radius > 100) // Limit radius to prevent issues
        return mp_const_none;

    uint8_t color_index = color565_to_332(color);

    // Simple Bresenham circle with minimal bounds checking
    int x = 0;
    int y = radius;
    int d = 3 - 2 * radius;

    while (x <= y)
    {
        // Only plot points that are clearly within bounds (fast check)
        int px1 = center_x + x, py1 = center_y + y;
        int px2 = center_x - x, py2 = center_y + y;
        int px3 = center_x + x, py3 = center_y - y;
        int px4 = center_x - x, py4 = center_y - y;
        int px5 = center_x + y, py5 = center_y + x;
        int px6 = center_x - y, py6 = center_y + x;
        int px7 = center_x + y, py7 = center_y - x;
        int px8 = center_x - y, py8 = center_y - x;

        // Quick bounds check and plot
        if (px1 >= 0 && px1 < DISPLAY_WIDTH && py1 >= 0 && py1 < DISPLAY_HEIGHT)
            fb_data[py1 * DISPLAY_WIDTH + px1] = color_index;
        if (px2 >= 0 && px2 < DISPLAY_WIDTH && py2 >= 0 && py2 < DISPLAY_HEIGHT)
            fb_data[py2 * DISPLAY_WIDTH + px2] = color_index;
        if (px3 >= 0 && px3 < DISPLAY_WIDTH && py3 >= 0 && py3 < DISPLAY_HEIGHT)
            fb_data[py3 * DISPLAY_WIDTH + px3] = color_index;
        if (px4 >= 0 && px4 < DISPLAY_WIDTH && py4 >= 0 && py4 < DISPLAY_HEIGHT)
            fb_data[py4 * DISPLAY_WIDTH + px4] = color_index;
        if (px5 >= 0 && px5 < DISPLAY_WIDTH && py5 >= 0 && py5 < DISPLAY_HEIGHT)
            fb_data[py5 * DISPLAY_WIDTH + px5] = color_index;
        if (px6 >= 0 && px6 < DISPLAY_WIDTH && py6 >= 0 && py6 < DISPLAY_HEIGHT)
            fb_data[py6 * DISPLAY_WIDTH + px6] = color_index;
        if (px7 >= 0 && px7 < DISPLAY_WIDTH && py7 >= 0 && py7 < DISPLAY_HEIGHT)
            fb_data[py7 * DISPLAY_WIDTH + px7] = color_index;
        if (px8 >= 0 && px8 < DISPLAY_WIDTH && py8 >= 0 && py8 < DISPLAY_HEIGHT)
            fb_data[py8 * DISPLAY_WIDTH + px8] = color_index;

        if (d < 0)
            d += 4 * x + 6;
        else
        {
            d += 4 * (x - y) + 10;
            y--;
        }
        x++;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_circle_obj, 5, 5, picoware_lcd_draw_circle);

STATIC mp_obj_t picoware_lcd_fill_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: framebuffer_data, center_x, center_y, radius, color565
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_circle requires 5 arguments"));
    }

    // Get framebuffer data
    mp_buffer_info_t fb_info;
    mp_get_buffer_raise(args[0], &fb_info, MP_BUFFER_WRITE);
    uint8_t *fb_data = (uint8_t *)fb_info.buf;

    int center_x = mp_obj_get_int(args[1]);
    int center_y = mp_obj_get_int(args[2]);
    int radius = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    if (radius <= 0 || radius > 50) // Limit radius to prevent performance issues
        return mp_const_none;

    uint8_t color_index = color565_to_332(color);
    int radius_squared = radius * radius;

    // Very tight bounding box with safety margins
    int start_x = center_x - radius;
    int end_x = center_x + radius;
    int start_y = center_y - radius;
    int end_y = center_y + radius;

    // Clamp to display bounds
    if (start_x < 0)
        start_x = 0;
    if (end_x >= DISPLAY_WIDTH)
        end_x = DISPLAY_WIDTH - 1;
    if (start_y < 0)
        start_y = 0;
    if (end_y >= DISPLAY_HEIGHT)
        end_y = DISPLAY_HEIGHT - 1;

    // Fill using distance check - optimized for small circles
    for (int y = start_y; y <= end_y; y++)
    {
        int dy = y - center_y;
        int dy_squared = dy * dy;

        for (int x = start_x; x <= end_x; x++)
        {
            int dx = x - center_x;
            int distance_squared = dx * dx + dy_squared;

            if (distance_squared <= radius_squared)
            {
                fb_data[y * DISPLAY_WIDTH + x] = color_index;
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_fill_circle_obj, 5, 5, picoware_lcd_fill_circle);

// Module globals table
STATIC const mp_rom_map_elem_t picoware_lcd_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_lcd)},

    // Display control
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_lcd_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_screen), MP_ROM_PTR(&picoware_lcd_clear_screen_obj)},
    {MP_ROM_QSTR(MP_QSTR_display_on), MP_ROM_PTR(&picoware_lcd_display_on_obj)},
    {MP_ROM_QSTR(MP_QSTR_display_off), MP_ROM_PTR(&picoware_lcd_display_off_obj)},

    // Blitting functions
    {MP_ROM_QSTR(MP_QSTR_blit_8bit), MP_ROM_PTR(&picoware_lcd_blit_8bit_obj)},
    {MP_ROM_QSTR(MP_QSTR_blit_8bit_fullscreen), MP_ROM_PTR(&picoware_lcd_blit_8bit_fullscreen_obj)},

    // Drawing functions
    {MP_ROM_QSTR(MP_QSTR_draw_pixel), MP_ROM_PTR(&picoware_lcd_draw_pixel_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_rect), MP_ROM_PTR(&picoware_lcd_fill_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_line), MP_ROM_PTR(&picoware_lcd_draw_line_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_line_custom), MP_ROM_PTR(&picoware_lcd_draw_line_custom_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_circle), MP_ROM_PTR(&picoware_lcd_draw_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_circle), MP_ROM_PTR(&picoware_lcd_fill_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_framebuffer), MP_ROM_PTR(&picoware_lcd_clear_framebuffer_obj)},

    // Font rendering functions
    {MP_ROM_QSTR(MP_QSTR_draw_char), MP_ROM_PTR(&picoware_lcd_draw_char_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_text), MP_ROM_PTR(&picoware_lcd_draw_text_obj)},

    // Constants
    {MP_ROM_QSTR(MP_QSTR_WIDTH), MP_ROM_INT(DISPLAY_WIDTH)},
    {MP_ROM_QSTR(MP_QSTR_HEIGHT), MP_ROM_INT(DISPLAY_HEIGHT)},
    {MP_ROM_QSTR(MP_QSTR_CHAR_WIDTH), MP_ROM_INT(CHAR_WIDTH)},
    {MP_ROM_QSTR(MP_QSTR_FONT_HEIGHT), MP_ROM_INT(FONT_HEIGHT)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lcd_module_globals, picoware_lcd_module_globals_table);

// Module definition
const mp_obj_module_t picoware_lcd_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_lcd_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_picoware_lcd, picoware_lcd_user_cmodule);
