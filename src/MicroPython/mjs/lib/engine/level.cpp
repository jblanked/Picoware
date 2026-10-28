#include "level.h"
#include "../engine/pico-game-engine/engine/level.hpp"

static Level *level_instance = nullptr;

void level_create(struct mjs *mjs, mjs_val_t *level_obj)
{
    *level_obj = mjs_mk_object(mjs);

    // level_instance = new Level();
}

void level_destroy()
{
    level_instance = nullptr;
}