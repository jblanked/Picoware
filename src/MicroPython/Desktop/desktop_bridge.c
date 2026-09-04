#include "desktop_bridge.h"

#include <stdbool.h>
#include <string.h>

#include "py/nlr.h"
#include "py/qstr.h"
#include "py/objstr.h"
#include "py/runtime.h"

#define DESKTOP_QSTR(name) qstr_from_strn_static(name, sizeof(name) - 1)

static mp_obj_t desktop_import(qstr module_name)
{
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
    mp_obj_t runtime = desktop_import(MP_QSTR_sim_runtime);
    return desktop_call_function_0(runtime, MP_QSTR_get_lcd);
}

static bool desktop_call_lcd(qstr name, size_t argument_count,
                             const mp_obj_t *arguments)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
        return false;

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

void desktop_lcd_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    mp_obj_t arguments[] = {
        mp_obj_new_int(x), mp_obj_new_int(y), mp_obj_new_int(color)};
    desktop_call_lcd(MP_QSTR__pixel, 3, arguments);
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
    size_t buffer_size = (size_t)width * (size_t)height * sizeof(uint16_t);
    mp_obj_t arguments[] = {
        mp_obj_new_int(x), mp_obj_new_int(y), mp_obj_new_int(width),
        mp_obj_new_int(height), mp_obj_new_bytes((const byte *)buffer,
                                                 buffer_size)};
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
