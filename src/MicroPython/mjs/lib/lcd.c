#include "lcd.h"
#include "../../lcd/lcd_config.h"
#include "../../font/font_mp.h"
#include <string.h>
#include "color.h"

#ifndef DESKTOP
#include LCD_INCLUDE
#endif

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC) || defined(CARDPUTER) || defined(WAVESHARE_2_06) || defined(PANCAKE) || defined(V8)
#include "../../sd/storage.h"
#elif defined(FLIPPER_ZERO)
#include "../../Flipper/sd/storage.h"
#endif

static uint16_t lcd_js_get_color(struct mjs *mjs, uint8_t arg, uint16_t default_color)
{
    mjs_val_t t_arg = mjs_arg(mjs, arg);
    if (mjs_is_null(t_arg) || mjs_is_undefined(t_arg))
    {
        return default_color;
    }
    size_t len;
    return (uint16_t)color_parse_str(mjs_get_string(mjs, &t_arg, &len));
}

static FontSize lcd_js_get_font_size(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t t_arg = mjs_arg(mjs, arg);
    if (mjs_is_null(t_arg) || mjs_is_undefined(t_arg))
    {
        return (FontSize)FONT_DEFAULT;
    }
    return (FontSize)mjs_get_int(mjs, t_arg);
}

static uint16_t arg_u16(struct mjs *mjs, int idx)
{
    return (uint16_t)mjs_get_int(mjs, mjs_arg(mjs, idx));
}

