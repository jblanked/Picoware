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
        void *game; // pointer to the GhoulsGame instance
        bool freed; // whether the game has been freed
    } ghouls_mp_obj_t;

    extern const mp_obj_type_t ghouls_mp_type;

    void ghouls_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the Ghouls object
    mp_obj_t ghouls_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the Ghouls object
    mp_obj_t ghouls_mp_del(mp_obj_t self_in);                                                                 // destructor for the Ghouls object
    void ghouls_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the Ghouls object

    mp_obj_t ghouls_mp_update_draw(mp_obj_t self_in);                               // method to render the game (called in a loop)
    mp_obj_t ghouls_mp_update_input(mp_obj_t self_in, mp_obj_t button_pressed_obj); // method to update input state (call when a button is pressed/released)

#ifdef __cplusplus
}
#endif