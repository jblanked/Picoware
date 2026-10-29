#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void game_destroy(struct mjs *mjs);
    void game_get(struct mjs *mjs);
    mjs_val_t game_get_object(struct mjs *mjs, void *game_instance_ptr);
    void *game_get_pointer(struct mjs *mjs, uint8_t arg);
    //
    void game_set(struct mjs *mjs);
    void game_level_add(struct mjs *mjs);
    void game_level_remove(struct mjs *mjs);
    void game_level_switch(struct mjs *mjs);
    //
    void game_create(struct mjs *mjs, mjs_val_t *game_obj);

#ifdef __cplusplus
}
#endif