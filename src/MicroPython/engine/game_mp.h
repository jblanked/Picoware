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
#include "engine_mp.h"
#include "level_mp.h"

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // Game* in C++
        bool freed;
        mp_obj_t start;
        mp_obj_t stop;
        mp_obj_t update;
        mp_obj_t draw;
        mp_obj_t position_obj;
        mp_obj_t size_obj;
        mp_obj_t camera_obj;
        mp_obj_t current_level_obj;
    } game_mp_obj_t;

    extern const mp_obj_type_t game_mp_type;

    void game_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t game_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t game_mp_del(mp_obj_t self_in);
    void game_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t game_mp_level_add(mp_obj_t self_in, mp_obj_t level);
    mp_obj_t game_mp_level_remove(mp_obj_t self_in, mp_obj_t level);
    mp_obj_t game_mp_level_switch(mp_obj_t self_in, mp_obj_t index);
    mp_obj_t game_mp_set_camera(mp_obj_t self_in, mp_obj_t camera);
    mp_obj_t game_mp_set_input(mp_obj_t self_in, mp_obj_t input_in);

    mp_obj_t game_mp_set_name(mp_obj_t self_in, mp_obj_t name_obj);
    mp_obj_t game_mp_set_position(mp_obj_t self_in, mp_obj_t position_obj);
    mp_obj_t game_mp_set_size(mp_obj_t self_in, mp_obj_t size_obj);
    mp_obj_t game_mp_set_is_active(mp_obj_t self_in, mp_obj_t is_active_obj);
    mp_obj_t game_mp_set_foreground_color(mp_obj_t self_in, mp_obj_t fg_color_obj);
    mp_obj_t game_mp_set_background_color(mp_obj_t self_in, mp_obj_t bg_color_obj);
    mp_obj_t game_mp_set_current_level(mp_obj_t self_in, mp_obj_t level_in);

    mp_obj_t game_mp_level_exists(mp_obj_t self_in, mp_obj_t level_in);

#ifdef __cplusplus
}
#endif