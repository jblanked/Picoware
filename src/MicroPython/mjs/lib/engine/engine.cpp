#include "engine.h"
#include "../engine/pico-game-engine/engine/engine.hpp"

static GameEngine *engine_instance = nullptr;

mjs_val_t engine_get_game(struct mjs *mjs)
{
    if (!engine_instance)
        return mjs_mk_undefined();
    Game *game = engine_instance->getGame();
    if (game == nullptr)
        return mjs_mk_undefined();
    mjs_val_t game_obj = mjs_mk_object(mjs);
    return game_obj;
}

void engine_create(struct mjs *mjs, mjs_val_t *engine_obj)
{
    *engine_obj = mjs_mk_object(mjs);

    // engine_instance = new GameEngine();
}

void engine_destroy()
{
    engine_instance = nullptr;
}