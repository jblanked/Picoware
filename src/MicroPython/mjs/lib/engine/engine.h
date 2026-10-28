#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    mjs_val_t engine_get_game(struct mjs *mjs);
    //
    void engine_set(struct mjs *mjs);
    void engine_run(struct mjs *mjs);
    void engine_run_async(struct mjs *mjs);
    void engine_stop(struct mjs *mjs);
    //
    void engine_create(struct mjs *mjs, mjs_val_t *engine_obj);
    void engine_destroy();

#ifdef __cplusplus
}
#endif