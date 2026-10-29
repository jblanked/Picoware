#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void image_destroy(struct mjs *mjs);
    void image_get(struct mjs *mjs);
    void *image_get_pointer(struct mjs *mjs, uint8_t arg);
    void image_create(struct mjs *mjs, mjs_val_t *image_obj);

#ifdef __cplusplus
}
#endif