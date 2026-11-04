#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void level_destroy(struct mjs *mjs);
    void level_get(struct mjs *mjs);
    mjs_val_t level_get_object(struct mjs *mjs, void *level_instance_ptr);
    void *level_get_pointer(struct mjs *mjs, uint8_t arg);
    //
    void level_has_collided(struct mjs *mjs);
    //
    void level_clear(struct mjs *mjs);
    void level_entity_add(struct mjs *mjs);
    void level_entity_remove(struct mjs *mjs);
    //
    void level_set(struct mjs *mjs);
    //
    void level_create(struct mjs *mjs, mjs_val_t *level_obj);

#ifdef __cplusplus
}
#endif