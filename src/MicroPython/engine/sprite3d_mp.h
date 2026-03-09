#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "triangle3d_mp.h"
#include "engine_mp.h"

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // Sprite3D* in C++
        bool freed;
    } sprite3d_mp_obj_t;

    extern const mp_obj_type_t sprite3d_mp_type;

    mp_obj_t sprite3d_mp_init(void);
    void sprite3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t sprite3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_del(mp_obj_t self_in);
    void sprite3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t sprite3d_mp_add_triangle(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_clear_triangles(mp_obj_t self_in);
    mp_obj_t sprite3d_mp_create_humanoid(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_tree(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_house(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_pillar(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_wall(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_cube(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_cylinder(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_sphere(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_create_triangular_prism(size_t n_args, const mp_obj_t *args);

    mp_obj_t sprite3d_mp_initialize_as_house(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_initialize_as_humanoid(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_initialize_as_pillar(size_t n_args, const mp_obj_t *args);
    mp_obj_t sprite3d_mp_initialize_as_tree(size_t n_args, const mp_obj_t *args);

#ifdef __cplusplus
}
#endif