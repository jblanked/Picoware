#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void *level_get_instance();
    //
    mjs_val_t level_get_entity_count(struct mjs *mjs);
    mjs_val_t level_get_light_direction(struct mjs *mjs);
    mjs_val_t level_get_name(struct mjs *mjs);
    mjs_val_t level_get_size(struct mjs *mjs);
    mjs_val_t level_get_shadow_color(struct mjs *mjs);
    mjs_val_t level_is_clear_allowed(struct mjs *mjs);
    //
    mjs_val_t level_get_entity(struct mjs *mjs);
    mjs_val_t level_has_collided(struct mjs *mjs);
    //
    void level_clear(struct mjs *mjs);
    void level_entity_add(struct mjs *mjs);
    void level_entity_remove(struct mjs *mjs);
    //
    void level_set(struct mjs *mjs);
    //
    void level_create(struct mjs *mjs, mjs_val_t *level_obj);
    void level_destroy();

#ifdef __cplusplus
}
#endif