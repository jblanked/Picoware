#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    mjs_val_t camera_get_direction(struct mjs *mjs);
    mjs_val_t camera_get_distance(struct mjs *mjs);
    mjs_val_t camera_get_height(struct mjs *mjs);
    mjs_val_t camera_get_perspective(struct mjs *mjs);
    mjs_val_t camera_get_plane(struct mjs *mjs);
    mjs_val_t camera_get_position(struct mjs *mjs);
    //
    void camera_set(struct mjs *mjs);
    //
    void camera_create(struct mjs *mjs, mjs_val_t *camera_obj);
    mjs_val_t camera_get_context(struct mjs *mjs, void *cameraContext);
    void camera_destroy();

#ifdef __cplusplus
}
#endif