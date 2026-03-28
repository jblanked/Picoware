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
#include "picoware_lvgl.h"

#define CHARACTERS_PER_LINE (DISPLAY_WIDTH / LVGL_FONT_WIDTH)
#define LINES_PER_SCREEN (DISPLAY_HEIGHT / LVGL_LINE_HEIGHT)

    typedef struct
    {
        mp_obj_base_t base;
        uint16_t foreground_color_565;
        uint16_t background_color_565;
        bool show_scrollbar;
        int16_t y;
        int16_t height;
        uint16_t characters_per_line;
        uint16_t lines_per_screen;
        uint16_t total_lines;
        int16_t current_line;
        lv_obj_t *textarea;
    } picoware_lvgl_textbox_obj_t;

    extern const mp_obj_type_t picoware_lvgl_textbox_type;

    void picoware_lvgl_textbox_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // TextBox print function
    mp_obj_t picoware_lvgl_textbox_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // TextBox constructor
    mp_obj_t picoware_lvgl_textbox_del(mp_obj_t self_in);                                                                 // TextBox destructor
    void picoware_lvgl_textbox_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // TextBox attribute getter/setter

    mp_obj_t picoware_lvgl_textbox_get_text(mp_obj_t self_in);                            // TextBox.text property getter
    mp_obj_t picoware_lvgl_textbox_get_text_height(mp_obj_t self_in);                     // TextBox.text_height property getter
    mp_obj_t picoware_lvgl_textbox_clear(mp_obj_t self_in);                               // TextBox.clear() - Clear the textbox
    mp_obj_t picoware_lvgl_textbox_refresh(mp_obj_t self_in);                             // TextBox.refresh() - Refresh the display
    mp_obj_t picoware_lvgl_textbox_scroll_down(mp_obj_t self_in);                         // TextBox.scroll_down() - Scroll down by one line
    mp_obj_t picoware_lvgl_textbox_scroll_up(mp_obj_t self_in);                           // TextBox.scroll_up() - Scroll up by one line
    mp_obj_t picoware_lvgl_textbox_set_current_line(mp_obj_t self_in, mp_obj_t line_obj); // TextBox.set_current_line(line) - Scroll to specific line
    mp_obj_t picoware_lvgl_textbox_set_text(mp_obj_t self_in, mp_obj_t text_obj);         // TextBox.set_text(text) - Set text content

#ifdef __cplusplus
}
#endif
