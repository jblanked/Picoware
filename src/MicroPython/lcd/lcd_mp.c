#include "lcd_mp.h"
#include LCD_INCLUDE

const mp_obj_type_t lcd_mp_type;

void lcd_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "LCD(");
    if (self->initialized)
    {
        mp_print_str(print, "width=");
        mp_obj_print_helper(print, mp_obj_new_int(self->width), PRINT_REPR);
        mp_print_str(print, ", height=");
        mp_obj_print_helper(print, mp_obj_new_int(self->height), PRINT_REPR);
    }
    else
    {
        mp_print_str(print, "uninitialized");
    }
    mp_print_str(print, ")");
}

mp_obj_t lcd_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    lcd_mp_obj_t *self = mp_obj_malloc(lcd_mp_obj_t, type);
    self->width = LCD_MP_WIDTH;
    self->height = LCD_MP_HEIGHT;
    LCD_MP_INIT();
    self->initialized = true;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t lcd_mp_del(mp_obj_t self_in)
{
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->initialized)
    {
#ifdef LCD_MP_DEINIT
        LCD_MP_DEINIT();
#endif
        self->initialized = false;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(lcd_mp_del_obj, lcd_mp_del);

void lcd_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // load attribute
        if (attribute == MP_QSTR_width)
        {
            destination[0] = mp_obj_new_int(self->width);
        }
        else if (attribute == MP_QSTR_height)
        {
            destination[0] = mp_obj_new_int(self->height);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&lcd_mp_del_obj);
        }
    }
}

mp_obj_t lcd_mp_char(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, char, color, font_size (optional)
    if (n_args < 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("char requires at least 5 arguments: self, x, y, char, color, [font_size]"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);

    const char *str = mp_obj_str_get_str(args[3]);
    if (strlen(str) != 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("char requires a single character string"));
    }
    char c = str[0];

    uint16_t color = mp_obj_get_int(args[4]);
    uint8_t font_size = 0; // Default font size
    if (n_args == 6)
    {
        font_size = mp_obj_get_int(args[5]);
    }

    LCD_MP_CHAR(x, y, c, color, font_size);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_char_obj, 5, 6, lcd_mp_char);

mp_obj_t lcd_mp_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, center_x, center_y, radius, color
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("circle requires 5 arguments: self, center_x, center_y, radius, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t center_x = mp_obj_get_int(args[1]);
    uint16_t center_y = mp_obj_get_int(args[2]);
    uint16_t radius = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    LCD_MP_CIRCLE(center_x, center_y, radius, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_circle_obj, 5, 5, lcd_mp_circle);

mp_obj_t lcd_mp_clear(mp_obj_t self_in, mp_obj_t color)
{
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }
    uint16_t clr = mp_obj_get_int(color);
    LCD_MP_CLEAR(clr);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(lcd_mp_clear_obj, lcd_mp_clear);

mp_obj_t lcd_mp_fill_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, center_x, center_y, radius, color
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_circle requires 5 arguments: self, center_x, center_y, radius, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t center_x = mp_obj_get_int(args[1]);
    uint16_t center_y = mp_obj_get_int(args[2]);
    uint16_t radius = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    LCD_MP_FILL_CIRCLE(center_x, center_y, radius, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_circle_obj, 5, 5, lcd_mp_fill_circle);

mp_obj_t lcd_mp_fill_rectangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, width, height, color
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_rectangle requires 6 arguments: self, x, y, width, height, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);

    LCD_MP_FILL_RECTANGLE(x, y, width, height, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_rectangle_obj, 6, 6, lcd_mp_fill_rectangle);

mp_obj_t lcd_mp_fill_round_rectangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, width, height, radius, color
    if (n_args != 7)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_round_rectangle requires 7 arguments: self, x, y, width, height, radius, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);
    uint16_t radius = mp_obj_get_int(args[5]);
    uint16_t color = mp_obj_get_int(args[6]);

    LCD_MP_FILL_ROUND_RECTANGLE(x, y, width, height, radius, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_round_rectangle_obj, 7, 7, lcd_mp_fill_round_rectangle);

