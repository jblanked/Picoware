#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void billboard_destroy(struct mjs *mjs);
    void *billboard_get_pointer(struct mjs *mjs, uint8_t arg);
    //
    void billboard_set(struct mjs *mjs);
    //
    void billboard_create(struct mjs *mjs, mjs_val_t *billboard_obj);

#ifdef __cplusplus
}
#endif