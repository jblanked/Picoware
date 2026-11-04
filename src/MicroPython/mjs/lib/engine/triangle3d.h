#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void triangle3d_destroy(struct mjs *mjs);
    void triangle3d_get(struct mjs *mjs);
    mjs_val_t triangle3d_get_object(struct mjs *mjs, void *triangle3d_instance_ptr);
    void triangle3d_set(struct mjs *mjs);
    void triangle3d_create(struct mjs *mjs, mjs_val_t *triangle3d_obj);

#ifdef __cplusplus
}
#endif