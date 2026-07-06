#include "lcd.h"
#include "../../lcd/lcd_config.h"
#include <string.h>

#include LCD_INCLUDE

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

    uint16_t color = arg_u16(mjs, 3);
    FontSize size = (FontSize)arg_u16(mjs, 4);
    LCD_MP_CHAR(x, y, c, color, size);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_circle(struct mjs *mjs)
{
    uint16_t cx = arg_u16(mjs, 0);
    uint16_t cy = arg_u16(mjs, 1);
    uint16_t radius = arg_u16(mjs, 2);
    uint16_t color = arg_u16(mjs, 3);
    LCD_MP_CIRCLE(cx, cy, radius, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_clear(struct mjs *mjs)
{
    uint16_t color = arg_u16(mjs, 0);
    LCD_MP_CLEAR(color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_fill_circle(struct mjs *mjs)
{
    uint16_t cx = arg_u16(mjs, 0);
    uint16_t cy = arg_u16(mjs, 1);
    uint16_t radius = arg_u16(mjs, 2);
    uint16_t color = arg_u16(mjs, 3);
    LCD_MP_FILL_CIRCLE(cx, cy, radius, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_fill_rectangle(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t w = arg_u16(mjs, 2);
    uint16_t h = arg_u16(mjs, 3);
    uint16_t color = arg_u16(mjs, 4);
    LCD_MP_FILL_RECTANGLE(x, y, w, h, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_fill_round_rectangle(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t w = arg_u16(mjs, 2);
    uint16_t h = arg_u16(mjs, 3);
    uint16_t r = arg_u16(mjs, 4);
    uint16_t color = arg_u16(mjs, 5);
    LCD_MP_FILL_ROUND_RECTANGLE(x, y, w, h, r, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_fill_triangle(struct mjs *mjs)
{
    uint16_t x1 = arg_u16(mjs, 0);
    uint16_t y1 = arg_u16(mjs, 1);
    uint16_t x2 = arg_u16(mjs, 2);
    uint16_t y2 = arg_u16(mjs, 3);
    uint16_t x3 = arg_u16(mjs, 4);
    uint16_t y3 = arg_u16(mjs, 5);
    uint16_t color = arg_u16(mjs, 6);
    LCD_MP_FILL_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_line(struct mjs *mjs)
{
    uint16_t x1 = arg_u16(mjs, 0);
    uint16_t y1 = arg_u16(mjs, 1);
    uint16_t x2 = arg_u16(mjs, 2);
    uint16_t y2 = arg_u16(mjs, 3);
    uint16_t color = arg_u16(mjs, 4);
    LCD_MP_LINE(x1, y1, x2, y2, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_pixel(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t color = arg_u16(mjs, 2);
    LCD_MP_PIXEL(x, y, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_rectangle(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);
    uint16_t w = arg_u16(mjs, 2);
    uint16_t h = arg_u16(mjs, 3);
    uint16_t color = arg_u16(mjs, 4);
    LCD_MP_RECTANGLE(x, y, w, h, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_text(struct mjs *mjs)
{
    uint16_t x = arg_u16(mjs, 0);
    uint16_t y = arg_u16(mjs, 1);

    mjs_val_t t_arg = mjs_arg(mjs, 2);
    size_t len;
    const char *text = mjs_get_string(mjs, &t_arg, &len);

    uint16_t color = arg_u16(mjs, 3);
    FontSize size = (FontSize)arg_u16(mjs, 4);
    LCD_MP_TEXT(x, y, text, color, size);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_triangle(struct mjs *mjs)
{
    uint16_t x1 = arg_u16(mjs, 0);
    uint16_t y1 = arg_u16(mjs, 1);
    uint16_t x2 = arg_u16(mjs, 2);
    uint16_t y2 = arg_u16(mjs, 3);
    uint16_t x3 = arg_u16(mjs, 4);
    uint16_t y3 = arg_u16(mjs, 5);
    uint16_t color = arg_u16(mjs, 6);
    LCD_MP_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_js_swap(struct mjs *mjs)
{
    LCD_SWAP();
    mjs_return(mjs, mjs_mk_undefined());
}

void lcd_register(struct mjs *mjs)
{
    mjs_val_t global = mjs_get_global(mjs);

    mjs_set(mjs, global, "lcd_clear", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_clear));
    mjs_set(mjs, global, "lcd_pixel", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_pixel));
    mjs_set(mjs, global, "lcd_line", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_line));
    mjs_set(mjs, global, "lcd_rectangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_rectangle));
    mjs_set(mjs, global, "lcd_fill_rectangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_rectangle));
    mjs_set(mjs, global, "lcd_fill_round_rectangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_round_rectangle));
    mjs_set(mjs, global, "lcd_circle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_circle));
    mjs_set(mjs, global, "lcd_fill_circle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_circle));
    mjs_set(mjs, global, "lcd_triangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_triangle));
    mjs_set(mjs, global, "lcd_fill_triangle", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_fill_triangle));
    mjs_set(mjs, global, "lcd_char", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_char));
    mjs_set(mjs, global, "lcd_text", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_text));
    mjs_set(mjs, global, "lcd_swap", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lcd_js_swap));
}