mp_obj_t lcd_mp_fill_triangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x1, y1, x2, y2, x3, y3, color
    if (n_args != 8)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_triangle requires 8 arguments: self, x1, y1, x2, y2, x3, y3, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x1 = mp_obj_get_int(args[1]);
    uint16_t y1 = mp_obj_get_int(args[2]);
    uint16_t x2 = mp_obj_get_int(args[3]);
    uint16_t y2 = mp_obj_get_int(args[4]);
    uint16_t x3 = mp_obj_get_int(args[5]);
    uint16_t y3 = mp_obj_get_int(args[6]);
    uint16_t color = mp_obj_get_int(args[7]);

    LCD_MP_FILL_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_fill_triangle_obj, 8, 8, lcd_mp_fill_triangle);

mp_obj_t lcd_mp_image_bytearray(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, width, height, buffer
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("blit requires 6 arguments: self, x, y, width, height, buffer"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);

    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[5], &bufinfo, MP_BUFFER_READ);

    // Verify buffer size
    size_t expected_size_8bit = width * height * sizeof(uint8_t);
    size_t expected_size_16bit = width * height * sizeof(uint16_t);
    if (bufinfo.len < expected_size_8bit && bufinfo.len < expected_size_16bit)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("buffer too small for blit operation"));
    }

    if (bufinfo.len == expected_size_16bit)
    {
        LCD_MP_BLIT_16BIT(x, y, width, height, (uint16_t *)bufinfo.buf);
    }
    else if (bufinfo.len == expected_size_8bit)
    {
        LCD_MP_BLIT(x, y, width, height, (uint8_t *)bufinfo.buf);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_image_bytearray_obj, 6, 6, lcd_mp_image_bytearray);

mp_obj_t lcd_mp_line(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x1, y1, x2, y2, color
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("line requires 6 arguments: self, x1, y1, x2, y2, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x1 = mp_obj_get_int(args[1]);
    uint16_t y1 = mp_obj_get_int(args[2]);
    uint16_t x2 = mp_obj_get_int(args[3]);
    uint16_t y2 = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);

    LCD_MP_LINE(x1, y1, x2, y2, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_line_obj, 6, 6, lcd_mp_line);

mp_obj_t lcd_mp_pixel(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, color
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("pixel requires 4 arguments: self, x, y, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }
    uint16_t x_val = mp_obj_get_int(args[1]);
    uint16_t y_val = mp_obj_get_int(args[2]);
    uint16_t color_val = mp_obj_get_int(args[3]);

    LCD_MP_PIXEL(x_val, y_val, color_val);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_pixel_obj, 4, 4, lcd_mp_pixel);

mp_obj_t lcd_mp_rectangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, width, height, color
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("rectangle requires 6 arguments: self, x, y, width, height, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    uint16_t width = mp_obj_get_int(args[3]);
    uint16_t height = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);

    LCD_MP_RECTANGLE(x, y, width, height, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_rectangle_obj, 6, 6, lcd_mp_rectangle);

mp_obj_t lcd_mp_set_mode(mp_obj_t self_in, mp_obj_t mode)
{
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }
    uint8_t mode_val = mp_obj_get_int(mode);
#ifdef LCD_MP_SET_MODE
    LCD_MP_SET_MODE(mode_val);
#else
    (void)mode_val;
#endif
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(lcd_mp_set_mode_obj, lcd_mp_set_mode);

mp_obj_t lcd_mp_swap(mp_obj_t self_in)
{
    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }
    LCD_MP_SWAP();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(lcd_mp_swap_obj, lcd_mp_swap);

mp_obj_t lcd_mp_text(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x, y, text, color, font_size (optional)
    if (n_args < 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_text requires at least 5 arguments: self, x, y, text, color, [font_size]"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x = mp_obj_get_int(args[1]);
    uint16_t y = mp_obj_get_int(args[2]);
    const char *text = mp_obj_str_get_str(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);
    uint8_t font_size = 0; // Default font size
    if (n_args == 6)
    {
        font_size = mp_obj_get_int(args[5]);
    }

    LCD_MP_TEXT(x, y, text, color, font_size);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_text_obj, 5, 6, lcd_mp_text);

mp_obj_t lcd_mp_triangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, x1, y1, x2, y2, x3, y3, color
    if (n_args != 8)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("triangle requires 8 arguments: self, x1, y1, x2, y2, x3, y3, color"));
    }

    lcd_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("LCD object is not initialized"));
    }

    uint16_t x1 = mp_obj_get_int(args[1]);
    uint16_t y1 = mp_obj_get_int(args[2]);
    uint16_t x2 = mp_obj_get_int(args[3]);
    uint16_t y2 = mp_obj_get_int(args[4]);
    uint16_t x3 = mp_obj_get_int(args[5]);
    uint16_t y3 = mp_obj_get_int(args[6]);
    uint16_t color = mp_obj_get_int(args[7]);

    LCD_MP_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_mp_triangle_obj, 8, 8, lcd_mp_triangle);

