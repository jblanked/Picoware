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
        bool state;
        uint16_t foreground_color_565;
        uint16_t background_color_565;
        uint16_t on_color_565;
        uint16_t border_color_565;
        int16_t pos_x;
        int16_t pos_y;
        int16_t width;
        int16_t height;
        lv_obj_t *screen;
        lv_obj_t *switch_obj;
        lv_obj_t *label;
        bool freed;
    } picoware_lvgl_toggle_obj_t;

    extern const mp_obj_type_t picoware_lvgl_toggle_type;

    void picoware_lvgl_toggle_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the Toggle object
    mp_obj_t picoware_lvgl_toggle_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the Toggle object
    mp_obj_t picoware_lvgl_toggle_del(mp_obj_t self_in);                                                                 // destructor for the Toggle object
    void picoware_lvgl_toggle_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the Toggle object

    mp_obj_t picoware_lvgl_toggle_get_state(mp_obj_t self_in);                 // Getter for the 'state' property
    mp_obj_t picoware_lvgl_toggle_set_state(mp_obj_t self_in, mp_obj_t value); // Setter for the 'state' property

    mp_obj_t picoware_lvgl_toggle_get_text(mp_obj_t self_in);                 // Getter for the 'text' property
    mp_obj_t picoware_lvgl_toggle_set_text(mp_obj_t self_in, mp_obj_t value); // Setter for the 'text' property

    mp_obj_t picoware_lvgl_toggle_draw(size_t n_args, const mp_obj_t *args);                       // Method to draw the toggle on the screen
    mp_obj_t picoware_lvgl_toggle_toggle(mp_obj_t self_in);                                        // Method to toggle the state
    mp_obj_t picoware_lvgl_toggle_update(mp_obj_t self_in, mp_obj_t text_obj, mp_obj_t state_obj); // Method to update text and state

#ifdef __cplusplus
}
#endif
