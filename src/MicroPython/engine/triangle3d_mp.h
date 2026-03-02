#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

typedef struct
{
    mp_obj_base_t base;
    float x1, y1, z1;
    float x2, y2, z2;
    float x3, y3, z3;
    bool visible;
    float distance;
} triangle3d_mp_obj_t;

extern const mp_obj_type_t triangle3d_mp_type;

void triangle3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t triangle3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t triangle3d_mp_del(mp_obj_t self_in);
void triangle3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
mp_obj_t triangle3d_mp_center(mp_obj_t self_in);
mp_obj_t triangle3d_mp_vertices(mp_obj_t self_in);
mp_obj_t triangle3d_mp_is_facing_camera(mp_obj_t self_in, mp_obj_t camera_pos_vector);