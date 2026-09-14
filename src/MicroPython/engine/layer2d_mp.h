#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "engine_mp.h"

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // Layer2D* in C++
        bool freed;
    } layer2d_mp_obj_t;

    extern const mp_obj_type_t layer2d_mp_type;

    void layer2d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t layer2d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t layer2d_mp_del(mp_obj_t self_in);
    void layer2d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
    mp_obj_t layer2d_mp_clear(mp_obj_t self_in);
    mp_obj_t layer2d_mp_circle(size_t n_args, const mp_obj_t *args);
    mp_obj_t layer2d_mp_fill_circle(size_t n_args, const mp_obj_t *args);
    mp_obj_t layer2d_mp_fill_rect(size_t n_args, const mp_obj_t *args);
    mp_obj_t layer2d_mp_get_command_count(mp_obj_t self_in);
    mp_obj_t layer2d_mp_get_pixel_bytes(mp_obj_t self_in);
    mp_obj_t layer2d_mp_image(size_t n_args, const mp_obj_t *args);
    mp_obj_t layer2d_mp_line(size_t n_args, const mp_obj_t *args);
    mp_obj_t layer2d_mp_render(size_t n_args, const mp_obj_t *args);
    mp_obj_t layer2d_mp_text(size_t n_args, const mp_obj_t *args);

#ifdef __cplusplus
}
#endif
