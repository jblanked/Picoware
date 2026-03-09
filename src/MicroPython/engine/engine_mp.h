#pragma once

#if defined(PICOCALC)
#include "../../vector/vector_mp.h"
#else
#include "../../../vector/vector_mp.h"
#endif

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
        void *context; // GameEngine* in C++
        bool freed;
    } engine_mp_obj_t;

    extern const mp_obj_type_t engine_mp_type;

    void engine_mp_del_reference(mp_obj_t mp_obj);
    void engine_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t engine_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t engine_mp_del(mp_obj_t self_in);
    void engine_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t engine_mp_run(mp_obj_t self_in);
    mp_obj_t engine_mp_run_async(size_t n_args, const mp_obj_t *args);
    mp_obj_t engine_mp_stop(mp_obj_t self_in);
    mp_obj_t engine_mp_update_game_input(mp_obj_t self_in, mp_obj_t input);
    mp_obj_t engine_mp_get_game(mp_obj_t self_in);

#ifdef __cplusplus
}
#endif