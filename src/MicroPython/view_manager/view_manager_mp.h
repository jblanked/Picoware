/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once
#define VIEW_MANAGER_MAX_VIEWS 10
#define VIEW_MANAGER_MAX_STACK 10

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "../view/view_mp.h"

    typedef struct
    {
        mp_obj_base_t base;
        bool _active;
        uint16_t _background_color;
        mp_obj_t _current_view; // View
        uint16_t _foreground_color;
        uint16_t _selected_color;
        uint8_t _stack_depth;
        uint8_t _view_count;
        mp_obj_t views;      // array
        mp_obj_t view_stack; // array
    } view_manager_mp_obj_t;

    extern const mp_obj_type_t view_manager_mp_type;

    void view_manager_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t view_manager_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t view_manager_mp_del(mp_obj_t self_in);
    void view_manager_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t view_manager_mp_set_active(mp_obj_t self_in, mp_obj_t active);
    mp_obj_t view_manager_mp_set_background_color(mp_obj_t self_in, mp_obj_t color);
    mp_obj_t view_manager_mp_set_foreground_color(mp_obj_t self_in, mp_obj_t color);
    mp_obj_t view_manager_mp_set_current_view(mp_obj_t self_in, mp_obj_t view);
    mp_obj_t view_manager_mp_set_selected_color(mp_obj_t self_in, mp_obj_t color);
    mp_obj_t view_manager_mp_set_stack_depth(mp_obj_t self_in, mp_obj_t depth);
    mp_obj_t view_manager_mp_set_view_count(mp_obj_t self_in, mp_obj_t count);
    mp_obj_t view_manager_mp_set_views(mp_obj_t self_in, mp_obj_t views);
    mp_obj_t view_manager_mp_set_view_stack(mp_obj_t self_in, mp_obj_t view_stack);

    mp_obj_t view_manager_mp_clear(mp_obj_t self_in);
    mp_obj_t view_manager_mp_clear_stack(mp_obj_t self_in);
    mp_obj_t view_manager_mp_get_view(mp_obj_t self_in, mp_obj_t view_name);

#ifdef __cplusplus
}
#endif