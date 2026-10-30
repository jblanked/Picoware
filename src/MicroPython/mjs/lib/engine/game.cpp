#include "game.h"
#include "engine.h"
#include "level.h"
#include "camera.h"
#include "../../engine/pico-game-engine/engine/game.hpp"
#include "../../engine/pico-game-engine/engine/level.hpp"
#include "../engine/memory.h"

static Game *game_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Game");
        return nullptr;
    }
    mjs_val_t game_ptr = mjs_get(mjs, this_obj, "_game", ~0);
    if (!mjs_is_foreign(game_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "game must be a Game");
        return nullptr;
    }
    return (Game *)mjs_get_ptr(mjs, game_ptr);
}

void game_destroy(struct mjs *mjs)
{
    Game *game = game_get_this(mjs);
    if (!game)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_game", ~0, mjs_mk_undefined());
    mjs_slot_release(game);
    delete game;
    game = nullptr;
}

void game_get(struct mjs *mjs)
{
    Game *game_instance = game_get_this(mjs);
    if (!game_instance)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid game instance");
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

    if (strcmp(name, "name") == 0)
    {
        mjs_return(mjs, mjs_mk_string(mjs, game_instance->name, ~0, 1));
        return;
    }
    if (strcmp(name, "size") == 0)
    {
        mjs_return(mjs, mjs_mk_vector(mjs, game_instance->size.x, game_instance->size.y, game_instance->size.z));
        return;
    }
    if (strcmp(name, "position") == 0)
    {
        mjs_return(mjs, mjs_mk_vector(mjs, game_instance->pos.x, game_instance->pos.y, game_instance->pos.z));
        return;
    }
    if (strcmp(name, "oldPosition") == 0)
    {
        mjs_return(mjs, mjs_mk_vector(mjs, game_instance->old_pos.x, game_instance->old_pos.y, game_instance->old_pos.z));
        return;
    }
    if (strcmp(name, "input") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)game_instance->input));
        return;
    }
    if (strcmp(name, "isActive") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, game_instance->is_active));
        return;
    }
    if (strcmp(name, "camera") == 0)
    {
        mjs_return(mjs, camera_get_object(mjs, game_instance->camera));
        return;
    }
    if (strcmp(name, "currentLevel") == 0)
    {
        mjs_return(mjs, level_get_object(mjs, game_instance->current_level));
        return;
    }
    mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "unknown property");
    mjs_return(mjs, mjs_mk_undefined());
}

void *game_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t game_arg = mjs_arg(mjs, arg);
    mjs_val_t game_ptr = mjs_is_object(game_arg)
                             ? mjs_get(mjs, game_arg, "_game", ~0)
                             : game_arg;
    if (!mjs_is_foreign(game_ptr))
    {
        return nullptr;
    }

    return (Game *)mjs_get_ptr(mjs, game_ptr);
}

mjs_val_t game_get_object(struct mjs *mjs, void *game_instance_ptr)
{
    Game *game_instance = static_cast<Game *>(game_instance_ptr);
    if (!game_instance)
        return mjs_mk_undefined();

    mjs_val_t game_obj = mjs_mk_object(mjs);
    mjs_set(mjs, game_obj, "_game", ~0, mjs_mk_foreign(mjs, game_instance));
    mjs_set(mjs, game_obj, "destroy", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_destroy));
    mjs_set(mjs, game_obj, "get", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_get));
    mjs_set(mjs, game_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_set));

    mjs_set(mjs, game_obj, "levelAdd", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_add));
    mjs_set(mjs, game_obj, "levelRemove", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_remove));
    mjs_set(mjs, game_obj, "levelSwitch", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_switch));
    return game_obj;
}

void game_level_add(struct mjs *mjs)
{
    Game *game_instance = game_get_this(mjs);
    if (!game_instance)
        return;

    Level *level = static_cast<Level *>(level_get_pointer(mjs, 0));
    if (!level)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "Invalid argument, expected Level");
        return;
    }

    game_instance->level_add(level);
    mjs_return(mjs, mjs_mk_boolean(mjs, true));
}

