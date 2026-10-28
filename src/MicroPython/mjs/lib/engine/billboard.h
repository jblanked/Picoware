#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void billboard_set(struct mjs *mjs);
    //
    void billboard_create(struct mjs *mjs, mjs_val_t *billboard_obj);
    void billboard_destroy();

#ifdef __cplusplus
}
#endif