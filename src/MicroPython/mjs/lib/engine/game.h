#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void *game_get_instance();
    mjs_val_t game_get_object(struct mjs *mjs);
    //
    mjs_val_t game_get_camera(struct mjs *mjs);
    mjs_val_t game_get_current_level(struct mjs *mjs);
    mjs_val_t game_get_input(struct mjs *mjs);
    mjs_val_t game_get_is_active(struct mjs *mjs);
    mjs_val_t game_get_name(struct mjs *mjs);
    mjs_val_t game_get_position(struct mjs *mjs);
    mjs_val_t game_get_old_position(struct mjs *mjs);
    mjs_val_t game_get_size(struct mjs *mjs);
    //
    void game_set(struct mjs *mjs);
    void game_level_add(struct mjs *mjs);
    void game_level_remove(struct mjs *mjs);
    void game_level_switch(struct mjs *mjs);
    //
    void game_create(struct mjs *mjs, mjs_val_t *game_obj);
    mjs_val_t game_create_object(struct mjs *mjs);
    void game_destroy();

#ifdef __cplusplus
}
#endif