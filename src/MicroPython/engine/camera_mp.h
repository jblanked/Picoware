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

    typedef struct camera_mp_obj_t
    {
        mp_obj_base_t base;
        void *context; // Camera* in C++
        bool freed;
    } camera_mp_obj_t;

    extern const mp_obj_type_t camera_mp_type;

    void camera_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t camera_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t camera_mp_del(mp_obj_t self_in);
    void camera_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

#ifdef __cplusplus
}
#endif