#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "stdio.h"
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "lcd.h"
#include "colors.h"

#ifndef STATIC
#define STATIC static
#endif

typedef struct
{
    mp_obj_base_t base;
    uint8_t brightness; // Store current brightness level (0-100)
} lcd_mp_obj_t;

const mp_obj_type_t lcd_mp_type;

STATIC void lcd_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "LCD(");
    mp_print_str(print, "brightness=");
    mp_obj_print_helper(print, mp_obj_new_int(self->brightness), PRINT_REPR);
    mp_print_str(print, ")");
}

STATIC mp_obj_t lcd_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    (void)type;
    (void)n_args;
    (void)n_kw;
    (void)args;
    lcd_mp_obj_t *self = mp_obj_malloc_with_finaliser(lcd_mp_obj_t, &lcd_mp_type);
    self->base.type = &lcd_mp_type;
    if (!lcd_init())
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to initialize LCD"));
    }
    /* Set default brightness so the backlight is on after init.
     * lcd_init() leaves the backlight at 0 (off). */
    self->brightness = LCD_DEFAULT_BRIGHTNESS;
    lcd_set_backlight(self->brightness);
    return MP_OBJ_FROM_PTR(self);
}

STATIC mp_obj_t lcd_mp_del(mp_obj_t self_in)
{
    (void)self_in;
    lcd_deinit();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(lcd_mp_del_obj, lcd_mp_del);

STATIC void lcd_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&lcd_mp_del_obj);
        }
        else if (attribute == MP_QSTR_brightness)
        {
            destination[0] = mp_obj_new_int(self->brightness);
        }
        else if (attribute == MP_QSTR_width)
        {
            destination[0] = mp_obj_new_int(LCD_WIDTH);
        }
        else if (attribute == MP_QSTR_height)
        {
            destination[0] = mp_obj_new_int(LCD_HEIGHT);
        }
        else if (attribute == MP_QSTR_scale_x || attribute == MP_QSTR_scale_y)
        {
            destination[0] = mp_obj_new_float(1.0f);
        }
        else if (attribute == MP_QSTR_scale_set || attribute == MP_QSTR_scale_position)
        {
            destination[0] = mp_obj_new_bool(false);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_brightness)
        {
            int brightness = mp_obj_get_int(destination[1]);
            if (brightness < 0 || brightness > 100)
            {
                mp_raise_ValueError(MP_ERROR_TEXT("Brightness must be between 0 and 100"));
            }
            self->brightness = (uint8_t)brightness;
            lcd_set_backlight(self->brightness);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_scale_x ||
                 attribute == MP_QSTR_scale_y ||
                 attribute == MP_QSTR_scale_position)
        {
            // Scaling is currently handled in Python layer for CrowPanel.
            destination[0] = MP_OBJ_NULL;
        }
    }
}