void lcd_js_char(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);

    // Accept either a single-character string or a character code
    mjs_val_t c_arg = mjs_arg(mjs, 2);
    char c;
    if (mjs_is_string(c_arg))
    {
        size_t len;
        const char *str = mjs_get_string(mjs, &c_arg, &len);
        c = (len > 0) ? str[0] : ' ';
    }
    else
    {
        c = (char)arg_u16(mjs, 2);
    }

    uint16_t color = lcd_js_get_color(mjs, 3, 0xFFFF);
    FontSize size = lcd_js_get_font_size(mjs, 4);
    LCD_MP_CHAR(x, y, c, color, size);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_circle(struct mjs *mjs)
{
    uint16_t cx = arg_u16(mjs, 0);
    uint16_t cy = arg_u16(mjs, 1);
    uint16_t radius = arg_u16(mjs, 2);
    uint16_t color = lcd_js_get_color(mjs, 3, 0xFFFF);
    LCD_MP_CIRCLE(cx, cy, radius, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_clear(struct mjs *mjs)
{
    uint16_t color = lcd_js_get_color(mjs, 0, 0x0000);
    LCD_MP_CLEAR(color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_fill_circle(struct mjs *mjs)
{
    uint16_t cx = arg_u16(mjs, 0);
    uint16_t cy = arg_u16(mjs, 1);
    uint16_t radius = arg_u16(mjs, 2);
    uint16_t color = lcd_js_get_color(mjs, 3, 0xFFFF);
    LCD_MP_FILL_CIRCLE(cx, cy, radius, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_fill_rectangle(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t w = arg_u16(mjs, 2);
    uint16_t h = arg_u16(mjs, 3);
    uint16_t color = lcd_js_get_color(mjs, 4, 0xFFFF);
    LCD_MP_FILL_RECTANGLE(x, y, w, h, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_fill_round_rectangle(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t w = arg_u16(mjs, 2);
    uint16_t h = arg_u16(mjs, 3);
    uint16_t r = arg_u16(mjs, 4);
    uint16_t color = lcd_js_get_color(mjs, 5, 0xFFFF);
    LCD_MP_FILL_ROUND_RECTANGLE(x, y, w, h, r, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_fill_triangle(struct mjs *mjs)
{
    uint16_t x1 = arg_u16(mjs, 0);
    uint16_t y1 = arg_u16(mjs, 1);
    uint16_t x2 = arg_u16(mjs, 2);
    uint16_t y2 = arg_u16(mjs, 3);
    uint16_t x3 = arg_u16(mjs, 4);
    uint16_t y3 = arg_u16(mjs, 5);
    uint16_t color = lcd_js_get_color(mjs, 6, 0xFFFF);
    LCD_MP_FILL_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_len(struct mjs *mjs)
{
    mjs_val_t t_arg = mjs_arg(mjs, 0);
    size_t len;
    const char *text = mjs_get_string(mjs, &t_arg, &len);
    FontSize size = lcd_js_get_font_size(mjs, 1);
    size_t text_len = strlen(text);
    FontTable table = font_get_table(size);
    mjs_return(mjs, mjs_mk_number(mjs, text_len * (table.width + table.spacing)));
}

void lcd_js_line(struct mjs *mjs)
{
    uint16_t x1 = arg_u16(mjs, 0);
    uint16_t y1 = arg_u16(mjs, 1);
    uint16_t x2 = arg_u16(mjs, 2);
    uint16_t y2 = arg_u16(mjs, 3);
    uint16_t color = lcd_js_get_color(mjs, 4, 0xFFFF);
    LCD_MP_LINE(x1, y1, x2, y2, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_pixel(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t color = lcd_js_get_color(mjs, 2, 0xFFFF);
    LCD_MP_PIXEL(x, y, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_rectangle(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t w = arg_u16(mjs, 2);
    uint16_t h = arg_u16(mjs, 3);
    uint16_t color = lcd_js_get_color(mjs, 4, 0xFFFF);
    LCD_MP_RECTANGLE(x, y, w, h, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_text(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);

    mjs_val_t t_arg = mjs_arg(mjs, 2);
    size_t len;
    const char *text = mjs_get_string(mjs, &t_arg, &len);

    uint16_t color = lcd_js_get_color(mjs, 3, 0xFFFF);
    FontSize size = lcd_js_get_font_size(mjs, 4);
    LCD_MP_TEXT(x, y, text, color, size);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_triangle(struct mjs *mjs)
{
    uint16_t x1 = arg_u16(mjs, 0);
    uint16_t y1 = arg_u16(mjs, 1);
    uint16_t x2 = arg_u16(mjs, 2);
    uint16_t y2 = arg_u16(mjs, 3);
    uint16_t x3 = arg_u16(mjs, 4);
    uint16_t y3 = arg_u16(mjs, 5);
    uint16_t color = lcd_js_get_color(mjs, 6, 0xFFFF);
    LCD_MP_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_screenshot(struct mjs *mjs)
{
#ifdef LCD_MP_READ_ROW
#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC) || defined(CARDPUTER) || defined(WAVESHARE_2_06) || defined(PANCAKE) || defined(V8) || defined(FLIPPER_ZERO)
    char *path = mjs_copy_string_arg(mjs, 0);
    if (!path)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "Either no argument or failed to allocate memory for the file path string");
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    void *file = storage_file_write_open(path);
    if (!file)
    {
        mjs_prepend_errorf(mjs, MJS_FILE_READ_ERROR, "Failed to open file for writing: %s", path);
        m_free(path);
        path = NULL;
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }

    // BMP layout parameters
    uint32_t img_w = (uint32_t)LCD_MP_WIDTH;
    uint32_t img_h = (uint32_t)LCD_MP_HEIGHT;
    uint32_t row_bytes = img_w * 3U;               // 3 bytes per pixel (BGR888)
    uint32_t padded_row = (row_bytes + 3U) & ~3U;  // rows must be 4-byte aligned
    uint32_t file_size = 54U + padded_row * img_h; // 14 (file hdr) + 40 (DIB hdr) + pixel data

    // --- BMP file header (14 bytes) ---
    uint8_t file_hdr[14];
    memset(file_hdr, 0, sizeof(file_hdr));
    file_hdr[0] = 'B';
    file_hdr[1] = 'M';
    file_hdr[2] = (uint8_t)(file_size);
    file_hdr[3] = (uint8_t)(file_size >> 8);
    file_hdr[4] = (uint8_t)(file_size >> 16);
    file_hdr[5] = (uint8_t)(file_size >> 24);
    // reserved: bytes 6-9 remain 0
    file_hdr[10] = 54; // pixel data offset = 54

    // --- BITMAPINFOHEADER (40 bytes), 24-bit top-down ---
    uint32_t u_neg_h = (uint32_t)(-(int32_t)img_h); // two's-complement negative height → top-down scan
    uint8_t dib_hdr[40];
    memset(dib_hdr, 0, sizeof(dib_hdr));
    dib_hdr[0] = 40;               // header size
    dib_hdr[4] = (uint8_t)(img_w); // width (LE)
    dib_hdr[5] = (uint8_t)(img_w >> 8);
    dib_hdr[6] = (uint8_t)(img_w >> 16);
    dib_hdr[7] = (uint8_t)(img_w >> 24);
    dib_hdr[8] = (uint8_t)(u_neg_h); // height, negative = top-down (LE)
    dib_hdr[9] = (uint8_t)(u_neg_h >> 8);
    dib_hdr[10] = (uint8_t)(u_neg_h >> 16);
    dib_hdr[11] = (uint8_t)(u_neg_h >> 24);
    dib_hdr[12] = 1;  // color planes
    dib_hdr[14] = 24; // bits per pixel
    // compression (BI_RGB=0), image size, pixels/meter, colors: all 0

    if (!storage_file_write_file_chunk(file, file_hdr, sizeof(file_hdr)) ||
        !storage_file_write_file_chunk(file, dib_hdr, sizeof(dib_hdr)))
    {
        storage_file_close(file);
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to write BMP header to file: %s", path);
        m_free(path);
        path = NULL;
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }

    // --- Write pixel rows ---
    // Framebuffers are 8-bit RGB332 (R[7:5] G[4:2] B[1:0]).
    // BMP expects BGR888, rows padded to 4 bytes.
    uint8_t *pixel_row = m_new(uint8_t, padded_row);
    memset(pixel_row, 0, padded_row); // zero padding bytes once
    uint8_t *src_row = m_new(uint8_t, img_w);
    bool write_error = false;
    for (uint32_t ry = 0; ry < img_h; ry++)
    {
        LCD_MP_READ_ROW(ry, src_row);
        for (uint32_t rx = 0; rx < img_w; rx++)
        {
            uint8_t p = src_row[rx];
            uint8_t r3 = (p >> 5) & 0x7U;
            uint8_t g3 = (p >> 2) & 0x7U;
            uint8_t b2 = p & 0x3U;
            pixel_row[rx * 3U + 0U] = (uint8_t)((b2 << 6) | (b2 << 4) | (b2 << 2) | b2); // B
            pixel_row[rx * 3U + 1U] = (uint8_t)((g3 << 5) | (g3 << 2) | (g3 >> 1));      // G
            pixel_row[rx * 3U + 2U] = (uint8_t)((r3 << 5) | (r3 << 2) | (r3 >> 1));      // R
        }
        if (!storage_file_write_file_chunk(file, pixel_row, padded_row))
        {
            write_error = true;
            break;
        }
    }
    m_free(path);
    path = NULL;
    m_del(uint8_t, src_row, img_w);
    m_del(uint8_t, pixel_row, padded_row);
    storage_file_close(file);

    if (write_error)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to write pixel data to BMP file: %s", path);
    }
#endif
#endif
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_js_swap(struct mjs *mjs)
{
    LCD_SWAP();
    mjs_return(mjs, MJS_UNDEFINED);
}

void lcd_create(struct mjs *mjs, mjs_val_t *lcd_obj)
{
    *lcd_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *lcd_obj, "clear", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_clear));
    mjs_set(mjs, *lcd_obj, "pixel", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_pixel));
    mjs_set(mjs, *lcd_obj, "len", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_len));
    mjs_set(mjs, *lcd_obj, "line", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_line));
    mjs_set(mjs, *lcd_obj, "rectangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_rectangle));
    mjs_set(mjs, *lcd_obj, "fillRectangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_rectangle));
    mjs_set(mjs, *lcd_obj, "fillRoundRectangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_round_rectangle));
    mjs_set(mjs, *lcd_obj, "circle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_circle));
    mjs_set(mjs, *lcd_obj, "fillCircle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_circle));
    mjs_set(mjs, *lcd_obj, "triangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_triangle));
    mjs_set(mjs, *lcd_obj, "screenshot", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_screenshot));
    mjs_set(mjs, *lcd_obj, "fillTriangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_triangle));
    mjs_set(mjs, *lcd_obj, "char", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_char));
    mjs_set(mjs, *lcd_obj, "text", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_text));
    mjs_set(mjs, *lcd_obj, "swap", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_swap));
}
