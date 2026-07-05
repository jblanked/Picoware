#pragma once
#include "../mjs/mjs.h"

void lcd_mp_char(struct mjs *mjs);
void lcd_mp_circle(struct mjs *mjs);
void lcd_mp_clear(struct mjs *mjs);
void lcd_mp_fill_circle(struct mjs *mjs);
void lcd_mp_fill_rectangle(struct mjs *mjs);
void lcd_mp_fill_round_rectangle(struct mjs *mjs);
void lcd_mp_fill_triangle(struct mjs *mjs);
void lcd_mp_line(struct mjs *mjs);
void lcd_mp_pixel(struct mjs *mjs);
void lcd_mp_rectangle(struct mjs *mjs);
void lcd_mp_text(struct mjs *mjs);
void lcd_mp_triangle(struct mjs *mjs);
void lcd_mp_swap(struct mjs *mjs);
//
void lcd_register(struct mjs *mjs);