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

    typedef struct
    {
        mp_obj_base_t base;
        bool initialized;
        bool was_capitalized;
    } input_mp_obj_t;

    extern const mp_obj_type_t input_mp_type;

    void input_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t input_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t input_mp_del(mp_obj_t self_in);
    void input_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t input_mp_button_to_char(mp_obj_t self_in, mp_obj_t button);
    mp_obj_t input_mp_deinit(mp_obj_t self_in);
    mp_obj_t input_mp_get_input(mp_obj_t self_in);
    mp_obj_t input_mp_get_last_button(mp_obj_t self_in);
    mp_obj_t input_mp_key_to_button(mp_obj_t self_in, mp_obj_t key);

#ifdef __cplusplus
}
#endif