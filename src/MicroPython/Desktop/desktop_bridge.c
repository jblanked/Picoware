#include "desktop_bridge.h"

#include <stdbool.h>
#include <math.h>
#include <string.h>

#include "py/nlr.h"
#include "py/gc.h"
#include "py/qstr.h"
#include "py/objstr.h"
#include "py/objmodule.h"
#include "py/mpstate.h"
#include "py/objtuple.h"
#include "py/runtime.h"

#define DESKTOP_QSTR(name) qstr_from_strn_static(name, sizeof(name) - 1)

static mp_obj_t desktop_import(qstr module_name)
{
    mp_map_elem_t *module = mp_map_lookup(&MP_STATE_VM(mp_loaded_modules_dict).map,
        MP_OBJ_NEW_QSTR(module_name), MP_MAP_LOOKUP);
    if (module != NULL && module->value != MP_OBJ_NULL)
        return module->value;
    // Finalisers may call the bridge while collection locks the heap. Importing
    // a new module then can leave an incomplete entry in sys.modules.
    if (gc_is_locked())
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("cannot import during collection"));
    return mp_import_name(module_name, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
}

static mp_obj_t desktop_call_method(mp_obj_t object, qstr name,
                                    size_t argument_count,
                                    const mp_obj_t *arguments)
{
    mp_obj_t destination[12];
    mp_load_method(object, name, destination);
    for (size_t index = 0; index < argument_count; index++)
        destination[index + 2] = arguments[index];
    return mp_call_method_n_kw(argument_count, 0, destination);
}

static mp_obj_t desktop_call_function_0(mp_obj_t object, qstr name)
{
    return desktop_call_method(object, name, 0, NULL);
}

static mp_obj_t desktop_lcd(void)
{
    // Read the current runtime binding on every call so LCD replacement and GC
    // cannot leave a cached framebuffer pointer behind.
    mp_map_elem_t *module = mp_map_lookup(&MP_STATE_VM(mp_loaded_modules_dict).map,
        MP_OBJ_NEW_QSTR(MP_QSTR_sim_runtime), MP_MAP_LOOKUP);
    if (module != NULL && mp_obj_is_type(module->value, &mp_type_module))
    {
        mp_obj_dict_t *globals = mp_obj_module_get_globals(module->value);
        mp_map_elem_t *lcd = mp_map_lookup(&globals->map,
            MP_OBJ_NEW_QSTR(MP_QSTR__lcd), MP_MAP_LOOKUP);
        if (lcd != NULL)
            return lcd->value;
    }
    mp_obj_t runtime = desktop_import(MP_QSTR_sim_runtime);
    return desktop_call_function_0(runtime, MP_QSTR_get_lcd);
}

static bool desktop_call_lcd(qstr name, size_t argument_count,
                             const mp_obj_t *arguments)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_t exception = MP_OBJ_FROM_PTR(nlr.ret_val);
        // Native games swap through this bridge; quit/reload must reach run.py.
        if (mp_obj_exception_match(exception, MP_OBJ_FROM_PTR(&mp_type_SystemExit)))
            nlr_jump(nlr.ret_val);
        return false;
    }

    mp_obj_t lcd = desktop_lcd();
    if (lcd == mp_const_none)
    {
        nlr_pop();
        return false;
    }
    desktop_call_method(lcd, name, argument_count, arguments);
    nlr_pop();
    return true;
}

void desktop_lcd_clear(uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__clear, 1, arguments);
}

static mp_obj_t desktop_polygon_points(uint16_t x[], uint16_t y[], int count)
{
    mp_obj_t result = mp_obj_new_tuple(count, NULL);
    mp_obj_tuple_t *points = MP_OBJ_TO_PTR(result);
    for (int i = 0; i < count; i++)
    {
        mp_obj_t pair[] = {mp_obj_new_int(x[i]), mp_obj_new_int(y[i])};
        points->items[i] = mp_obj_new_tuple(2, pair);
    }
    return result;
}