STATIC const mp_rom_map_elem_t lcd_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR__char), MP_ROM_PTR(&lcd_mp_char_obj)},                                 // self._char()
    {MP_ROM_QSTR(MP_QSTR__circle), MP_ROM_PTR(&lcd_mp_circle_obj)},                             // self._circle()
    {MP_ROM_QSTR(MP_QSTR__clear), MP_ROM_PTR(&lcd_mp_clear_obj)},                               // self._clear()
    {MP_ROM_QSTR(MP_QSTR__fill_circle), MP_ROM_PTR(&lcd_mp_fill_circle_obj)},                   // self._fill_circle()
    {MP_ROM_QSTR(MP_QSTR__fill_rectangle), MP_ROM_PTR(&lcd_mp_fill_rectangle_obj)},             // self._fill_rectangle()
    {MP_ROM_QSTR(MP_QSTR__fill_round_rectangle), MP_ROM_PTR(&lcd_mp_fill_round_rectangle_obj)}, // self._fill_round_rectangle()
    {MP_ROM_QSTR(MP_QSTR__fill_triangle), MP_ROM_PTR(&lcd_mp_fill_triangle_obj)},               // self._fill_triangle()
    {MP_ROM_QSTR(MP_QSTR__bytearray), MP_ROM_PTR(&lcd_mp_image_bytearray_obj)},                 // self._bytearray()
    {MP_ROM_QSTR(MP_QSTR__line), MP_ROM_PTR(&lcd_mp_line_obj)},                                 // self._line()
    {MP_ROM_QSTR(MP_QSTR__pixel), MP_ROM_PTR(&lcd_mp_pixel_obj)},                               // self._pixel()
    {MP_ROM_QSTR(MP_QSTR__rectangle), MP_ROM_PTR(&lcd_mp_rectangle_obj)},                       // self._rectangle()
    {MP_ROM_QSTR(MP_QSTR_set_mode), MP_ROM_PTR(&lcd_mp_set_mode_obj)},                          // self.set_mode()
    {MP_ROM_QSTR(MP_QSTR_swap), MP_ROM_PTR(&lcd_mp_swap_obj)},                                  // self.swap()
    {MP_ROM_QSTR(MP_QSTR__text), MP_ROM_PTR(&lcd_mp_text_obj)},                                 // self._text()
    {MP_ROM_QSTR(MP_QSTR__triangle), MP_ROM_PTR(&lcd_mp_triangle_obj)},                         // self._triangle()

    {MP_ROM_QSTR(MP_QSTR_FONT_DEFAULT), MP_ROM_INT(FONT_DEFAULT)},
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

// Define module globals
STATIC const mp_rom_map_elem_t lcd_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lcd)},
    {MP_ROM_QSTR(MP_QSTR_LCD), MP_ROM_PTR(&lcd_mp_type)},
};
STATIC MP_DEFINE_CONST_DICT(lcd_mp_globals, lcd_mp_globals_table);

// Define module
const mp_obj_module_t lcd_mp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&lcd_mp_globals,
};
// Register the module to make it available in Python
MP_REGISTER_MODULE(MP_QSTR_lcd, lcd_mp_module);