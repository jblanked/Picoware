#include "desktop_bridge.h"

#include <string.h>

#include "py/objstr.h"
#include "py/runtime.h"

static mp_obj_t desktop_import(qstr module_name)
{
    return mp_import_name(module_name, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
}

static mp_obj_t desktop_call_function_0(mp_obj_t object, qstr name)
{
    mp_obj_t destination[2];
    mp_load_method(object, name, destination);
    return mp_call_method_n_kw(0, 0, destination);
}

static mp_obj_t desktop_lcd(void)
{
    mp_obj_t runtime = desktop_import(MP_QSTR_sim_runtime);
    return desktop_call_function_0(runtime, MP_QSTR_get_lcd);
}

static void desktop_call_lcd(qstr name, size_t argument_count,
                             const mp_obj_t *arguments)
{
    mp_obj_t lcd = desktop_lcd();
    if (lcd == mp_const_none)
        return;

    mp_obj_t destination[11];
    mp_load_method(lcd, name, destination);
    for (size_t index = 0; index < argument_count; index++)
        destination[index + 2] = arguments[index];
    mp_call_method_n_kw(argument_count, 0, destination);
}

void desktop_lcd_clear(uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__clear, 1, arguments);
}

void desktop_lcd_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    mp_obj_t arguments[] = {
        mp_obj_new_int(x), mp_obj_new_int(y), mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__pixel, 3, arguments);
}

void desktop_lcd_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                      uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(x1), mp_obj_new_int(y1),
                            mp_obj_new_int(x2), mp_obj_new_int(y2),
                            mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__line, 5, arguments);
}

void desktop_lcd_rectangle(uint16_t x, uint16_t y, uint16_t width,
                           uint16_t height, uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(x), mp_obj_new_int(y),
                            mp_obj_new_int(width), mp_obj_new_int(height),
                            mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__rectangle, 5, arguments);
}

void desktop_lcd_fill_rectangle(uint16_t x, uint16_t y, uint16_t width,
                                uint16_t height, uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(x), mp_obj_new_int(y),
                            mp_obj_new_int(width), mp_obj_new_int(height),
                            mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__fill_rectangle, 5, arguments);
}

void desktop_lcd_circle(uint16_t x, uint16_t y, uint16_t radius,
                        uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(x), mp_obj_new_int(y),
                            mp_obj_new_int(radius), mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__circle, 4, arguments);
}

void desktop_lcd_fill_circle(uint16_t x, uint16_t y, uint16_t radius,
                             uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(x), mp_obj_new_int(y),
                            mp_obj_new_int(radius), mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__fill_circle, 4, arguments);
}

void desktop_lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2,
                               uint16_t y2, uint16_t x3, uint16_t y3,
                               uint16_t color)
{
    mp_obj_t arguments[] = {
        mp_obj_new_int(x1), mp_obj_new_int(y1), mp_obj_new_int(x2),
        mp_obj_new_int(y2), mp_obj_new_int(x3), mp_obj_new_int(y3),
        mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__fill_triangle, 7, arguments);
}

void desktop_lcd_text(uint16_t x, uint16_t y, const char *text,
                      uint16_t color, int font_size)
{
    mp_obj_t arguments[] = {
        mp_obj_new_int(x), mp_obj_new_int(y),
        mp_obj_new_str(text, strlen(text)), mp_obj_new_int(color),
        mp_obj_new_int(font_size)};
    desktop_call_lcd(MP_QSTR__text, 5, arguments);
}

void desktop_lcd_swap(void)
{
    desktop_call_lcd(MP_QSTR_swap, 0, NULL);
}

void desktop_log_message(const char *message)
{
    mp_printf(&mp_plat_print, "[desktop:mmbasic] %s\n", message);
}

static mp_obj_t desktop_call_storage(qstr name, size_t argument_count,
                                     const mp_obj_t *arguments)
{
    mp_obj_t storage = desktop_import(MP_QSTR_sd_mp);
    mp_obj_t destination[6];
    mp_load_method(storage, name, destination);
    for (size_t index = 0; index < argument_count; index++)
        destination[index + 2] = arguments[index];
    return mp_call_method_n_kw(argument_count, 0, destination);
}

size_t desktop_storage_file_size(const char *path)
{
    mp_obj_t arguments[] = {mp_obj_new_str(path, strlen(path))};
    return (size_t)mp_obj_get_int(
        desktop_call_storage(MP_QSTR_get_file_size, 1, arguments));
}

size_t desktop_storage_file_read(const char *path, void *buffer,
                                 size_t buffer_size)
{
    mp_obj_t arguments[] = {mp_obj_new_str(path, strlen(path)),
                            mp_obj_new_int(0),
                            mp_obj_new_int_from_uint(buffer_size)};
    mp_obj_t result = desktop_call_storage(MP_QSTR_read, 3, arguments);
    mp_buffer_info_t source;
    mp_get_buffer_raise(result, &source, MP_BUFFER_READ);
    size_t count = source.len < buffer_size ? source.len : buffer_size;
    memcpy(buffer, source.buf, count);
    return count;
}
