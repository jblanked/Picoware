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

    typedef struct
    {
        mp_obj_base_t base;
        int state;
        uint16_t foreground_color_565;
        uint16_t background_color_565;
        int16_t pos_x;
        int16_t pos_y;
        int16_t width;
        int16_t height;
        size_t num_options;
        lv_obj_t *screen;
        lv_obj_t *title_label;
        lv_obj_t *dropdown;
        bool freed;
    } picoware_lvgl_choice_obj_t;

    extern const mp_obj_type_t picoware_lvgl_choice_type;

    void picoware_lvgl_choice_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the Choice object
    mp_obj_t picoware_lvgl_choice_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // Choice constructor
    mp_obj_t picoware_lvgl_choice_del(mp_obj_t self_in);                                                                 // Choice destructor
    void picoware_lvgl_choice_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // Choice attribute handler

    mp_obj_t picoware_lvgl_choice_get_state(mp_obj_t self_in);                 // Choice.state property getter
    mp_obj_t picoware_lvgl_choice_set_state(mp_obj_t self_in, mp_obj_t value); // Choice.state property setter
    mp_obj_t picoware_lvgl_choice_clear(mp_obj_t self_in);                     // Choice.clear() - Clear the choice (hide it)
    mp_obj_t picoware_lvgl_choice_draw(mp_obj_t self_in);                      // Choice.draw() - Draw the choice
    mp_obj_t picoware_lvgl_choice_reset(mp_obj_t self_in);                     // Choice.reset() - Reset to initial state
    mp_obj_t picoware_lvgl_choice_scroll_down(mp_obj_t self_in);               // Choice.scroll_down() - Scroll to next option
    mp_obj_t picoware_lvgl_choice_scroll_up(mp_obj_t self_in);                 // Choice.scroll_up() - Scroll to previous option
    mp_obj_t picoware_lvgl_choice_close(mp_obj_t self_in);                     // Choice.close() - Close the dropdown
    mp_obj_t picoware_lvgl_choice_is_open(mp_obj_t self_in);                   // Choice.is_open() - Check if dropdown is open
    mp_obj_t picoware_lvgl_choice_open(mp_obj_t self_in);                      // Choice.open() - Open the dropdown

#ifdef __cplusplus
}
#endif
