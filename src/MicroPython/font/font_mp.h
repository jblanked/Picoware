#pragma once
#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "font.h"

#ifndef STATIC
#define STATIC static
#endif

#define FONT_DEFAULT FONT_XTRA_SMALL

typedef struct
{
    mp_obj_base_t base;
    bool initialized;
} font_mp_obj_t;

const uint8_t *font_get_character(FontSize size, char c); // Get the bitmap data for a specific character in the specified font size
const uint8_t *font_get_data(FontSize size);              // Get the font data pointer for a given font size
FontTable font_get_table(FontSize size);                  // Get the FontTable structure for a given font size
uint8_t font_get_height(FontSize size);                   // Get the height of a font in pixels
uint8_t font_get_spacing(FontSize size);                  // Get the spacing of a font in pixels
uint8_t font_get_width(FontSize size);                    // Get the width of a font in pixels

mp_obj_t font_mp_get_character(mp_obj_t self_in, mp_obj_t size, mp_obj_t char_obj); // Get the bitmap data for a specific character in the specified font size
mp_obj_t font_mp_get_data(mp_obj_t self_in, mp_obj_t size);                         // Get the font data pointer for a given font size
mp_obj_t font_mp_get_height(mp_obj_t self_in, mp_obj_t size);                       // Get the height of a font in pixels
mp_obj_t font_mp_get_spacing(mp_obj_t self_in, mp_obj_t size);                      // Get the spacing of a font in pixels
mp_obj_t font_mp_get_width(mp_obj_t self_in, mp_obj_t size);                        // Get the width of a font in pixels

void font_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the font object
mp_obj_t font_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the font object
mp_obj_t font_mp_del(mp_obj_t self_in);                                                                 // destructor for the font object
void font_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the font object (e.g., to access properties like height and width

typedef struct
{
    mp_obj_base_t base;
    FontSize size;
    uint8_t spacing;
    uint8_t width;
    uint8_t height;
} font_size_mp_obj_t;

void font_size_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the font size object
mp_obj_t font_size_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the font size object
mp_obj_t font_size_mp_del(mp_obj_t self_in);                                                                 // destructor for the font size object
void font_size_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the font size object (e.g., to access properties like height and width)