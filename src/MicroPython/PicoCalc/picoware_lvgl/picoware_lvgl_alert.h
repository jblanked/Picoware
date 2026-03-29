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
        uint16_t text_color_565;
        uint16_t background_color_565;
        bool is_circular;
        lv_obj_t *msgbox;
        bool freed;
    } picoware_lvgl_alert_obj_t;

    extern const mp_obj_type_t picoware_lvgl_alert_type;

    void picoware_lvgl_alert_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t picoware_lvgl_alert_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t picoware_lvgl_alert_del(mp_obj_t self_in);
    void picoware_lvgl_alert_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t picoware_lvgl_alert_clear(mp_obj_t self_in);
    mp_obj_t picoware_lvgl_alert_draw(mp_obj_t self_in, mp_obj_t title_in);
    mp_obj_t picoware_lvgl_alert_get_text(mp_obj_t self_in);
    mp_obj_t picoware_lvgl_alert_set_text(mp_obj_t self_in, mp_obj_t text_in);

#ifdef __cplusplus
}
#endif
