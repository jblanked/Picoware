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
        uint16_t spinner_color_565;
        uint16_t background_color_565;
        bool animating;
        uint32_t time_start;
        uint32_t time_elapsed;
        lv_obj_t *spinner;
        lv_obj_t *text_label;
        lv_obj_t *time_label;
        bool freed;
    } picoware_lvgl_loading_obj_t;

    extern const mp_obj_type_t picoware_lvgl_loading_type;

    void picoware_lvgl_loading_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t picoware_lvgl_loading_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // Loading constructor
    mp_obj_t picoware_lvgl_loading_del(mp_obj_t self_in);                                                                 // Loading destructor
    void picoware_lvgl_loading_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // Loading attribute getter/setter
    mp_obj_t picoware_lvgl_loading_get_text(mp_obj_t self_in);                                                            // Loading.text property getter
    mp_obj_t picoware_lvgl_loading_set_text(mp_obj_t self_in, mp_obj_t value);                                            // Loading.text property setter
    mp_obj_t picoware_lvgl_loading_animate(size_t n_args, const mp_obj_t *args);                                          // Loading.animate(swap=True) - Animate the loading spinner
    mp_obj_t picoware_lvgl_loading_stop(mp_obj_t self_in);                                                                // Loading.stop() - Stop the loading animation

#ifdef __cplusplus
}
#endif