void desktop_lcd_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    if (count < 2)
        return;
    mp_obj_t arguments[] = {desktop_polygon_points(x, y, count), mp_obj_new_int(color)};
    desktop_call_lcd(DESKTOP_QSTR("_polygon"), 2, arguments);
}

void desktop_lcd_fill_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    if (count < 3)
        return;
    mp_obj_t arguments[] = {desktop_polygon_points(x, y, count), mp_obj_new_int(color)};
    desktop_call_lcd(DESKTOP_QSTR("_fill_polygon"), 2, arguments);
}

void desktop_lcd_fill_polygon_alpha(uint16_t x[], uint16_t y[], int count,
                                    uint16_t color, uint8_t alpha)
{
    if (count < 3 || alpha == 0)
        return;
    mp_obj_t arguments[] = {desktop_polygon_points(x, y, count),
                            mp_obj_new_int(color), mp_obj_new_int(alpha)};
    desktop_call_lcd(DESKTOP_QSTR("_fill_polygon_alpha"), 3, arguments);
}

uint16_t desktop_lcd_width(void)
{
    mp_obj_t lcd = desktop_lcd();
    return lcd == mp_const_none ? 320 : mp_obj_get_int(mp_load_attr(lcd, MP_QSTR_width));
}

uint16_t desktop_lcd_height(void)
{
    mp_obj_t lcd = desktop_lcd();
    return lcd == mp_const_none ? 320 : mp_obj_get_int(mp_load_attr(lcd, MP_QSTR_height));
}

void desktop_lcd_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    mp_obj_t arguments[] = {
        mp_obj_new_int(x), mp_obj_new_int(y), mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__pixel, 3, arguments);
}

void desktop_lcd_blit_mask(int16_t dst_x, int16_t dst_y, uint16_t dst_w, uint16_t dst_h,
                           uint16_t src_w, uint16_t src_h, const uint8_t *buffer, const uint8_t *mask)
{
    if (!buffer || !mask || !dst_w || !dst_h || !src_w || !src_h)
        return;

    int32_t src_x = dst_x < 0 ? -(int32_t)dst_x : 0;
    int32_t src_y = dst_y < 0 ? -(int32_t)dst_y : 0;
    int32_t screen_x = dst_x < 0 ? 0 : dst_x;
    int32_t screen_y = dst_y < 0 ? 0 : dst_y;
    int32_t copy_width = (int32_t)dst_w - src_x;
    int32_t copy_height = (int32_t)dst_h - src_y;
    int32_t display_width = desktop_lcd_width();
    int32_t display_height = desktop_lcd_height();
    if (screen_x + copy_width > display_width)
        copy_width = display_width - screen_x;
    if (screen_y + copy_height > display_height)
        copy_height = display_height - screen_y;
    if (copy_width <= 0 || copy_height <= 0)
        return;

    for (int32_t row = 0; row < copy_height; ++row)
    {
        uint32_t source_y = (uint32_t)(src_y + row) * src_h / dst_h;
        for (int32_t col = 0; col < copy_width; ++col)
        {
            uint32_t source_x = (uint32_t)(src_x + col) * src_w / dst_w;
            uint32_t pixel = source_y * src_w + source_x;
            if (mask[pixel >> 3] & (0x80u >> (pixel & 7)))
            {
                uint8_t rgb332 = buffer[pixel];
                uint16_t red = (uint16_t)((((rgb332 >> 5) & 7u) << 2) | (((rgb332 >> 5) & 7u) >> 1));
                uint16_t green = (uint16_t)((((rgb332 >> 2) & 7u) << 3) | ((rgb332 >> 2) & 7u));
                uint16_t blue = (uint16_t)(((rgb332 & 3u) << 3) | ((rgb332 & 3u) << 1) | ((rgb332 & 3u) >> 1));
                desktop_lcd_pixel((uint16_t)(screen_x + col), (uint16_t)(screen_y + row),
                                  (uint16_t)((red << 11) | (green << 5) | blue));
            }
        }
    }
}

