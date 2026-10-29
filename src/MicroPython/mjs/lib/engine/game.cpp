#include "game.h"
#include "engine.h"
#include "level.h"
#include "../../engine/pico-game-engine/engine/game.hpp"
#include "../../engine/pico-game-engine/engine/level.hpp"
#include "../engine/memory.h"

static Game *game_instance = nullptr;
static Draw *game_draw_instance = nullptr;

mjs_val_t game_get_object(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();

    mjs_val_t game_obj = mjs_mk_object(mjs);
    mjs_set(mjs, game_obj, "_game", ~0, mjs_mk_foreign(mjs, game_instance));
    mjs_set_getter(mjs, game_obj, "name", ~0, game_get_name);
    mjs_set_getter(mjs, game_obj, "size", ~0, game_get_size);
    mjs_set_getter(mjs, game_obj, "position", ~0, game_get_position);
    mjs_set_getter(mjs, game_obj, "oldPosition", ~0, game_get_old_position);
    mjs_set_getter(mjs, game_obj, "input", ~0, game_get_input);
    mjs_set_getter(mjs, game_obj, "isActive", ~0, game_get_is_active);
    mjs_set_getter(mjs, game_obj, "camera", ~0, game_get_camera);
    mjs_set_getter(mjs, game_obj, "currentLevel", ~0, game_get_current_level);
    mjs_set(mjs, game_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_set));
    mjs_set(mjs, game_obj, "levelAdd", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_add));
    mjs_set(mjs, game_obj, "levelRemove", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_remove));
    mjs_set(mjs, game_obj, "levelSwitch", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_switch));
    return game_obj;
}

void *game_get_instance()
{
    return game_instance;
}

mjs_val_t game_get_name(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    if (!game_instance->name || !*game_instance->name)
        return mjs_mk_string(mjs, "game", ~0, 1);
    return mjs_mk_string(mjs, game_instance->name, ~0, 1);
}

mjs_val_t game_get_size(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs, game_instance->size.x, game_instance->size.y, game_instance->size.z);
}

mjs_val_t game_get_position(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs, game_instance->pos.x, game_instance->pos.y, game_instance->pos.z);
}

mjs_val_t game_get_old_position(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs, game_instance->old_pos.x, game_instance->old_pos.y, game_instance->old_pos.z);
}

mjs_val_t game_get_input(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)game_instance->input);
}

mjs_val_t game_get_is_active(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, (int)game_instance->is_active);
}

mjs_val_t game_get_camera(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    Camera *cam = game_instance->getCamera();
    if (!cam)
        return mjs_mk_undefined();
    return mjs_mk_foreign(mjs, (void *)cam);
}

mjs_val_t game_get_current_level(struct mjs *mjs)
{
    if (!game_instance)
        return mjs_mk_undefined();
    Level *level = game_instance->current_level;
    if (!level)
        return mjs_mk_undefined();
    return mjs_mk_foreign(mjs, (void *)level);
}

/* Level ownership lives with the level module; the game array holds
   non-owning references only. */
static Level *level_from_foreign(struct mjs *mjs, mjs_val_t arg)
{
    mjs_val_t ptr = mjs_is_object(arg)
                        ? mjs_get(mjs, arg, "_level", ~0)
                        : arg;
    if (!mjs_is_foreign(ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "level must be a Level");
        return nullptr;
    }
    return (Level *)mjs_get_ptr(mjs, ptr);
}

void game_level_add(struct mjs *mjs)
{
    if (!game_instance)
        return;

    Level *level = level_from_foreign(mjs, mjs_arg(mjs, 0));
    if (!level)
        return;

    game_instance->level_add(level);

    if (!game_instance->current_level)
        game_instance->current_level = level;
}

void game_level_remove(struct mjs *mjs)
{
    if (!game_instance)
        return;

    Level *level = level_from_foreign(mjs, mjs_arg(mjs, 0));
    if (!level)
        return;

    for (int i = 0; i < MAX_LEVELS; i++)
    {
        if (game_instance->levels[i] == level)
        {
            game_instance->levels[i] = nullptr;
            break;
        }
    }
    if (game_instance->current_level == level)
        game_instance->current_level = nullptr;
}

void game_level_switch(struct mjs *mjs)
{
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
    // Replace any previous game.
    engine_destroy();
    if (game_instance)
    {
        for (int i = 0; i < MAX_LEVELS; i++)
            game_instance->levels[i] = nullptr;
        game_instance->current_level = nullptr;
        delete game_instance;
        game_instance = nullptr;
    }
    if (game_draw_instance)
    {
        delete game_draw_instance;
        game_draw_instance = nullptr;
    }

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

    game_draw_instance = new Draw();
    if (!game_draw_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to create draw");
        m_free(name_buf);
        return;
    }

    game_instance = new Game(name_buf, size, game_draw_instance,
                             fg, bg, nullptr, {}, {}, {});
    if (!game_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Game creation failed");
        m_free(name_buf);
        return;
    }

    *game_obj = mjs_mk_object(mjs);
    mjs_set(mjs, *game_obj, "_game", ~0, mjs_mk_foreign(mjs, game_instance));
    mjs_set_getter(mjs, *game_obj, "name", ~0, game_get_name);
    mjs_set_getter(mjs, *game_obj, "size", ~0, game_get_size);
    mjs_set_getter(mjs, *game_obj, "position", ~0, game_get_position);
    mjs_set_getter(mjs, *game_obj, "oldPosition", ~0, game_get_old_position);
    mjs_set_getter(mjs, *game_obj, "input", ~0, game_get_input);
    mjs_set_getter(mjs, *game_obj, "isActive", ~0, game_get_is_active);
    mjs_set_getter(mjs, *game_obj, "camera", ~0, game_get_camera);
    mjs_set_getter(mjs, *game_obj, "currentLevel", ~0, game_get_current_level);
    mjs_set(mjs, *game_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_set));
    mjs_set(mjs, *game_obj, "levelAdd", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_add));
    mjs_set(mjs, *game_obj, "levelRemove", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_remove));
    mjs_set(mjs, *game_obj, "levelSwitch", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)game_level_switch));

    // Back-fit a level that was created before this game. Such a level has a
    // null gameRef, so entities added through it would be a no-op. Pointing
    // it at the new game fixes `level.entityAdd`.
    {
        Level *level = static_cast<Level *>(level_get_instance());
        if (level)
        {
            level->setGame(game_instance);
            game_instance->level_add(level);
            game_instance->current_level = level;
            game_instance->is_active = true;
        }
    }
}

mjs_val_t game_create_object(struct mjs *mjs)
{
    mjs_val_t game_obj = mjs_mk_object(mjs);
    game_create(mjs, &game_obj);
    return game_obj;
}

void game_destroy()
{
    engine_destroy();
    if (game_instance)
    {
        // Level ownership lives with the level module; null the non-owning
        // references so the game destructor does not delete them.
        for (int i = 0; i < MAX_LEVELS; i++)
            game_instance->levels[i] = nullptr;
        game_instance->current_level = nullptr;
        delete game_instance;
        game_instance = nullptr;
    }
    if (game_draw_instance)
    {
        delete game_draw_instance;
        game_draw_instance = nullptr;
    }
}