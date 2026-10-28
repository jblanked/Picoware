#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    mjs_val_t triangle3d_get_x1(struct mjs *mjs);
    mjs_val_t triangle3d_get_y1(struct mjs *mjs);
    mjs_val_t triangle3d_get_z1(struct mjs *mjs);
    mjs_val_t triangle3d_get_x2(struct mjs *mjs);
    mjs_val_t triangle3d_get_y2(struct mjs *mjs);
    mjs_val_t triangle3d_get_z2(struct mjs *mjs);
    mjs_val_t triangle3d_get_x3(struct mjs *mjs);
    mjs_val_t triangle3d_get_y3(struct mjs *mjs);
    mjs_val_t triangle3d_get_z3(struct mjs *mjs);
    mjs_val_t triangle3d_get_color(struct mjs *mjs);
    mjs_val_t triangle3d_get_wireframe(struct mjs *mjs);
    //
    void triangle3d_set(struct mjs *mjs);
    //
    void triangle3d_create(struct mjs *mjs, mjs_val_t *triangle3d_obj);
    void triangle3d_destroy();

#ifdef __cplusplus
}
#endif