void game_level_remove(struct mjs *mjs)
{
    Game *game_instance = game_get_this(mjs);
    if (!game_instance)
        return;

    Level *level = static_cast<Level *>(level_get_pointer(mjs, 0));
    if (!level)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "Invalid argument, expected Level");
        return;
    }

    game_instance->level_remove(level);
    mjs_return(mjs, mjs_mk_boolean(mjs, true));
}

void game_level_switch(struct mjs *mjs)
{
    Game *game_instance = game_get_this(mjs);
    if (!game_instance)
        return;

    mjs_val_t arg = mjs_arg(mjs, 0);
    if (mjs_is_number(arg))
    {
        game_instance->level_switch(mjs_get_int(mjs, arg));
    }
    else if (mjs_is_string(arg))
    {
        size_t len = 0;
        const char *name = mjs_get_string(mjs, &arg, &len);
        if (name)
            game_instance->level_switch(name);
    }
}

void game_set(struct mjs *mjs)
{
    Game *game_instance = game_get_this(mjs);
    if (!game_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "No game instance");
        return;
    }

    mjs_val_t key_val = mjs_arg(mjs, 0);
    if (!mjs_is_string(key_val))
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Property name must be a string");
        return;
    }
    size_t len = 0;
    const char *key = mjs_get_string(mjs, &key_val, &len);

    if (strcmp(key, "name") == 0)
    {
        size_t value_len = 0;
        mjs_val_t value_val = mjs_arg(mjs, 1);
        const char *value = mjs_is_string(value_val)
                                ? mjs_get_string(mjs, &value_val, &value_len)
                                : NULL;
        if (value)
        {
            char *buffer = (char *)m_malloc(value_len + 1);
            if (!buffer)
            {
                mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to allocate name");
                return;
            }
            memcpy(buffer, value, value_len);
            buffer[value_len] = '\0';
            m_free(const_cast<char *>(game_instance->name));
            game_instance->name = buffer;
        }
    }
    else if (strcmp(key, "size") == 0 || strcmp(key, "position") == 0 || strcmp(key, "oldPosition") == 0)
    {
        float x, y, z;
        if (mjs_get_vector(mjs, 1, &x, &y, &z))
        {
            if (strcmp(key, "size") == 0)
                game_instance->size = Vector(x, y, z, false);
            else if (strcmp(key, "position") == 0)
                game_instance->pos = Vector(x, y, z, false);
            else
                game_instance->old_pos = Vector(x, y, z, false);
        }
    }
    else if (strcmp(key, "isActive") == 0)
    {
        game_instance->is_active = mjs_get_boolean(mjs, 1);
    }
    else if (strcmp(key, "fgColor") == 0)
    {
        game_instance->fg_color = mjs_get_color(mjs, mjs_arg(mjs, 1));
    }
    else if (strcmp(key, "bgColor") == 0)
    {
        game_instance->bg_color = mjs_get_color(mjs, mjs_arg(mjs, 1));
    }
}

void game_create(struct mjs *mjs, mjs_val_t *game_obj)
{
    mjs_val_t name_val = mjs_arg(mjs, 1);
    char *name_buf = (char *)m_malloc(256);
    if (!name_buf)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to allocate name");
        return;
    }
    {
        size_t len = 0;
        const char *name = mjs_is_string(name_val) ? mjs_get_string(mjs, &name_val, &len)
                                                   : "";
        size_t copy_len = (len < 255) ? len : 255;
        memcpy(name_buf, name, copy_len);
        name_buf[copy_len] = '\0';
    }

    Vector size(640, 480, 0, false);
    mjs_val_t size_val = mjs_arg(mjs, 2);
    if (mjs_is_object(size_val))
    {
        float x, y, z;
        if (mjs_get_vector(mjs, 2, &x, &y, &z))
            size = Vector(x, y, z, false);
    }

    uint16_t fg = mjs_get_color(mjs, mjs_arg(mjs, 3));
    uint16_t bg = mjs_get_color(mjs, mjs_arg(mjs, 4));

    Draw *game_draw_instance = new Draw();
    if (!game_draw_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to create draw");
        m_free(name_buf);
        return;
    }

    Game *game_instance = new Game(name_buf, size, game_draw_instance,
                                   fg, bg, nullptr, {}, {}, {});
    if (!game_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Game creation failed");
        m_free(name_buf);
        return;
    }
    mjs_slot_set(game_instance);

    *game_obj = game_get_object(mjs, game_instance);
}