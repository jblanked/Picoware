#include "engine.h"
#include "../engine/pico-game-engine/engine/engine.hpp"
#include "../engine/memory.h"
#include "game.h"

static GameEngine *engine_instance = nullptr;
static float engine_fps = 30.0f;
static bool engine_clamp = false;

mjs_val_t engine_get_game(struct mjs *mjs)
{
    if (!engine_instance)
        return mjs_mk_undefined();
    return game_get_object(mjs);
}

mjs_val_t engine_get_clamp(struct mjs *mjs)
{
    if (!engine_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, engine_clamp);
}

mjs_val_t engine_get_input(struct mjs *mjs)
{
    Game *game = engine_instance ? engine_instance->getGame() : nullptr;
    if (!game)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)game->input);
}

void engine_set(struct mjs *mjs)
{
    if (!engine_instance)
        return;

    mjs_val_t key_val = mjs_arg(mjs, 0);
    if (!mjs_is_string(key_val))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "Property name must be a string");
        return;
    }

    size_t key_len = 0;
    const char *key = mjs_get_string(mjs, &key_val, &key_len);
    (void)key_len;
    mjs_val_t value = mjs_arg(mjs, 1);
    if (strcmp(key, "clamp") == 0)
    {
        engine_clamp = mjs_get_bool(mjs, value);
        engine_instance->setClamp(engine_clamp);
    }
    else if (strcmp(key, "input") == 0)
    {
        if (!mjs_is_number(value))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "Input must be a number");
            return;
        }
        engine_instance->updateGameInput((uint8_t)mjs_get_int(mjs, value));
    }
}

void engine_run(struct mjs *mjs)
{
    (void)mjs;
    Game *game = engine_instance ? engine_instance->getGame() : nullptr;
    if (!game)
        return;
    if (!game->is_active)
        game->start();
    while (game->is_active)
    {
        game->update();
        game->render(engine_clamp);
        ENGINE_DELAY_MS(1000 / engine_fps);
    }
    engine_stop(nullptr);
}

void engine_run_async(struct mjs *mjs)
{
    bool should_delay = false;
    mjs_val_t arg = mjs_arg(mjs, 0);
    if (!mjs_is_undefined(arg))
        should_delay = mjs_get_bool(mjs, arg);
    if (engine_instance && engine_instance->getGame())
        engine_instance->runAsync(should_delay);
}

void engine_stop(struct mjs *mjs)
{
    (void)mjs;
    Game *game = engine_instance ? engine_instance->getGame() : nullptr;
    if (!game)
        return;
    if (game->is_active)
    {
        if (game->_stop)
            game->_stop();
        if (game->current_level)
            game->current_level->stop();
        game->is_active = false;
    }
    if (game->draw)
        game->draw->fillScreen(game->bg_color);
}

void engine_update_game_input(struct mjs *mjs)
{
    mjs_val_t input = mjs_arg(mjs, 0);
    if (!engine_instance || !mjs_is_number(input))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "Input must be a number");
        return;
    }
    engine_instance->updateGameInput((uint8_t)mjs_get_int(mjs, input));
}

void engine_set_clamp(struct mjs *mjs)
{
    if (engine_instance)
        engine_instance->setClamp(mjs_get_boolean(mjs, 0));
}

void engine_create(struct mjs *mjs, mjs_val_t *engine_obj)
{
    *engine_obj = mjs_mk_object(mjs);

    engine_destroy();
    Game *game = static_cast<Game *>(game_get_instance());
    if (!game)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Create a Game before its Engine");
        *engine_obj = mjs_mk_undefined();
        return;
    }

    float fps = 30.0f;
    mjs_val_t fps_val = mjs_arg(mjs, 1);
    if (mjs_is_number(fps_val))
        fps = (float)mjs_get_double(mjs, fps_val);
    if (fps <= 0.0f)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "FPS must be greater than zero");
        *engine_obj = mjs_mk_undefined();
        return;
    }

    bool clamp = mjs_get_boolean(mjs, 2);
    engine_instance = new GameEngine(game, fps, clamp);
    if (!engine_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Engine creation failed");
        *engine_obj = mjs_mk_undefined();
        return;
    }
    engine_fps = fps;
    engine_clamp = clamp;

    mjs_set(mjs, *engine_obj, "_engine", ~0, mjs_mk_foreign(mjs, engine_instance));
    mjs_set_getter(mjs, *engine_obj, "game", ~0, engine_get_game);
    mjs_set_getter(mjs, *engine_obj, "clamp", ~0, engine_get_clamp);
    mjs_set_getter(mjs, *engine_obj, "input", ~0, engine_get_input);
    mjs_set(mjs, *engine_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_set));
    mjs_set(mjs, *engine_obj, "run", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_run));
    mjs_set(mjs, *engine_obj, "runAsync", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_run_async));
    mjs_set(mjs, *engine_obj, "stop", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_stop));
    mjs_set(mjs, *engine_obj, "setClamp", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_set_clamp));
    mjs_set(mjs, *engine_obj, "updateGameInput", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_update_game_input));
}

void engine_destroy()
{
    if (engine_instance)
        delete engine_instance;
    engine_instance = nullptr;
    engine_fps = 30.0f;
    engine_clamp = false;
}
