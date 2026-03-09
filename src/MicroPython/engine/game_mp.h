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
    } game_mp_obj_t;

    mp_obj_t game_mp_get_current_draw(void);

    extern const mp_obj_type_t game_mp_type;

    void game_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t game_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t game_mp_del(mp_obj_t self_in);
    void game_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t game_mp_get_camera(mp_obj_t self_in);
    mp_obj_t game_mp_level_add(mp_obj_t self_in, mp_obj_t level);
    mp_obj_t game_mp_level_remove(mp_obj_t self_in, mp_obj_t level);
    mp_obj_t game_mp_level_switch(mp_obj_t self_in, mp_obj_t index);
    mp_obj_t game_mp_set_camera(mp_obj_t self_in, mp_obj_t camera);
    mp_obj_t game_mp_set_input(mp_obj_t self_in, mp_obj_t input_in);

#ifdef __cplusplus
}
#endif