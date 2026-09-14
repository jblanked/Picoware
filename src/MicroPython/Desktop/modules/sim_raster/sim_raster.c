#include "py/runtime.h"
#include "py/objarray.h"
#include <stdint.h>

// One physical LCD controller per simulator process. Its GRAM belongs to the
// host, not the emulated MCU heap. Static lifetime keeps exported memoryviews
// safe even after an LCD wrapper is collected. All LCD wrappers share GRAM.
// Reserve enough for the largest supported display (CrowPanel 1024 x 600).
static uint8_t display_pixels[1024 * 600 * 2];

// Match the simulator's inclusive edge coverage and RGB565 integer blending.
// Coordinates are bounded before multiplication so edge arithmetic fits int64_t.

static mp_obj_t blit_rgb332(size_t n_args, const mp_obj_t *args);
static mp_obj_t display_buffer(mp_obj_t width_in, mp_obj_t height_in);
static int64_t edge(int64_t ax, int64_t ay, int64_t bx, int64_t by,
                    int64_t px, int64_t py);
static mp_obj_t fill_triangle(size_t n_args, const mp_obj_t *args);
static uint16_t mono(uint16_t color);

static mp_obj_t blit_rgb332(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    mp_buffer_info_t destination;
    mp_buffer_info_t source;
    mp_get_buffer_raise(args[0], &destination, MP_BUFFER_WRITE);
    mp_int_t destination_width = mp_obj_get_int(args[1]);
    mp_int_t destination_height = mp_obj_get_int(args[2]);
    mp_int_t x = mp_obj_get_int(args[3]);
    mp_int_t y = mp_obj_get_int(args[4]);
    mp_int_t image_width = mp_obj_get_int(args[5]);
    mp_int_t image_height = mp_obj_get_int(args[6]);
    mp_get_buffer_raise(args[7], &source, MP_BUFFER_READ);
    if (destination_width <= 0 || destination_height <= 0
        || image_width <= 0 || image_height <= 0
        || (size_t)destination_width * (size_t)destination_height * 2 > destination.len
        || (size_t)image_width * (size_t)image_height > source.len) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid RGB332 blit dimensions"));
    }

    mp_int_t left = x < 0 ? 0 : x;
    mp_int_t top = y < 0 ? 0 : y;
    mp_int_t right = x + image_width;
    mp_int_t bottom = y + image_height;
    if (right > destination_width) right = destination_width;
    if (bottom > destination_height) bottom = destination_height;
    if (left >= right || top >= bottom) {
        return mp_const_none;
    }

    const uint8_t *source_pixels = (const uint8_t *)source.buf;
    uint8_t *destination_pixels = (uint8_t *)destination.buf;
    for (mp_int_t row = top; row < bottom; ++row) {
        const uint8_t *source_row = source_pixels
            + (size_t)(row - y) * (size_t)image_width + (left - x);
        uint8_t *destination_row = destination_pixels
            + ((size_t)row * (size_t)destination_width + left) * 2;
        for (mp_int_t column = left; column < right; ++column) {
            uint8_t value = *source_row++;
            uint8_t red = (uint8_t)(((value >> 5) & 0x07) * 255 / 7);
            uint8_t green = (uint8_t)(((value >> 2) & 0x07) * 255 / 7);
            uint8_t blue = (uint8_t)((value & 0x03) * 255 / 3);
            uint16_t color = (uint16_t)(((red & 0xf8) << 8)
                | ((green & 0xfc) << 3) | (blue >> 3));
            *destination_row++ = (uint8_t)(color & 0xff);
            *destination_row++ = (uint8_t)(color >> 8);
        }
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(blit_rgb332_obj, 8, 8, blit_rgb332);

static mp_obj_t display_buffer(mp_obj_t width_in, mp_obj_t height_in) {
    mp_int_t width = mp_obj_get_int(width_in);
    mp_int_t height = mp_obj_get_int(height_in);
    if (width <= 0 || height <= 0
        || (size_t)width > sizeof(display_pixels) / 2 / (size_t)height) {
        mp_raise_ValueError(MP_ERROR_TEXT("unsupported simulator display size"));
    }
    return mp_obj_new_memoryview('B' | MP_OBJ_ARRAY_TYPECODE_FLAG_RW,
        (size_t)width * (size_t)height * 2, display_pixels);
}
static MP_DEFINE_CONST_FUN_OBJ_2(display_buffer_obj, display_buffer);

static int64_t edge(int64_t ax, int64_t ay, int64_t bx, int64_t by,
                    int64_t px, int64_t py) {
    return (px - ax) * (by - ay) - (py - ay) * (bx - ax);
}

static mp_obj_t fill_triangle(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    mp_buffer_info_t buffer;
    mp_get_buffer_raise(args[0], &buffer, MP_BUFFER_WRITE);
    mp_int_t width = mp_obj_get_int(args[1]);
    mp_int_t height = mp_obj_get_int(args[2]);
    if (width <= 0 || height <= 0
        || (size_t)width > buffer.len / 2 / (size_t)height) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid framebuffer dimensions"));
    }
    int64_t p[6];
    for (size_t i = 0; i < 6; ++i) {
        p[i] = mp_obj_get_int(args[i + 3]);
        if (p[i] < -1000000 || p[i] > 1000000) {
            mp_raise_ValueError(MP_ERROR_TEXT("triangle coordinate out of range"));
        }
    }
    uint16_t color = (uint16_t)mp_obj_get_int(args[9]);
    uint8_t alpha = (uint8_t)mp_obj_get_int(args[10]);
    bool monochrome = mp_obj_is_true(args[11]);
    int64_t area = edge(p[0], p[1], p[2], p[3], p[4], p[5]);
    if (alpha == 0 || area == 0) {
        return mp_const_none;
    }

    int64_t min_x = p[0], max_x = p[0], min_y = p[1], max_y = p[1];
    for (size_t i = 2; i < 6; i += 2) {
        if (p[i] < min_x) min_x = p[i];
        if (p[i] > max_x) max_x = p[i];
        if (p[i + 1] < min_y) min_y = p[i + 1];
        if (p[i + 1] > max_y) max_y = p[i + 1];
    }
    if (min_x < 0) min_x = 0;
    if (min_y < 0) min_y = 0;
    if (max_x >= width) max_x = width - 1;
    if (max_y >= height) max_y = height - 1;

    int64_t e0 = edge(p[0], p[1], p[2], p[3], min_x, min_y);
    int64_t e1 = edge(p[2], p[3], p[4], p[5], min_x, min_y);
    int64_t e2 = edge(p[4], p[5], p[0], p[1], min_x, min_y);
    uint8_t *pixels = buffer.buf;
    unsigned inverse = 255 - alpha;
    unsigned red = ((color >> 11) & 31) * alpha;
    unsigned green = ((color >> 5) & 63) * alpha;
    unsigned blue = (color & 31) * alpha;
    uint16_t opaque = monochrome ? mono(color) : color;
    for (int64_t y = min_y; y <= max_y; ++y) {
        int64_t a = e0, b = e1, c = e2;
        for (int64_t x = min_x; x <= max_x; ++x) {
            bool inside = area > 0 ? (a >= 0 && b >= 0 && c >= 0)
                                   : (a <= 0 && b <= 0 && c <= 0);
            if (inside) {
                size_t offset = ((size_t)y * (size_t)width + (size_t)x) * 2;
                uint16_t result = opaque;
                if (alpha != 255) {
                    uint16_t dst = pixels[offset] | ((uint16_t)pixels[offset + 1] << 8);
                    result = ((red + ((dst >> 11) & 31) * inverse) / 255) << 11
                        | ((green + ((dst >> 5) & 63) * inverse) / 255) << 5
                        | (blue + (dst & 31) * inverse) / 255;
                    if (monochrome) result = mono(result);
                }
                pixels[offset] = result & 0xff;
                pixels[offset + 1] = result >> 8;
            }
            a += p[3] - p[1];
            b += p[5] - p[3];
            c += p[1] - p[5];
        }
        e0 -= p[2] - p[0];
        e1 -= p[4] - p[2];
        e2 -= p[0] - p[4];
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(fill_triangle_obj, 12, 12, fill_triangle);

static uint16_t mono(uint16_t color) {
    unsigned luminance = ((color >> 11) & 31) * 299
        + ((color >> 5) & 63) * 587 + (color & 31) * 114;
    return luminance > 44800 ? 0xffff : 0;
}

static const mp_rom_map_elem_t sim_raster_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sim_raster) },
    { MP_ROM_QSTR(MP_QSTR_blit_rgb332), MP_ROM_PTR(&blit_rgb332_obj) },
    { MP_ROM_QSTR(MP_QSTR_display_buffer), MP_ROM_PTR(&display_buffer_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill_triangle), MP_ROM_PTR(&fill_triangle_obj) },
};
static MP_DEFINE_CONST_DICT(sim_raster_globals, sim_raster_globals_table);

const mp_obj_module_t sim_raster_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sim_raster_globals,
};
MP_REGISTER_MODULE(MP_QSTR_sim_raster, sim_raster_module);
