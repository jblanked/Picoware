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

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // Triangle3D* in C++
        bool freed;
    } triangle3d_mp_obj_t;

    extern const mp_obj_type_t triangle3d_mp_type;

    void triangle3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t triangle3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t triangle3d_mp_del(mp_obj_t self_in);
    void triangle3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
    mp_obj_t triangle3d_mp_center(mp_obj_t self_in);
    mp_obj_t triangle3d_mp_is_facing_camera(mp_obj_t self_in, mp_obj_t camera_pos_vector);

    mp_obj_t triangle3d_mp_set_x1(mp_obj_t self_in, mp_obj_t x1_obj);
    mp_obj_t triangle3d_mp_set_y1(mp_obj_t self_in, mp_obj_t y1_obj);
    mp_obj_t triangle3d_mp_set_z1(mp_obj_t self_in, mp_obj_t z1_obj);
    mp_obj_t triangle3d_mp_set_x2(mp_obj_t self_in, mp_obj_t x2_obj);
    mp_obj_t triangle3d_mp_set_y2(mp_obj_t self_in, mp_obj_t y2_obj);
    mp_obj_t triangle3d_mp_set_z2(mp_obj_t self_in, mp_obj_t z2_obj);
    mp_obj_t triangle3d_mp_set_x3(mp_obj_t self_in, mp_obj_t x3_obj);
    mp_obj_t triangle3d_mp_set_y3(mp_obj_t self_in, mp_obj_t y3_obj);
    mp_obj_t triangle3d_mp_set_z3(mp_obj_t self_in, mp_obj_t z3_obj);
    mp_obj_t triangle3d_mp_set_visible(mp_obj_t self_in, mp_obj_t visible_obj);
    mp_obj_t triangle3d_mp_set_distance(mp_obj_t self_in, mp_obj_t distance_obj);
    mp_obj_t triangle3d_mp_set_color(mp_obj_t self_in, mp_obj_t color_obj);

#ifdef __cplusplus
}
#endif