void desktop_lcd_char(uint16_t x, uint16_t y, char character, uint16_t color,
                      int font_size)
{
    char text[2] = {character, '\0'};
    mp_obj_t arguments[] = {mp_obj_new_int(x), mp_obj_new_int(y),
                            mp_obj_new_str(text, 1), mp_obj_new_int(color),
                            mp_obj_new_int(font_size)};
    desktop_call_lcd(DESKTOP_QSTR("_char"), 5, arguments);
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

void desktop_lcd_triangle(uint16_t x1, uint16_t y1, uint16_t x2,
                          uint16_t y2, uint16_t x3, uint16_t y3,
                          uint16_t color)
{
    mp_obj_t arguments[] = {
        mp_obj_new_int(x1), mp_obj_new_int(y1), mp_obj_new_int(x2),
        mp_obj_new_int(y2), mp_obj_new_int(x3), mp_obj_new_int(y3),
        mp_obj_new_int(color)};
    desktop_call_lcd(DESKTOP_QSTR("_triangle"), 7, arguments);
}

void desktop_lcd_fill_rectangle(uint16_t x, uint16_t y, uint16_t width,
                                uint16_t height, uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(x), mp_obj_new_int(y),
                            mp_obj_new_int(width), mp_obj_new_int(height),
                            mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__fill_rectangle, 5, arguments);
}

void desktop_lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width,
                                      uint16_t height, uint16_t radius,
                                      uint16_t color)
{
    mp_obj_t arguments[] = {mp_obj_new_int(x), mp_obj_new_int(y),
                            mp_obj_new_int(width), mp_obj_new_int(height),
                            mp_obj_new_int(radius), mp_obj_new_int(color)};
    desktop_call_lcd(DESKTOP_QSTR("_fill_round_rectangle"), 6, arguments);
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

void desktop_lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2,
                                     uint16_t y2, uint16_t x3, uint16_t y3,
                                     uint16_t color, uint8_t alpha)
{
    mp_obj_t arguments[] = {
        mp_obj_new_int(x1), mp_obj_new_int(y1), mp_obj_new_int(x2),
        mp_obj_new_int(y2), mp_obj_new_int(x3), mp_obj_new_int(y3),
        mp_obj_new_int(color), mp_obj_new_int(alpha)};
    desktop_call_lcd(DESKTOP_QSTR("_fill_triangle_alpha"), 8, arguments);
}

void desktop_lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                      const void *buffer)
{
    size_t buffer_size = (size_t)width * (size_t)height;
    mp_obj_t arguments[] = {
        mp_obj_new_int(x), mp_obj_new_int(y), mp_obj_new_int(width),
        mp_obj_new_int(height), mp_obj_new_bytes((const byte *)buffer,
                                                 buffer_size)};
    desktop_call_lcd(DESKTOP_QSTR("_bytearray"), 5, arguments);
}

