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
#include "entity_mp.h"

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // Level* in C++
        bool freed;
        mp_obj_t start;
        mp_obj_t stop;
        mp_obj_t size_obj;
    } level_mp_obj_t;

    extern const mp_obj_type_t level_mp_type;

    void level_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t level_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t level_mp_del(mp_obj_t self_in);
    void level_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t level_mp_clear(mp_obj_t self_in);
    mp_obj_t level_mp_entity_add(mp_obj_t self_in, mp_obj_t entity);
    mp_obj_t level_mp_entity_remove(mp_obj_t self_in, mp_obj_t entity);

    mp_obj_t level_mp_set_name(mp_obj_t self_in, mp_obj_t name_obj);
    mp_obj_t level_mp_set_size(mp_obj_t self_in, mp_obj_t size_obj);
    mp_obj_t level_mp_set_clear_allowed(mp_obj_t self_in, mp_obj_t clear_allowed_obj);

#ifdef __cplusplus
}
#endif