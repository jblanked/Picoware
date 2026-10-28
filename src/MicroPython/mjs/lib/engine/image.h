#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    mjs_val_t image_get_data(struct mjs *mjs);
    mjs_val_t image_get_data_size(struct mjs *mjs);
    mjs_val_t image_get_mask(struct mjs *mjs);
    mjs_val_t image_get_mask_size(struct mjs *mjs);
    mjs_val_t image_get_size(struct mjs *mjs);
    mjs_val_t image_has_mask(struct mjs *mjs);

    void image_create(struct mjs *mjs, mjs_val_t *image_obj);
    void image_destroy();

#ifdef __cplusplus
}
#endif