void desktop_lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width,
                            uint16_t height, const void *buffer)
{
    if (!buffer || !width || !height)
        return;
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t lcd = desktop_lcd();
        if (lcd != mp_const_none)
        {
            bool unscaled = mp_obj_get_float(mp_load_attr(lcd, MP_QSTR__scale_x_factor)) == 1.0 &&
                            mp_obj_get_float(mp_load_attr(lcd, MP_QSTR__scale_y_factor)) == 1.0;
            mp_int_t w = mp_obj_get_int(mp_load_attr(lcd, MP_QSTR_width));
            mp_int_t h = mp_obj_get_int(mp_load_attr(lcd, MP_QSTR_height));
            bool mono = mp_obj_is_true(mp_load_attr(lcd, MP_QSTR__is_flipper));
            mp_buffer_info_t target;
            mp_get_buffer_raise(mp_load_attr(lcd, MP_QSTR__buffer), &target, MP_BUFFER_WRITE);
            if (unscaled && w > 0 && h > 0 && (size_t)w <= target.len / 2 / (size_t)h)
            {
                size_t rows = y < h ? (size_t)h - y : 0;
                size_t columns = x < w ? (size_t)w - x : 0;
                if (rows > height) rows = height;
                if (columns > width) columns = width;
                if (!rows || !columns) { nlr_pop(); return; }
                const byte *source = buffer;
                for (size_t row = 0; row < rows; ++row)
                {
                    byte *destination = (byte *)target.buf + (((size_t)y + row) * w + x) * 2;
                    const byte *pixels = source + row * width * 2;
                    if (!mono)
                        memcpy(destination, pixels, columns * 2);
                    else
                        for (size_t column = 0; column < columns; ++column)
                        {
                            uint16_t color = pixels[column * 2] | (pixels[column * 2 + 1] << 8);
                            unsigned luminance = ((color >> 11) & 31) * 299 +
                                ((color >> 5) & 63) * 587 + (color & 31) * 114;
                            byte value = luminance > 44800 ? 255 : 0;
                            destination[column * 2] = destination[column * 2 + 1] = value;
                        }
                }
                nlr_pop();
                return;
            }
        }
        nlr_pop();
    }
    else if (mp_obj_exception_match(MP_OBJ_FROM_PTR(nlr.ret_val), MP_OBJ_FROM_PTR(&mp_type_SystemExit)))
        nlr_jump(nlr.ret_val);
    size_t buffer_size = (size_t)width * height * sizeof(uint16_t);
    mp_obj_t arguments[] = {
        mp_obj_new_int(x), mp_obj_new_int(y), mp_obj_new_int(width),
        mp_obj_new_int(height), mp_obj_new_bytes((const byte *)buffer, buffer_size)};
    desktop_call_lcd(DESKTOP_QSTR("_bytearray"), 5, arguments);
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

void desktop_lcd_read_row(uint16_t row, uint8_t *out_buffer)
{
    if (!out_buffer)
        return;

    memset(out_buffer, 0, 320);

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
        return;

    mp_obj_t lcd = desktop_lcd();
    if (lcd != mp_const_none)
    {
        mp_obj_t arguments[] = {mp_obj_new_int(row)};
        mp_obj_t result = desktop_call_method(
            lcd, DESKTOP_QSTR("_read_row"), 1, arguments);
        mp_buffer_info_t source;
        if (mp_get_buffer(result, &source, MP_BUFFER_READ))
        {
            size_t copy_size = source.len < 320 ? source.len : 320;
            memcpy(out_buffer, source.buf, copy_size);
        }
    }
    nlr_pop();
}

void desktop_lcd_set_brightness(uint8_t brightness)
{
    mp_obj_t arguments[] = {mp_obj_new_int(brightness)};
    desktop_call_lcd(DESKTOP_QSTR("set_brightness"), 1, arguments);
}

void desktop_lcd_set_rgb_led(uint8_t red, uint8_t green, uint8_t blue)
{
    mp_obj_t arguments[] = {mp_obj_new_int(red), mp_obj_new_int(green),
                            mp_obj_new_int(blue)};
    desktop_call_lcd(DESKTOP_QSTR("set_rgb_led"), 3, arguments);
}

void desktop_lcd_swap(void)
{
    desktop_call_lcd(MP_QSTR_swap, 0, NULL);
}

void desktop_log_message(const char *message)
{
    mp_printf(&mp_plat_print, "[desktop] %s\n", message ? message : "");
}

static mp_obj_t desktop_call_module(qstr module_name, qstr function_name,
                                    size_t argument_count,
                                    const mp_obj_t *arguments)
{
    mp_obj_t module = desktop_import(module_name);
    return desktop_call_method(module, function_name, argument_count,
                               arguments);
}

static bool desktop_module_bool(qstr module_name, qstr function_name,
                                size_t argument_count,
                                const mp_obj_t *arguments)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
        return false;

    mp_obj_t result = desktop_call_module(module_name, function_name,
                                          argument_count, arguments);
    bool value = mp_obj_is_true(result);
    nlr_pop();
    return value;
}

