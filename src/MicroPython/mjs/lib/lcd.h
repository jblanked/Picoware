#pragma once
#include "mjs.h"

void lcd_js_char(struct mjs *mjs);
void lcd_js_circle(struct mjs *mjs);
void lcd_js_clear(struct mjs *mjs);
void lcd_js_fill_circle(struct mjs *mjs);
void lcd_js_fill_rectangle(struct mjs *mjs);
void lcd_js_fill_round_rectangle(struct mjs *mjs);
void lcd_js_fill_triangle(struct mjs *mjs);
void lcd_js_len(struct mjs *mjs);
void lcd_js_line(struct mjs *mjs);
void lcd_js_pixel(struct mjs *mjs);
void lcd_js_rectangle(struct mjs *mjs);
void lcd_js_text(struct mjs *mjs);
void lcd_js_triangle(struct mjs *mjs);
void lcd_js_screenshot(struct mjs *mjs);
void lcd_js_swap(struct mjs *mjs);
//
void lcd_create(struct mjs *mjs, mjs_val_t *lcd_obj);