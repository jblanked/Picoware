#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    void entity_destroy(struct mjs *mjs);
    void entity_get(struct mjs *mjs);
    mjs_val_t entity_get_object(struct mjs *mjs, void *entity_instance_ptr);
    void *entity_get_pointer(struct mjs *mjs, uint8_t arg);

    void entity_set(struct mjs *mjs);
    void entity_update_position(struct mjs *mjs);

    void entity_create(struct mjs *mjs, mjs_val_t *entity_obj);

#ifdef __cplusplus
}
#endif