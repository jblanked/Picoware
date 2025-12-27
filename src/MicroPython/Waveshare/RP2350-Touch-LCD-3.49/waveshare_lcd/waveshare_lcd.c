/*
 * Waveshare LCD Native C Extension for MicroPython
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

// Function to get backlight level
STATIC mp_obj_t waveshare_lcd_get_backlight_level(void)
{
    uint8_t level = lcd_get_backlight_level();
    return mp_obj_new_int(level);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_lcd_get_backlight_level_obj, waveshare_lcd_get_backlight_level);

// Function to initialize the LCD
STATIC mp_obj_t waveshare_lcd_init(void)
{
    lcd_init();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_lcd_init_obj, waveshare_lcd_init);

// Function to set backlight level
STATIC mp_obj_t waveshare_lcd_set_backlight_level(size_t n_args, const mp_obj_t *args)
{
    // Arguments: brightness
    if (n_args != 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("set_backlight_level requires 1 argument: brightness"));
    }
    uint8_t brightness = mp_obj_get_int(args[0]);
    lcd_set_backlight_level(brightness);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_set_backlight_level_obj, 1, 1, waveshare_lcd_set_backlight_level);

// Function to "swap" the framebuffer to the display
STATIC mp_obj_t waveshare_lcd_swap(void)
{
    lcd_swap();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_lcd_swap_obj, waveshare_lcd_swap);

// Draw pixel in 16-bit framebuffer
STATIC mp_obj_t waveshare_lcd_draw_pixel(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, color
    if (n_args != 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_pixel requires 3 arguments: x, y, color"));
    }

    uint16_t x = mp_obj_get_int(args[0]);
    uint16_t y = mp_obj_get_int(args[1]);
    uint16_t color = mp_obj_get_int(args[2]);

    lcd_draw_pixel(x, y, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_draw_pixel_obj, 3, 3, waveshare_lcd_draw_pixel);

// Fill the screen with a color
STATIC mp_obj_t waveshare_lcd_fill_screen(size_t n_args, const mp_obj_t *args)
{
    // Arguments: color
    if (n_args != 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_screen requires 1 argument: color"));
    }
    uint16_t color = mp_obj_get_int(args[0]);
    lcd_fill(color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_fill_screen_obj, 1, 1, waveshare_lcd_fill_screen);

// Blit a buffer to the framebuffer
STATIC mp_obj_t waveshare_lcd_blit(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, width, height, buffer
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("blit requires 5 arguments: x, y, width, height, buffer"));
    }

    uint16_t x = mp_obj_get_int(args[0]);
    uint16_t y = mp_obj_get_int(args[1]);
    uint16_t width = mp_obj_get_int(args[2]);
    uint16_t height = mp_obj_get_int(args[3]);

    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[4], &bufinfo, MP_BUFFER_READ);

    // Verify buffer size
    size_t expected_size = width * height * sizeof(uint8_t);
    if (bufinfo.len < expected_size)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("buffer too small for blit operation"));
    }

    lcd_blit(x, y, width, height, (uint8_t *)bufinfo.buf);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_blit_obj, 5, 5, waveshare_lcd_blit);

// Draw a line
STATIC mp_obj_t waveshare_lcd_draw_line(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x1, y1, x2, y2, color
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_line requires 5 arguments: x1, y1, x2, y2, color"));
    }

    uint16_t x1 = mp_obj_get_int(args[0]);
    uint16_t y1 = mp_obj_get_int(args[1]);
    uint16_t x2 = mp_obj_get_int(args[2]);
    uint16_t y2 = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    lcd_draw_line(x1, y1, x2, y2, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_draw_line_obj, 5, 5, waveshare_lcd_draw_line);

// Draw a rectangle (outline)
STATIC mp_obj_t waveshare_lcd_draw_rect(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, width, height, color
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_rect requires 5 arguments: x, y, width, height, color"));
    }

    uint16_t x = mp_obj_get_int(args[0]);
    uint16_t y = mp_obj_get_int(args[1]);
    uint16_t width = mp_obj_get_int(args[2]);
    uint16_t height = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    lcd_draw_rect(x, y, width, height, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_draw_rect_obj, 5, 5, waveshare_lcd_draw_rect);

// Fill a rectangle
STATIC mp_obj_t waveshare_lcd_fill_rect(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, width, height, color
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_rect requires 5 arguments: x, y, width, height, color"));
    }

    uint16_t x = mp_obj_get_int(args[0]);
    uint16_t y = mp_obj_get_int(args[1]);
    uint16_t width = mp_obj_get_int(args[2]);
    uint16_t height = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    lcd_fill_rect(x, y, width, height, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_fill_rect_obj, 5, 5, waveshare_lcd_fill_rect);

// Draw a circle (outline)
STATIC mp_obj_t waveshare_lcd_draw_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: center_x, center_y, radius, color
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_circle requires 4 arguments: center_x, center_y, radius, color"));
    }

    uint16_t center_x = mp_obj_get_int(args[0]);
    uint16_t center_y = mp_obj_get_int(args[1]);
    uint16_t radius = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    lcd_draw_circle(center_x, center_y, radius, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_draw_circle_obj, 4, 4, waveshare_lcd_draw_circle);

// Fill a circle
STATIC mp_obj_t waveshare_lcd_fill_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: center_x, center_y, radius, color
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_circle requires 4 arguments: center_x, center_y, radius, color"));
    }

    uint16_t center_x = mp_obj_get_int(args[0]);
    uint16_t center_y = mp_obj_get_int(args[1]);
    uint16_t radius = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    lcd_fill_circle(center_x, center_y, radius, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_fill_circle_obj, 4, 4, waveshare_lcd_fill_circle);

// Fill a triangle
STATIC mp_obj_t waveshare_lcd_fill_triangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x1, y1, x2, y2, x3, y3, color
    if (n_args != 7)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_triangle requires 7 arguments: x1, y1, x2, y2, x3, y3, color"));
    }

    uint16_t x1 = mp_obj_get_int(args[0]);
    uint16_t y1 = mp_obj_get_int(args[1]);
    uint16_t x2 = mp_obj_get_int(args[2]);
    uint16_t y2 = mp_obj_get_int(args[3]);
    uint16_t x3 = mp_obj_get_int(args[4]);
    uint16_t y3 = mp_obj_get_int(args[5]);
    uint16_t color = mp_obj_get_int(args[6]);

    lcd_fill_triangle(x1, y1, x2, y2, x3, y3, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_fill_triangle_obj, 7, 7, waveshare_lcd_fill_triangle);

// Draw a single character
STATIC mp_obj_t waveshare_lcd_draw_char(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, char, color
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_char requires 4 arguments: x, y, char, color"));
    }

    uint16_t x = mp_obj_get_int(args[0]);
    uint16_t y = mp_obj_get_int(args[1]);

    const char *str = mp_obj_str_get_str(args[2]);
    if (strlen(str) != 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_char requires a single character string"));
    }
    char c = str[0];

    uint16_t color = mp_obj_get_int(args[3]);

    lcd_draw_char(x, y, c, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_draw_char_obj, 4, 4, waveshare_lcd_draw_char);

// Draw text
STATIC mp_obj_t waveshare_lcd_draw_text(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, text, color
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_text requires 4 arguments: x, y, text, color"));
    }

    uint16_t x = mp_obj_get_int(args[0]);
    uint16_t y = mp_obj_get_int(args[1]);
    const char *text = mp_obj_str_get_str(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    lcd_draw_text(x, y, text, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_draw_text_obj, 4, 4, waveshare_lcd_draw_text);

// Get font size (as a tuple)
STATIC mp_obj_t waveshare_lcd_get_font_size(void)
{
    uint8_t width = lcd_get_font_width();
    uint8_t height = lcd_get_font_height();
    mp_obj_t tuple[2] = {mp_obj_new_int(width), mp_obj_new_int(height)};
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_lcd_get_font_size_obj, waveshare_lcd_get_font_size);

// Set font size
STATIC mp_obj_t waveshare_lcd_set_font(size_t n_args, const mp_obj_t *args)
{
    // Arguments: font_size (0-4)
    if (n_args != 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("set_font requires 1 argument: font_size (0-4)"));
    }

    int font_size = mp_obj_get_int(args[0]);
    if (font_size < 0 || font_size > 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("font_size must be between 0 (FONT_XTRA_SMALL) and 4 (FONT_XTRA_LARGE)"));
    }

    lcd_set_font((FontSize)font_size);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_lcd_set_font_obj, 1, 1, waveshare_lcd_set_font);

// Module globals table
STATIC const mp_rom_map_elem_t waveshare_lcd_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_waveshare_lcd)},

    // Display control
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&waveshare_lcd_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_swap), MP_ROM_PTR(&waveshare_lcd_swap_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_backlight_level), MP_ROM_PTR(&waveshare_lcd_get_backlight_level_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_backlight_level), MP_ROM_PTR(&waveshare_lcd_set_backlight_level_obj)},

    // Framebuffer drawing functions
    {MP_ROM_QSTR(MP_QSTR_draw_pixel), MP_ROM_PTR(&waveshare_lcd_draw_pixel_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_screen), MP_ROM_PTR(&waveshare_lcd_fill_screen_obj)},
    {MP_ROM_QSTR(MP_QSTR_blit), MP_ROM_PTR(&waveshare_lcd_blit_obj)},

    // Shape drawing functions
    {MP_ROM_QSTR(MP_QSTR_draw_line), MP_ROM_PTR(&waveshare_lcd_draw_line_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_rect), MP_ROM_PTR(&waveshare_lcd_draw_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_rect), MP_ROM_PTR(&waveshare_lcd_fill_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_circle), MP_ROM_PTR(&waveshare_lcd_draw_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_circle), MP_ROM_PTR(&waveshare_lcd_fill_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_triangle), MP_ROM_PTR(&waveshare_lcd_fill_triangle_obj)},

    // Text rendering functions
    {MP_ROM_QSTR(MP_QSTR_draw_char), MP_ROM_PTR(&waveshare_lcd_draw_char_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_text), MP_ROM_PTR(&waveshare_lcd_draw_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_font_size), MP_ROM_PTR(&waveshare_lcd_get_font_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_font), MP_ROM_PTR(&waveshare_lcd_set_font_obj)},

    // Font size constants
    {MP_ROM_QSTR(MP_QSTR_FONT_XTRA_SMALL), MP_ROM_INT(0)},
    {MP_ROM_QSTR(MP_QSTR_FONT_SMALL), MP_ROM_INT(1)},
    {MP_ROM_QSTR(MP_QSTR_FONT_MEDIUM), MP_ROM_INT(2)},
    {MP_ROM_QSTR(MP_QSTR_FONT_LARGE), MP_ROM_INT(3)},
    {MP_ROM_QSTR(MP_QSTR_FONT_XTRA_LARGE), MP_ROM_INT(4)},

    // Color constants (RGB565)
    {MP_ROM_QSTR(MP_QSTR_COLOR_WHITE), MP_ROM_INT(0xFFFF)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_BLACK), MP_ROM_INT(0x0000)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_BLUE), MP_ROM_INT(0x001F)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_CYAN), MP_ROM_INT(0x07FF)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_RED), MP_ROM_INT(0xF800)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_LIGHTGREY), MP_ROM_INT(0xD69A)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_DARKGREY), MP_ROM_INT(0x7BEF)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_GREEN), MP_ROM_INT(0x07E0)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_DARKCYAN), MP_ROM_INT(0x03EF)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_DARKGREEN), MP_ROM_INT(0x03E0)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_SKYBLUE), MP_ROM_INT(0x867D)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_VIOLET), MP_ROM_INT(0x915C)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_BROWN), MP_ROM_INT(0x9A60)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_TRANSPARENT), MP_ROM_INT(0x0120)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_YELLOW), MP_ROM_INT(0xFFE0)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_ORANGE), MP_ROM_INT(0xFDA0)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_PINK), MP_ROM_INT(0xFE19)},

    // Display dimensions
    {MP_ROM_QSTR(MP_QSTR_LCD_WIDTH), MP_ROM_INT(LCD_WIDTH)},
    {MP_ROM_QSTR(MP_QSTR_LCD_HEIGHT), MP_ROM_INT(LCD_HEIGHT)},
};
STATIC MP_DEFINE_CONST_DICT(waveshare_lcd_module_globals, waveshare_lcd_module_globals_table);

// Module definition
const mp_obj_module_t waveshare_lcd_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&waveshare_lcd_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_waveshare_lcd, waveshare_lcd_user_cmodule);