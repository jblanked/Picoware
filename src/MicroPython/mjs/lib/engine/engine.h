#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void engine_destroy(struct mjs *mjs);
    void engine_get(struct mjs *mjs);
    void *engine_get_pointer(struct mjs *mjs, uint8_t arg);
    //
    void engine_set(struct mjs *mjs);
    void engine_run(struct mjs *mjs);
    void engine_run_async(struct mjs *mjs);
    void engine_stop(struct mjs *mjs);
    void engine_update_game_input(struct mjs *mjs);
    void engine_set_clamp(struct mjs *mjs);
    //
    void engine_create(struct mjs *mjs, mjs_val_t *engine_obj);

#ifdef __cplusplus
}
#endif