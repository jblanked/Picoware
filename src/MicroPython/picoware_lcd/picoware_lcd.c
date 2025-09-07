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

// Module state
static bool module_initialized = false;

// Function to initialize the LCD
STATIC mp_obj_t picoware_lcd_init(void)
{
    if (!module_initialized)
    {
        lcd_init();
        module_initialized = true;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_init_obj, picoware_lcd_init);

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

    // Constants
    {MP_ROM_QSTR(MP_QSTR_WIDTH), MP_ROM_INT(DISPLAY_WIDTH)},
    {MP_ROM_QSTR(MP_QSTR_HEIGHT), MP_ROM_INT(DISPLAY_HEIGHT)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lcd_module_globals, picoware_lcd_module_globals_table);

// Module definition
const mp_obj_module_t picoware_lcd_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_lcd_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_picoware_lcd, picoware_lcd_user_cmodule);
