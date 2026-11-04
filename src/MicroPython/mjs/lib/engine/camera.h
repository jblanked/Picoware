#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void camera_destroy(struct mjs *mjs);
    void camera_get(struct mjs *mjs);
    mjs_val_t camera_get_object(struct mjs *mjs, void *camera_instance_ptr);
    void *camera_get_pointer(struct mjs *mjs, uint8_t arg);
    //
    void camera_set(struct mjs *mjs);
    //
    void camera_create(struct mjs *mjs, mjs_val_t *camera_obj);

#ifdef __cplusplus
}
#endif