static bool desktop_module_copy_string(qstr module_name, qstr function_name,
                                       size_t argument_count,
                                       const mp_obj_t *arguments, void *buffer,
                                       size_t buffer_size)
{
    if (buffer == NULL && buffer_size != 0)
        return false;

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
        return false;

    mp_obj_t result = desktop_call_module(module_name, function_name,
                                          argument_count, arguments);
    if (!mp_obj_is_str(result))
    {
        nlr_pop();
        return false;
    }

    size_t result_size = 0;
    const char *text = mp_obj_str_get_data(result, &result_size);
    if (buffer_size != 0)
    {
        size_t copy_size = result_size < buffer_size - 1
                               ? result_size
                               : buffer_size - 1;
        memcpy(buffer, text, copy_size);
        ((char *)buffer)[copy_size] = '\0';
    }
    nlr_pop();
    return true;
}

size_t desktop_storage_file_size(const char *path)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
        return 0;

    mp_obj_t arguments[] = {mp_obj_new_str(path, strlen(path))};
    mp_int_t result = mp_obj_get_int(desktop_call_module(
        MP_QSTR_sd_mp, MP_QSTR_get_file_size, 1, arguments));
    nlr_pop();
    return result > 0 ? (size_t)result : 0;
}

static size_t desktop_storage_file_read_at(const char *path, void *buffer,
                                           size_t buffer_size, size_t offset)
{
    if (buffer == NULL && buffer_size != 0)
        return 0;

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
        return 0;

    mp_obj_t arguments[] = {mp_obj_new_str(path, strlen(path)),
                            mp_obj_new_int_from_uint(offset),
                            mp_obj_new_int_from_uint(buffer_size)};
    mp_obj_t result = desktop_call_module(MP_QSTR_sd_mp, MP_QSTR_read, 3,
                                          arguments);
    mp_buffer_info_t source;
    mp_get_buffer_raise(result, &source, MP_BUFFER_READ);
    size_t count = source.len < buffer_size ? source.len : buffer_size;
    if (count != 0)
        memcpy(buffer, source.buf, count);
    nlr_pop();
    return count;
}

size_t desktop_storage_file_read(const char *path, void *buffer,
                                 size_t buffer_size)
{
    return desktop_storage_file_read_at(path, buffer, buffer_size, 0);
}

size_t desktop_storage_file_read_chunk(const char *path, void *buffer,
                                       size_t buffer_size, size_t offset)
{
    return desktop_storage_file_read_at(path, buffer, buffer_size, offset);
}

static bool desktop_storage_file_write_mode(const char *path,
                                            const void *buffer,
                                            size_t buffer_size, bool overwrite);

bool desktop_storage_file_write(const char *path, const void *buffer,
                                size_t buffer_size)
{
    return desktop_storage_file_write_mode(path, buffer, buffer_size, true);
}

static bool desktop_storage_file_write_mode(const char *path,
                                            const void *buffer,
                                            size_t buffer_size, bool overwrite)
{
    if (buffer == NULL && buffer_size != 0)
        return false;

    mp_obj_t arguments[] = {mp_obj_new_str(path, strlen(path)),
                            mp_obj_new_bytes((const byte *)buffer,
                                             buffer_size),
                            mp_obj_new_bool(overwrite)};
    return desktop_module_bool(MP_QSTR_sd_mp, MP_QSTR_write, 3, arguments);
}

typedef struct
{
    char *path;
} desktop_storage_write_handle_t;

void *desktop_storage_file_write_open(const char *path)
{
    if (!path)
        return NULL;

    desktop_storage_write_handle_t *handle =
        m_malloc(sizeof(desktop_storage_write_handle_t));
    if (!handle)
        return NULL;

    size_t path_size = strlen(path) + 1;
    handle->path = m_malloc(path_size);
    if (!handle->path)
    {
        m_free(handle);
        return NULL;
    }
    memcpy(handle->path, path, path_size);

    if (!desktop_storage_file_write_mode(path, NULL, 0, true))
    {
        m_free(handle->path);
        m_free(handle);
        return NULL;
    }
    return handle;
}

