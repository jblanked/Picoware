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

    struct mjs;

    typedef struct
    {
        mp_obj_base_t base;
        bool is_initialized;
        struct mjs *mjs;
    } mjs_mp_obj_t;

    extern const mp_obj_type_t mjs_mp_type;

    void mjs_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the MJS object
    mp_obj_t mjs_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the MJS object
    mp_obj_t mjs_mp_del(mp_obj_t self_in);                                                                 // destructor for the MJS object
    void mjs_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the MJS object

    mp_obj_t mjs_mp_exec(mp_obj_t self_in, mp_obj_t path);   // execute JavaScript code from a file
    mp_obj_t mjs_mp_run(mp_obj_t self_in, mp_obj_t js_code); // execute JavaScript code

#ifdef __cplusplus
}
#endif