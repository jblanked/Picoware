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
#include "sprite3d_mp.h"
#include "engine_mp.h"

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // Entity* in C++
        bool freed;
        mp_obj_t start;
        mp_obj_t stop;
        mp_obj_t update;
        mp_obj_t render;
        mp_obj_t collision;
    } entity_mp_obj_t;

    extern const mp_obj_type_t entity_mp_type;

    void entity_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t entity_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t entity_mp_del(mp_obj_t self_in);
    void entity_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t entity_mp_has_3d_sprite(mp_obj_t self_in);
    mp_obj_t entity_mp_set_3d_sprite_rotation(mp_obj_t self_in, mp_obj_t rotation);
    mp_obj_t entity_mp_set_3d_sprite_scale(mp_obj_t self_in, mp_obj_t scale);
    mp_obj_t entity_mp_update_3d_sprite_position(mp_obj_t self_in);

    mp_obj_t entity_mp_has_changed_position(mp_obj_t self_in);

#ifdef __cplusplus
}
#endif