void desktop_storage_file_close(void *handle)
{
    desktop_storage_write_handle_t *file = handle;
    if (!file)
        return;
    m_free(file->path);
    m_free(file);
}

bool desktop_storage_file_write_file_chunk(void *handle, const void *data,
                                           size_t size)
{
    desktop_storage_write_handle_t *file = handle;
    if (!file)
        return false;
    return desktop_storage_file_write_mode(file->path, data, size, false);
}

bool desktop_http_get_response(void *buffer, size_t buffer_size)
{
    mp_obj_t arguments[] = {mp_const_none,
                            mp_obj_new_int_from_uint(buffer_size)};
    return desktop_module_copy_string(DESKTOP_QSTR("http"),
                                      DESKTOP_QSTR("http_get_http_response"), 2,
                                      arguments, buffer, buffer_size);
}

bool desktop_http_is_finished(void)
{
    return desktop_module_bool(DESKTOP_QSTR("http"),
                               DESKTOP_QSTR("http_is_finished"), 0, NULL);
}

bool desktop_http_send_request(const char *url, const char *method,
                               const char *headers, const char *payload)
{
    mp_obj_t arguments[] = {
        mp_obj_new_str(url ? url : "", strlen(url ? url : "")),
        mp_obj_new_str(method ? method : "GET",
                       strlen(method ? method : "GET")),
        headers ? mp_obj_new_str(headers, strlen(headers)) : mp_const_none,
        payload ? mp_obj_new_str(payload, strlen(payload)) : mp_const_none,
    };
    return desktop_module_bool(DESKTOP_QSTR("http"),
                               DESKTOP_QSTR("http_send_request"), 4,
                               arguments);
}

bool desktop_http_get_websocket_response(void *buffer, size_t buffer_size)
{
    mp_obj_t arguments[] = {mp_const_none,
                            mp_obj_new_int_from_uint(buffer_size)};
    return desktop_module_copy_string(
        DESKTOP_QSTR("websocket"),
        DESKTOP_QSTR("http_get_websocket_response"), 2,
        arguments, buffer, buffer_size);
}

bool desktop_http_websocket_is_connected(void)
{
    return desktop_module_bool(DESKTOP_QSTR("websocket"),
                               DESKTOP_QSTR("http_websocket_is_connected"),
                               0, NULL);
}

bool desktop_http_websocket_send(const char *message)
{
    mp_obj_t arguments[] = {
        mp_obj_new_str(message ? message : "", strlen(message ? message : ""))};
    return desktop_module_bool(DESKTOP_QSTR("websocket"),
                               DESKTOP_QSTR("http_websocket_send"), 1,
                               arguments);
}

bool desktop_http_websocket_start(const char *url, int port)
{
    mp_obj_t arguments[] = {
        mp_obj_new_str(url ? url : "", strlen(url ? url : "")),
        mp_obj_new_int(port),
    };
    return desktop_module_bool(DESKTOP_QSTR("websocket"),
                               DESKTOP_QSTR("http_websocket_start"), 2,
                               arguments);
}

bool desktop_http_websocket_stop(void)
{
    return desktop_module_bool(DESKTOP_QSTR("websocket"),
                               DESKTOP_QSTR("http_websocket_stop"), 0,
                               NULL);
}

