#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

typedef enum
{
    SPRITE_3D_NONE = 0,
    SPRITE_3D_HUMANOID = 1,
    SPRITE_3D_TREE = 2,
    SPRITE_3D_HOUSE = 3,
    SPRITE_3D_PILLAR = 4,
    SPRITE_3D_CUSTOM = 5
} Sprite3DType;

typedef struct
{
    mp_obj_base_t base;
    mp_obj_t triangles;
    size_t triangle_count;
    mp_obj_t pos;
    float rotation_y;
    float scale_factor;
    Sprite3DType type;
    bool active;
    uint16_t color;
    bool freed;
} sprite3d_mp_obj_t;

extern const mp_obj_type_t sprite3d_mp_type;

mp_obj_t sprite3d_mp_init(void);
void sprite3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t sprite3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t sprite3d_mp_del(mp_obj_t self_in);
void sprite3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
mp_obj_t sprite3d_mp_add_triangle(mp_obj_t self_in, mp_obj_t triangle_in);
mp_obj_t sprite3d_mp_clear_triangles(mp_obj_t self_in);