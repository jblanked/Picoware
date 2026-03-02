#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

typedef struct
{
    mp_obj_base_t base;
    float x;
    float y;
    float z;
    bool integer;
} vector_mp_obj_t;

extern const mp_obj_type_t vector_mp_type;

mp_obj_t vector_mp_init(float x, float y, float z, bool integer);
void vector_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t vector_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t vector_mp_del(mp_obj_t self_in);
void vector_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
mp_obj_t vector_mp_rotate_y(mp_obj_t self_in, mp_obj_t angle_in);
mp_obj_t vector_mp_translate(size_t n_args, const mp_obj_t *args);
mp_obj_t vector_mp_scale(size_t n_args, const mp_obj_t *args);