void desktop_lcd_textured_triangle(float x1, float y1, float u1, float v1,
                           float x2, float y2, float u2, float v2,
                           float x3, float y3, float u3, float v3,
                           const uint16_t *texture, uint16_t texture_width, uint16_t texture_height, uint16_t tint)
{
    if (!texture || texture_width == 0 || texture_height == 0)
        return;

    mp_obj_t lcd = desktop_lcd();
    if (lcd == mp_const_none)
        return;
    mp_int_t width = mp_obj_get_int(mp_load_attr(lcd, MP_QSTR_width));
    mp_int_t height = mp_obj_get_int(mp_load_attr(lcd, MP_QSTR_height));
    mp_buffer_info_t target;
    mp_get_buffer_raise(mp_load_attr(lcd, MP_QSTR__buffer), &target, MP_BUFFER_WRITE);
    if (width <= 0 || height <= 0 || (size_t)width > target.len / 2 / (size_t)height)
        return;
    bool monochrome = mp_obj_is_true(mp_load_attr(lcd, MP_QSTR__is_flipper));
    if (mp_obj_is_true(mp_load_attr(lcd, MP_QSTR_scale_position)))
    {
        float sx = mp_obj_get_float(mp_load_attr(lcd, MP_QSTR__scale_x_factor));
        float sy = mp_obj_get_float(mp_load_attr(lcd, MP_QSTR__scale_y_factor));
        x1 *= sx; x2 *= sx; x3 *= sx;
        y1 *= sy; y2 *= sy; y3 *= sy;
    }
    // Bound float-to-int conversion and reject NaN/Inf from malformed meshes.
    const float values[] = {x1, y1, u1, v1, x2, y2, u2, v2, x3, y3, u3, v3};
    for (size_t i = 0; i < sizeof(values) / sizeof(values[0]); ++i)
        if (!(values[i] >= -1000000.f && values[i] <= 1000000.f))
            return;
    uint8_t *pixels = target.buf;

    // Match PicoCalc lcd_textured_triangle scanlines, UV sampling and tint.
    // Tint as 8-bit multipliers (matches SDL vertex color)
    const uint8_t tint_r5 = (tint >> 11) & 0x1F;
    const uint8_t tint_g6 = (tint >> 5) & 0x3F;
    const uint8_t tint_b5 = tint & 0x1F;
    const uint16_t tint_r8 = (uint16_t)((tint_r5 << 3) | (tint_r5 >> 2));
    const uint16_t tint_g8 = (uint16_t)((tint_g6 << 2) | (tint_g6 >> 4));
    const uint16_t tint_b8 = (uint16_t)((tint_b5 << 3) | (tint_b5 >> 2));

    // Vertices, sorted by Y (A top, B mid, C bot)
    float ax = x1, ay = y1, au = u1, av = v1;
    float bx = x2, by = y2, bu = u2, bv = v2;
    float cx = x3, cy = y3, cu = u3, cv = v3;
    if (ay > by)
    {
        float t;
        t = ax;
        ax = bx;
        bx = t;
        t = ay;
        ay = by;
        by = t;
        t = au;
        au = bu;
        bu = t;
        t = av;
        av = bv;
        bv = t;
    }
    if (by > cy)
    {
        float t;
        t = bx;
        bx = cx;
        cx = t;
        t = by;
        by = cy;
        cy = t;
        t = bu;
        bu = cu;
        cu = t;
        t = bv;
        bv = cv;
        cv = t;
    }
    if (ay > by)
    {
        float t;
        t = ax;
        ax = bx;
        bx = t;
        t = ay;
        ay = by;
        by = t;
        t = au;
        au = bu;
        bu = t;
        t = av;
        av = bv;
        bv = t;
    }

    const int iy_top = ay < 0 ? 0 : (int)ay;
    const int iy_bot = cy >= height ? height - 1 : (int)cy;
    if (cy <= ay)
        return;

    const float total_h = cy - ay;

    for (int scanY = iy_top; scanY <= iy_bot; scanY++)
    {
        if (scanY < 0 || scanY >= height)
            continue;

        const float sy = (float)scanY + 0.5f;
        if (sy < ay || sy >= cy)
            continue;

        // Full-height A->C edge
        const float f2 = total_h != 0.f ? (sy - ay) / total_h : 0.f;
        float e2x = ax + (cx - ax) * f2;
        float e2u = au + (cu - au) * f2;
        float e2v = av + (cv - av) * f2;

        // Upper: A->B, lower: B->C
        float e1x, e1u, e1v;
        if (sy <= by)
        {
            const float d1 = by - ay;
            const float f1 = d1 != 0.f ? (sy - ay) / d1 : 0.f;
            e1x = ax + (bx - ax) * f1;
            e1u = au + (bu - au) * f1;
            e1v = av + (bv - av) * f1;
        }
        else
        {
            const float d1 = cy - by;
            const float f1 = d1 != 0.f ? (sy - by) / d1 : 0.f;
            e1x = bx + (cx - bx) * f1;
            e1u = bu + (cu - bu) * f1;
            e1v = bv + (cv - bv) * f1;
        }

        // Left/right bounds with matching coords
        float x_left = e1x, x_right = e2x, u_left = e1u, u_right = e2u, v_left = e1v, v_right = e2v;
        if (e1x > e2x)
        {
            x_left = e2x;
            u_left = e2u;
            v_left = e2v;
            x_right = e1x;
            u_right = e1u;
            v_right = e1v;
        }
        if (x_left == x_right)
            continue;

        int start_x = (int)x_left;
        if ((float)start_x + 0.5f < x_left)
            start_x++;
        int end_x = (int)x_right;
        if ((float)end_x + 0.5f >= x_right)
            end_x--;
        if (start_x < 0)
            start_x = 0;
        if (end_x >= width)
            end_x = width - 1;
        if (start_x > end_x)
            continue;

        // Pixel-center UV interpolation
        const float inv_w = 1.0f / (x_right - x_left);
        const float u_step = (u_right - u_left) * inv_w;
        const float v_step = (v_right - v_left) * inv_w;
        float u_cur = u_left + ((float)start_x + 0.5f - x_left) * u_step;
        float v_cur = v_left + ((float)start_x + 0.5f - x_left) * v_step;

        const int span = end_x - start_x + 1;
        for (int col = 0; col < span; col++)
        {
            // Normalized UV to clamped texel
            int tu = (int)(fminf(1.f, fmaxf(0.f, u_cur)) * (float)texture_width);
            if (tu < 0)
                tu = 0;
            else if (tu >= texture_width)
                tu = texture_width - 1;
            int tv = (int)(fminf(1.f, fmaxf(0.f, v_cur)) * (float)texture_height);
            if (tv < 0)
                tv = 0;
            else if (tv >= texture_height)
                tv = texture_height - 1;
            const uint16_t texel = texture[(size_t)tv * texture_width + tu];

            // Modulate texel by tint, keep RGB565
            const uint8_t tr5 = (texel >> 11) & 0x1F;
            const uint8_t tg6 = (texel >> 5) & 0x3F;
            const uint8_t tb5 = texel & 0x1F;
            const uint16_t tr8 = (uint16_t)((tr5 << 3) | (tr5 >> 2));
            const uint16_t tg8 = (uint16_t)((tg6 << 2) | (tg6 >> 4));
            const uint16_t tb8 = (uint16_t)((tb5 << 3) | (tb5 >> 2));
            const uint16_t mod_r5 = (uint16_t)((tint_r8 * tr8) / 2040);
            const uint16_t mod_g6 = (uint16_t)((tint_g8 * tg8) / 1020);
            const uint16_t mod_b5 = (uint16_t)((tint_b8 * tb8) / 2040);
            uint16_t color = (mod_r5 << 11) | (mod_g6 << 5) | mod_b5;
            if (monochrome)
                color = mod_r5 * 299 + mod_g6 * 587 + mod_b5 * 114 > 44800 ? 0xffff : 0;
            size_t offset = ((size_t)scanY * width + start_x + col) * 2;
            pixels[offset] = color & 0xff;
            pixels[offset + 1] = color >> 8;

            u_cur += u_step;
            v_cur += v_step;
        }

    }
}
