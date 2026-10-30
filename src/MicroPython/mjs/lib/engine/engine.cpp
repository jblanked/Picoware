#include "engine.h"
#include "../engine/pico-game-engine/engine/engine.hpp"
#include "../engine/memory.h"
#include "game.h"

static float engine_fps = 30.0f;
static bool engine_clamp = false;

static GameEngine *engine_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Engine");
        return nullptr;
    }
    mjs_val_t engine_ptr = mjs_get(mjs, this_obj, "_engine", ~0);
    if (!mjs_is_foreign(engine_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "engine must be a Engine");
        return nullptr;
    }
    return (GameEngine *)mjs_get_ptr(mjs, engine_ptr);
}

void engine_destroy(struct mjs *mjs)
{
    GameEngine *engine = engine_get_this(mjs);
    if (!engine)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_engine", ~0, mjs_mk_undefined());
    mjs_slot_release(engine);
    delete engine;
    engine_fps = 30.0f;
    engine_clamp = false;
}

void *engine_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t engine_arg = mjs_arg(mjs, arg);
    mjs_val_t engine_ptr = mjs_is_object(engine_arg)
                               ? mjs_get(mjs, engine_arg, "_engine", ~0)
                               : engine_arg;
    if (!mjs_is_foreign(engine_ptr))
    {
        return nullptr;
    }
    return (GameEngine *)mjs_get_ptr(mjs, engine_ptr);
}

void engine_get(struct mjs *mjs)
{
    GameEngine *engine_instance = engine_get_this(mjs);
    if (!engine_instance)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid engine instance");
        mjs_return(mjs, mjs_mk_undefined());
        return;
    }
    mjs_val_t name_val = mjs_arg(mjs, 0);
    if (!mjs_is_string(name_val))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "name must be a string");
        mjs_return(mjs, mjs_mk_undefined());
        return;
    }
    size_t len;
    const char *name = mjs_get_string(mjs, &name_val, &len);

    if (strcmp(name, "game") == 0)
    {
        mjs_return(mjs, game_get_object(mjs, engine_instance ? engine_instance->getGame() : nullptr));
        return;
    }
    if (strcmp(name, "clamp") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, engine_clamp));
        return;
    }
    if (strcmp(name, "input") == 0)
    {
        Game *game = engine_instance ? engine_instance->getGame() : nullptr;
        if (!game)
            mjs_return(mjs, mjs_mk_undefined());
        else
            mjs_return(mjs, mjs_mk_number(mjs, (double)game->input));
        return;
    }
    mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "unknown property: %s", name);
    mjs_return(mjs, mjs_mk_undefined());
}

void engine_set(struct mjs *mjs)
{
    GameEngine *engine_instance = engine_get_this(mjs);
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
    GameEngine *engine_instance = engine_get_this(mjs);
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
    engine_stop(mjs);
}

void engine_run_async(struct mjs *mjs)
{
    GameEngine *engine_instance = engine_get_this(mjs);
    bool should_delay = false;
    mjs_val_t arg = mjs_arg(mjs, 0);
    if (!mjs_is_undefined(arg))
        should_delay = mjs_get_bool(mjs, arg);
    if (engine_instance && engine_instance->getGame())
        engine_instance->runAsync(should_delay);
}

void engine_stop(struct mjs *mjs)
{
    GameEngine *engine_instance = engine_get_this(mjs);
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
    GameEngine *engine_instance = engine_get_this(mjs);
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
    GameEngine *engine_instance = engine_get_this(mjs);
    if (engine_instance)
        engine_instance->setClamp(mjs_get_boolean(mjs, 0));
}

void engine_create(struct mjs *mjs, mjs_val_t *engine_obj)
{
    *engine_obj = mjs_mk_object(mjs);

    Game *game = static_cast<Game *>(game_get_pointer(mjs, 1));
    if (!game)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Create a Game before its Engine");
        *engine_obj = mjs_mk_undefined();
        return;
    }

    float fps = 30.0f;
    mjs_val_t fps_val = mjs_arg(mjs, 2);
    if (mjs_is_number(fps_val))
        fps = (float)mjs_get_double(mjs, fps_val);
    if (fps <= 0.0f)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "FPS must be greater than zero");
        *engine_obj = mjs_mk_undefined();
        return;
    }

    bool clamp = mjs_get_boolean(mjs, 3);
    GameEngine *engine_instance = new GameEngine(game, fps, clamp);
    if (!engine_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Engine creation failed");
        *engine_obj = mjs_mk_undefined();
        return;
    }
    mjs_slot_set(engine_instance);
    engine_fps = fps;
    engine_clamp = clamp;

    mjs_set(mjs, *engine_obj, "_engine", ~0, mjs_mk_foreign(mjs, engine_instance));
    mjs_set(mjs, *engine_obj, "destroy", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_destroy));
    mjs_set(mjs, *engine_obj, "get", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_get));
    mjs_set(mjs, *engine_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_set));

    mjs_set(mjs, *engine_obj, "run", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_run));
    mjs_set(mjs, *engine_obj, "runAsync", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_run_async));
    mjs_set(mjs, *engine_obj, "stop", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_stop));
    mjs_set(mjs, *engine_obj, "setClamp", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_set_clamp));
    mjs_set(mjs, *engine_obj, "updateGameInput", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)engine_update_game_input));
}
