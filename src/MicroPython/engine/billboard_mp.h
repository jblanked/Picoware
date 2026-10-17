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
        void *context;
    } billboard_mp_obj_t;

    extern const mp_obj_type_t billboard_mp_type;

    void billboard_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t billboard_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t billboard_mp_del(mp_obj_t self_in);
    void billboard_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t billboard_mp_set_counts(mp_obj_t self_in, mp_obj_t d, mp_obj_t p);
    mp_obj_t billboard_mp_set_direction_pose(size_t, const mp_obj_t *args);
    mp_obj_t billboard_mp_set_direction_pose_data(size_t, const mp_obj_t *args);

#ifdef __cplusplus
}

#endif