#pragma once
#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "lcd_config.h"

#ifndef STATIC
#define STATIC static
#endif

typedef struct
{
    mp_obj_base_t base;
    bool initialized;
    uint16_t width;
    uint16_t height;
} lcd_mp_obj_t;

void lcd_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the LCD object
mp_obj_t lcd_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the LCD object
mp_obj_t lcd_mp_del(mp_obj_t self_in);                                                                 // destructor for the LCD object
void lcd_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the LCD object (e.g., to access properties like width and height

mp_obj_t lcd_mp_char(size_t n_args, const mp_obj_t *args);                 // draw a character on the LCD
mp_obj_t lcd_mp_circle(size_t n_args, const mp_obj_t *args);               // draw a circle on the LCD
mp_obj_t lcd_mp_clear(mp_obj_t self_in, mp_obj_t color);                   // clear the LCD framebuffer
mp_obj_t lcd_mp_fill_circle(size_t n_args, const mp_obj_t *args);          // fill a circle on the LCD
mp_obj_t lcd_mp_fill_rectangle(size_t n_args, const mp_obj_t *args);       // fill a rectangle on the LCD
mp_obj_t lcd_mp_fill_round_rectangle(size_t n_args, const mp_obj_t *args); // fill a rounded rectangle on the LCD
mp_obj_t lcd_mp_fill_triangle(size_t n_args, const mp_obj_t *args);        // fill a triangle
mp_obj_t lcd_mp_image_bytearray(size_t n_args, const mp_obj_t *args);      // draw an image from a bytearray on the LCD
mp_obj_t lcd_mp_line(size_t n_args, const mp_obj_t *args);                 // draw a line on the LCD
mp_obj_t lcd_mp_pixel(size_t n_args, const mp_obj_t *args);                // draw a pixel on the LCD
mp_obj_t lcd_mp_psram(size_t n_args, const mp_obj_t *args);                // draw a buffer from PSRAM
mp_obj_t lcd_mp_rectangle(size_t n_args, const mp_obj_t *args);            // draw a rectangle on the LCD
mp_obj_t lcd_mp_set_mode(mp_obj_t self_in, mp_obj_t mode);                 // set the LCD mode (PSRAM or HEAP)
mp_obj_t lcd_mp_swap(mp_obj_t self_in);                                    // swap function to update the display with the current framebuffer contents
mp_obj_t lcd_mp_text(size_t n_args, const mp_obj_t *args);                 // draw text on the LCD
mp_obj_t lcd_mp_triangle(size_t n_args, const mp_obj_t *args);             // draw a triangle on the LCD