STATIC mp_obj_t lcd_mp_swap(mp_obj_t self_in)
{
    (void)self_in;
    lcd_swap();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(lcd_mp_swap_obj, lcd_mp_swap);

STATIC mp_obj_t lcd_mp_draw_pixel(size_t n_args, const mp_obj_t *args)
{
    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);
    lcd_draw_pixel(x, y, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_draw_pixel_obj, 4, 4, lcd_mp_draw_pixel);

STATIC mp_obj_t lcd_mp_fill(mp_obj_t self_in, mp_obj_t color_in)
{
    (void)self_in;
    uint16_t color = mp_obj_get_int(color_in);
    lcd_fill(color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(lcd_mp_fill_obj, lcd_mp_fill);

STATIC mp_obj_t lcd_mp_blit(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x, args[2] is y, args[3] is width, args[4] is height, args[5] is buffer
    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[5], &bufinfo, MP_BUFFER_READ);
    if (bufinfo.len < width * height * sizeof(uint16_t))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Buffer size is too small for specified width and height"));
    }
    lcd_blit(x, y, width, height, (const uint16_t *)bufinfo.buf);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_blit_obj, 6, 6, lcd_mp_blit);

STATIC mp_obj_t lcd_mp_draw_line(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x1, args[2] is y1, args[3] is x2, args[4] is y2, args[5] is color
    uint16_t x1 = mp_obj_get_int(args[1]);
    uint16_t y1 = mp_obj_get_int(args[2]);
    uint16_t x2 = mp_obj_get_int(args[3]);
    uint16_t y2 = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);
    lcd_draw_line(x1, y1, x2, y2, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_draw_line_obj, 6, 6, lcd_mp_draw_line);

STATIC mp_obj_t lcd_mp_draw_rect(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x, args[2] is y, args[3] is width, args[4] is height, args[5] is color
    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);
    lcd_draw_rect(x, y, width, height, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_draw_rect_obj, 6, 6, lcd_mp_draw_rect);

STATIC mp_obj_t lcd_mp_fill_rect(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x, args[2] is y, args[3] is width, args[4] is height, args[5] is color
    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);
    lcd_fill_rect(x, y, width, height, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_rect_obj, 6, 6, lcd_mp_fill_rect);

STATIC mp_obj_t lcd_mp_draw_circle(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is center_x, args[2] is center_y, args[3] is radius, args[4] is color
    uint16_t center_x = mp_obj_get_int(args[1]);
    uint16_t center_y = mp_obj_get_int(args[2]);
    uint16_t radius = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);
    lcd_draw_circle(center_x, center_y, radius, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_draw_circle_obj, 5, 5, lcd_mp_draw_circle);

STATIC mp_obj_t lcd_mp_fill_circle(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is center_x, args[2] is center_y, args[3] is radius, args[4] is color
    uint16_t center_x = mp_obj_get_int(args[1]);
    uint16_t center_y = mp_obj_get_int(args[2]);
    uint16_t radius = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);
    lcd_fill_circle(center_x, center_y, radius, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_circle_obj, 5, 5, lcd_mp_fill_circle);

STATIC mp_obj_t lcd_mp_fill_triangle(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x1, args[2] is y1, args[3] is x2, args[4] is y2, args[5] is x3, args[6] is y3, args[7] is color
    uint16_t x1 = mp_obj_get_int(args[1]);
    uint16_t y1 = mp_obj_get_int(args[2]);
    uint16_t x2 = mp_obj_get_int(args[3]);
    uint16_t y2 = mp_obj_get_int(args[4]);
    uint16_t x3 = mp_obj_get_int(args[5]);
    uint16_t y3 = mp_obj_get_int(args[6]);
    uint16_t color = mp_obj_get_int(args[7]);
    lcd_fill_triangle(x1, y1, x2, y2, x3, y3, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_triangle_obj, 8, 8, lcd_mp_fill_triangle);

STATIC mp_obj_t lcd_mp_draw_triangle(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x1, args[2] is y1, args[3] is x2, args[4] is y2, args[5] is x3, args[6] is y3, args[7] is color
    uint16_t x1 = mp_obj_get_int(args[1]);
    uint16_t y1 = mp_obj_get_int(args[2]);
    uint16_t x2 = mp_obj_get_int(args[3]);
    uint16_t y2 = mp_obj_get_int(args[4]);
    uint16_t x3 = mp_obj_get_int(args[5]);
    uint16_t y3 = mp_obj_get_int(args[6]);
    uint16_t color = mp_obj_get_int(args[7]);
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_draw_triangle_obj, 8, 8, lcd_mp_draw_triangle);

STATIC mp_obj_t lcd_mp_fill_round_rect(size_t n_args, const mp_obj_t *args)
{
    // Basic fallback implementation: rounded rectangles are approximated as filled rectangles.
    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[6]);
    lcd_fill_rect(x, y, width, height, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_round_rect_obj, 7, 7, lcd_mp_fill_round_rect);

STATIC mp_obj_t lcd_mp_draw_char(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x, args[2] is y, args[3] is c, args[4] is color, args[5] is optional font size
    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    const char *str = mp_obj_str_get_str(args[3]);
    char c = str[0];
    uint16_t color = mp_obj_get_int(args[4]);
    if (n_args >= 6)
    {
        lcd_set_font((FontSize)mp_obj_get_int(args[5]));
    }
    lcd_draw_char(x, y, c, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_draw_char_obj, 5, 6, lcd_mp_draw_char);

STATIC mp_obj_t lcd_mp_draw_text(size_t n_args, const mp_obj_t *args)
{
    // args[0] is self, args[1] is x, args[2] is y, args[3] is text, args[4] is color, args[5] is optional font size
    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    const char *text = mp_obj_str_get_str(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);
    if (n_args >= 6)
    {
        lcd_set_font((FontSize)mp_obj_get_int(args[5]));
    }
    lcd_draw_text(x, y, text, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_draw_text_obj, 5, 6, lcd_mp_draw_text);

STATIC mp_obj_t lcd_mp_set_scaling(size_t n_args, const mp_obj_t *args)
{
    (void)n_args;
    (void)args;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_set_scaling_obj, 4, 4, lcd_mp_set_scaling);

STATIC mp_obj_t lcd_mp_set_mode(mp_obj_t self_in, mp_obj_t mode_in)
{
    (void)self_in;
    (void)mode_in;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(lcd_mp_set_mode_obj, lcd_mp_set_mode);

STATIC mp_obj_t lcd_mp_psram(size_t n_args, const mp_obj_t *args)
{
    (void)n_args;
    (void)args;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_psram_obj, 6, 6, lcd_mp_psram);

STATIC mp_obj_t lcd_mp_get_font_height(mp_obj_t self_in)
{
    (void)self_in;
    return mp_obj_new_int(lcd_get_font_height());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(lcd_mp_get_font_height_obj, lcd_mp_get_font_height);

STATIC mp_obj_t lcd_mp_get_font_width(mp_obj_t self_in)
{
    (void)self_in;
    return mp_obj_new_int(lcd_get_font_width());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(lcd_mp_get_font_width_obj, lcd_mp_get_font_width);

STATIC mp_obj_t lcd_mp_set_font(mp_obj_t self_in, mp_obj_t size_in)
{
    (void)self_in;
    int size = mp_obj_get_int(size_in);
    lcd_set_font((FontSize)size);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(lcd_mp_set_font_obj, lcd_mp_set_font);

STATIC const mp_rom_map_elem_t lcd_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_swap), MP_ROM_PTR(&lcd_mp_swap_obj)},
    {MP_ROM_QSTR(MP_QSTR_pixel), MP_ROM_PTR(&lcd_mp_draw_pixel_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill), MP_ROM_PTR(&lcd_mp_fill_obj)},
    {MP_ROM_QSTR(MP_QSTR_blit), MP_ROM_PTR(&lcd_mp_blit_obj)},
    {MP_ROM_QSTR(MP_QSTR_line), MP_ROM_PTR(&lcd_mp_draw_line_obj)},
    {MP_ROM_QSTR(MP_QSTR_rect), MP_ROM_PTR(&lcd_mp_draw_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_rect), MP_ROM_PTR(&lcd_mp_fill_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR_circle), MP_ROM_PTR(&lcd_mp_draw_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_circle), MP_ROM_PTR(&lcd_mp_fill_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_triangle), MP_ROM_PTR(&lcd_mp_fill_triangle_obj)},
    {MP_ROM_QSTR(MP_QSTR_char), MP_ROM_PTR(&lcd_mp_draw_char_obj)},
    {MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&lcd_mp_draw_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_font_height), MP_ROM_PTR(&lcd_mp_get_font_height_obj)},
    {MP_ROM_QSTR(MP_QSTR_font_width), MP_ROM_PTR(&lcd_mp_get_font_width_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_font), MP_ROM_PTR(&lcd_mp_set_font_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_scaling), MP_ROM_PTR(&lcd_mp_set_scaling_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_mode), MP_ROM_PTR(&lcd_mp_set_mode_obj)},
    // Compatibility aliases used by Picoware's Draw wrapper.
    {MP_ROM_QSTR(MP_QSTR__char), MP_ROM_PTR(&lcd_mp_draw_char_obj)},
    {MP_ROM_QSTR(MP_QSTR__circle), MP_ROM_PTR(&lcd_mp_draw_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR__clear), MP_ROM_PTR(&lcd_mp_fill_obj)},
    {MP_ROM_QSTR(MP_QSTR__fill_circle), MP_ROM_PTR(&lcd_mp_fill_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR__fill_rectangle), MP_ROM_PTR(&lcd_mp_fill_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR__fill_round_rectangle), MP_ROM_PTR(&lcd_mp_fill_round_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR__fill_triangle), MP_ROM_PTR(&lcd_mp_fill_triangle_obj)},
    {MP_ROM_QSTR(MP_QSTR__bytearray), MP_ROM_PTR(&lcd_mp_blit_obj)},
    {MP_ROM_QSTR(MP_QSTR__line), MP_ROM_PTR(&lcd_mp_draw_line_obj)},
    {MP_ROM_QSTR(MP_QSTR__pixel), MP_ROM_PTR(&lcd_mp_draw_pixel_obj)},
    {MP_ROM_QSTR(MP_QSTR__psram), MP_ROM_PTR(&lcd_mp_psram_obj)},
    {MP_ROM_QSTR(MP_QSTR__rectangle), MP_ROM_PTR(&lcd_mp_draw_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR__text), MP_ROM_PTR(&lcd_mp_draw_text_obj)},
    {MP_ROM_QSTR(MP_QSTR__triangle), MP_ROM_PTR(&lcd_mp_draw_triangle_obj)},
};
STATIC MP_DEFINE_CONST_DICT(lcd_mp_locals_dict, lcd_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lcd_mp_type,
    MP_QSTR_LCD,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, lcd_mp_print,
    make_new, lcd_mp_make_new,
    attr, lcd_mp_attr,
    locals_dict, &lcd_mp_locals_dict);

STATIC const mp_rom_map_elem_t lcd_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lcd)},
    {MP_ROM_QSTR(MP_QSTR_WIDTH), MP_ROM_INT(LCD_WIDTH)},
    {MP_ROM_QSTR(MP_QSTR_HEIGHT), MP_ROM_INT(LCD_HEIGHT)},
    {MP_ROM_QSTR(MP_QSTR_BACKLIGHT_PIN), MP_ROM_INT(LCD_BACKLIGHT_PIN)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_WHITE), MP_ROM_INT(COLOR_WHITE)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_BLACK), MP_ROM_INT(COLOR_BLACK)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_BLUE), MP_ROM_INT(COLOR_BLUE)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_CYAN), MP_ROM_INT(COLOR_CYAN)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_RED), MP_ROM_INT(COLOR_RED)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_LIGHTGREY), MP_ROM_INT(COLOR_LIGHTGREY)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_DARKGREY), MP_ROM_INT(COLOR_DARKGREY)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_GREEN), MP_ROM_INT(COLOR_GREEN)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_DARKCYAN), MP_ROM_INT(COLOR_DARKCYAN)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_DARKGREEN), MP_ROM_INT(COLOR_DARKGREEN)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_SKYBLUE), MP_ROM_INT(COLOR_SKYBLUE)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_VIOLET), MP_ROM_INT(COLOR_VIOLET)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_BROWN), MP_ROM_INT(COLOR_BROWN)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_TRANSPARENT), MP_ROM_INT(COLOR_TRANSPARENT)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_YELLOW), MP_ROM_INT(COLOR_YELLOW)},
    {MP_ROM_QSTR(MP_QSTR_COLOR_PINK), MP_ROM_INT(COLOR_PINK)},
    {MP_ROM_QSTR(MP_QSTR_FONT_XTRA_SMALL), MP_ROM_INT(FONT_XTRA_SMALL)},
    {MP_ROM_QSTR(MP_QSTR_FONT_SMALL), MP_ROM_INT(FONT_SMALL)},
    {MP_ROM_QSTR(MP_QSTR_FONT_MEDIUM), MP_ROM_INT(FONT_MEDIUM)},
    {MP_ROM_QSTR(MP_QSTR_FONT_LARGE), MP_ROM_INT(FONT_LARGE)},
    {MP_ROM_QSTR(MP_QSTR_FONT_XTRA_LARGE), MP_ROM_INT(FONT_XTRA_LARGE)},
    {MP_ROM_QSTR(MP_QSTR_FONT_DEFAULT), MP_ROM_INT(FONT_MEDIUM)},
    {MP_ROM_QSTR(MP_QSTR_LCD), MP_ROM_PTR(&lcd_mp_type)},
};
STATIC MP_DEFINE_CONST_DICT(lcd_module_globals, lcd_module_globals_table);

// Define module
const mp_obj_module_t lcd_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&lcd_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_lcd, lcd_user_cmodule);