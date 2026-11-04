#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void sprite3d_destroy(struct mjs *mjs);
    mjs_val_t sprite3d_get_object(struct mjs *mjs, void *sprite3d_instance_ptr);
    void *sprite3d_get_pointer(struct mjs *mjs, uint8_t arg);
    //
    void sprite3d_get(struct mjs *mjs);
    //
    void sprite3d_add_triangle(struct mjs *mjs);
    void sprite3d_bake_transform(struct mjs *mjs);
    void sprite3d_clear_triangles(struct mjs *mjs);
    void sprite3d_create_humanoid(struct mjs *mjs);
    void sprite3d_create_tree(struct mjs *mjs);
    void sprite3d_create_house(struct mjs *mjs);
    void sprite3d_create_pillar(struct mjs *mjs);
    void sprite3d_create_wall(struct mjs *mjs);
    void sprite3d_create_cube(struct mjs *mjs);
    void sprite3d_create_cylinder(struct mjs *mjs);
    void sprite3d_create_sphere(struct mjs *mjs);
    void sprite3d_create_triangular_prism(struct mjs *mjs);
    void sprite3d_from_path(struct mjs *mjs);
    void sprite3d_reserve_triangles(struct mjs *mjs);
    void sprite3d_to_path(struct mjs *mjs);
    void sprite3d_update_triangle(struct mjs *mjs);
    //
    void sprite3d_set(struct mjs *mjs);
    //
    void sprite3d_create(struct mjs *mjs, mjs_val_t *sprite3d_obj);

#ifdef __cplusplus
}
#endif