#include "game.h"
#include "../engine/pico-game-engine/engine/game.hpp"

static Game *game_instance = nullptr;

void game_create(struct mjs *mjs, mjs_val_t *game_obj)
{
    *game_obj = mjs_mk_object(mjs);

    // game_instance = new Game();
}

mjs_val_t game_create_object(struct mjs *mjs)
{
    mjs_val_t game_obj = mjs_mk_object(mjs);
    game_create(mjs, &game_obj);
    return game_obj;
}

void game_destroy()
{
    game_instance = nullptr;
}