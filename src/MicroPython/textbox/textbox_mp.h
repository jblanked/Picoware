/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include <string.h>

#define TEXTBOX_INITIAL_LINE_CAPACITY 64
#define TEXTBOX_SCROLLBAR_WIDTH 6
#define TEXTBOX_INITIAL_EDIT_CAPACITY 256

    // Stores the start byte-offset and character count of one wrapped line
    typedef struct
    {
        uint32_t start;  // byte offset into the text buffer
        uint16_t length; // number of characters on this line
    } textbox_line_t;

    typedef struct
    {
        mp_obj_base_t base;
        // Text storage
        const char *text;
        size_t text_len;
        // Geometry
        uint16_t pos_y;      // top-left y of the textbox
        uint16_t box_width;  // full display width
        uint16_t box_height; // height of the textbox in pixels
        // Font / layout
        uint16_t chars_per_line;   // maximum characters per wrapped line
        uint16_t spacing;          // vertical distance between line baselines (pixels)
        uint16_t lines_per_screen; // box_height / spacing
        // Colours
        uint16_t foreground_color;
        uint16_t background_color;
        // Scrollbar
        bool show_scrollbar;
        // Line-wrap cache
        textbox_line_t *lines; // GC-allocated array of line descriptors
        uint16_t total_lines;
        uint16_t line_capacity;
        uint16_t current_line;
        bool cache_valid;
        // Cursor state
        size_t cursor_pos; // byte offset of the cursor in the text
        bool show_cursor;  // whether to render the cursor
        bool freed;
        // Editing
        char *edit_buf;
        size_t edit_buf_capacity;
    } textbox_mp_obj_t;

    extern const mp_obj_type_t textbox_mp_type;

    // Lifecycle
    void textbox_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t textbox_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t textbox_mp_del(mp_obj_t self_in);
    void textbox_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    // Methods exposed to Python
    mp_obj_t textbox_mp_render(mp_obj_t self_in);                          // re-wrap + redraw + swap
    mp_obj_t textbox_mp_scroll_up(mp_obj_t self_in);                       // scroll up one line
    mp_obj_t textbox_mp_scroll_down(mp_obj_t self_in);                     // scroll down one line
    mp_obj_t textbox_mp_clear(mp_obj_t self_in);                           // clear text and redraw
    mp_obj_t textbox_mp_set_text(mp_obj_t self_in, mp_obj_t text);         // set text and redraw
    mp_obj_t textbox_mp_set_current_line(mp_obj_t self_in, mp_obj_t line); // jump to line
    mp_obj_t textbox_mp_set_cursor(mp_obj_t self_in, mp_obj_t pos_in);     // set cursor position, scroll viewport, and redraw
    mp_obj_t textbox_mp_cursor_up(mp_obj_t self_in);                       // move cursor up one wrapped line
    mp_obj_t textbox_mp_cursor_down(mp_obj_t self_in);                     // move cursor down one wrapped line
    mp_obj_t textbox_mp_insert_char(mp_obj_t self_in, mp_obj_t char_in);   // insert char at cursor and advance
    mp_obj_t textbox_mp_delete_char(mp_obj_t self_in);                     // delete char before cursor (backspace)

#ifdef __cplusplus
}
#endif