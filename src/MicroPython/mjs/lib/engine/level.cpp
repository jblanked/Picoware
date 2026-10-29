#include "level.h"
#include "game.h"
#include "../../engine/pico-game-engine/engine/level.hpp"
#include "../../engine/pico-game-engine/engine/game.hpp"
#include "../engine/memory.h"

static Level *level_instance = nullptr;
static bool level_name_owned = false;

void *level_get_instance()
{
    return level_instance;
}

mjs_val_t level_get_entity_count(struct mjs *mjs)
{
    if (!level_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)level_instance->getEntityCount());
}

mjs_val_t level_get_light_direction(struct mjs *mjs)
{
    if (!level_instance)
        return mjs_mk_undefined();
    const Vector light_direction = level_instance->getLightDirection();
    return mjs_mk_vector(mjs, light_direction.x, light_direction.y, light_direction.z);
}

mjs_val_t level_get_name(struct mjs *mjs)
{
    if (!level_instance || !level_instance->name)
        return mjs_mk_undefined();
    return mjs_mk_string(mjs, level_instance->name, ~0, 1);
}

mjs_val_t level_get_size(struct mjs *mjs)
{
    if (!level_instance)
        return mjs_mk_undefined();
    const Vector size = level_instance->size;
    return mjs_mk_vector(mjs, size.x, size.y, size.z);
}

mjs_val_t level_get_shadow_color(struct mjs *mjs)
{
    if (!level_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)(int)level_instance->getShadowColor());
}

mjs_val_t level_is_clear_allowed(struct mjs *mjs)
{
    if (!level_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, (int)level_instance->isClearAllowed());
}

mjs_val_t level_get_entity(struct mjs *mjs)
{
    if (!level_instance)
        return mjs_mk_undefined();

    mjs_val_t index_val = mjs_arg(mjs, 0);
    if (!mjs_is_number(index_val))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "index must be a number");
        return mjs_mk_undefined();
    }
    int index = mjs_get_int(mjs, index_val);

    if (index < 0 || index >= level_instance->getEntityCount())
        return mjs_mk_undefined();

    Entity *e = level_instance->getEntity(index);
    if (!e)
        return mjs_mk_undefined();

    return mjs_mk_foreign(mjs, (void *)e);
}

mjs_val_t level_has_collided(struct mjs *mjs)
{
    if (!level_instance)
        return mjs_mk_undefined();

    mjs_val_t entity_arg = mjs_arg(mjs, 0);
    mjs_val_t entity_ptr = mjs_is_object(entity_arg)
                               ? mjs_get(mjs, entity_arg, "_entity", ~0)
                               : entity_arg;
    if (!mjs_is_foreign(entity_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "entity must be an Entity");
        return mjs_mk_undefined();
    }

    Entity *entity = (Entity *)mjs_get_ptr(mjs, entity_ptr);
    if (!entity)
        return mjs_mk_boolean(mjs, 0);

    return mjs_mk_boolean(mjs, (int)level_instance->has_collided(entity));
}

void level_clear(struct mjs *mjs)
{
    if (level_instance)
        level_instance->clear();
}

void level_entity_add(struct mjs *mjs)
{
    if (!level_instance)
        return;

    mjs_val_t entity_arg = mjs_arg(mjs, 0);
    mjs_val_t entity_ptr = mjs_is_object(entity_arg)
                               ? mjs_get(mjs, entity_arg, "_entity", ~0)
                               : entity_arg;
    if (!mjs_is_foreign(entity_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "entity must be an Entity");
        return;
    }

    Entity *entity = (Entity *)mjs_get_ptr(mjs, entity_ptr);
    if (entity)
        level_instance->entity_add(entity);
}

void level_entity_remove(struct mjs *mjs)
{
    if (!level_instance)
        return;

    mjs_val_t entity_arg = mjs_arg(mjs, 0);
    mjs_val_t entity_ptr = mjs_is_object(entity_arg)
                               ? mjs_get(mjs, entity_arg, "_entity", ~0)
                               : entity_arg;
    if (!mjs_is_foreign(entity_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "entity must be an Entity");
        return;
    }

    Entity *entity = (Entity *)mjs_get_ptr(mjs, entity_ptr);
    if (entity)
        level_instance->entity_remove(entity);
}

void level_set(struct mjs *mjs)
{
    if (!level_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "No level instance");
        return;
    }

    if (!mjs_is_string(mjs_arg(mjs, 0)))
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Property name must be a string");
        return;
    }

    mjs_val_t name_val = mjs_arg(mjs, 0);
    size_t name_len = 0;
    const char *name = mjs_get_string(mjs, &name_val, &name_len);

    if (strcmp(name, "name") == 0)
    {
        mjs_val_t value = mjs_arg(mjs, 1);
        size_t value_len = 0;
        const char *value_str = mjs_is_string(value) ? mjs_get_string(mjs, &value, &value_len) : NULL;
        if (value_str)
        {
            char *buffer = (char *)m_malloc(value_len + 1);
            if (buffer)
            {
                memcpy(buffer, value_str, value_len);
                buffer[value_len] = '\0';
                if (level_name_owned)
                    m_free(const_cast<char *>(level_instance->name));
                level_instance->name = (const char *)buffer;
                level_name_owned = true;
            }
        }
    }
    else if (strcmp(name, "size") == 0)
    {
        float x, y, z;
        if (mjs_get_vector(mjs, 1, &x, &y, &z))
        {
            level_instance->size.x = x;
            level_instance->size.y = y;
            level_instance->size.z = z;
        }
    }
    else if (strcmp(name, "lightDirection") == 0)
    {
        float x, y, z;
        if (mjs_get_vector(mjs, 1, &x, &y, &z))
            level_instance->setLightDirection(x, y, z);
    }
    else if (strcmp(name, "shadowColor") == 0)
        level_instance->setShadowColor(mjs_get_color(mjs, mjs_arg(mjs, 1)));
    else if (strcmp(name, "clearAllowed") == 0)
        level_instance->setClearAllowed(mjs_get_bool(mjs, mjs_arg(mjs, 1)));
}

void level_create(struct mjs *mjs, mjs_val_t *level_obj)
{
    if (level_instance)
    {
        if (level_name_owned)
            m_free(const_cast<char *>(level_instance->name));
        // Detach from the game's non-owning level references.
        if (Game *g = static_cast<Game *>(game_get_instance()))
        {
            for (int i = 0; i < MAX_LEVELS; i++)
                if (g->levels[i] == level_instance)
                    g->levels[i] = nullptr;
            g->current_level = nullptr;
        }
        delete level_instance;
        level_instance = nullptr;
        level_name_owned = false;
    }

    // Parse name (owned by this binding) and size first, then construct.
    const char *name_str = "";
    size_t name_len = 0;
    {
        mjs_val_t name_val = mjs_arg(mjs, 1);
        if (mjs_is_string(name_val))
            name_str = mjs_get_string(mjs, &name_val, &name_len);
    }
    char *name = nullptr;
    if (name_len)
    {
        name = (char *)m_malloc(name_len + 1);
        if (!name)
        {
            *level_obj = mjs_mk_undefined();
            mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to allocate level name");
            return;
        }
        memcpy(name, name_str, name_len);
        name[name_len] = '\0';
    }

    Vector size(640.0f, 480.0f, 0.0f, false);
    {
        mjs_val_t size_val = mjs_arg(mjs, 2);
        float x, y, z;
        if (mjs_is_object(size_val) && mjs_get_vector(mjs, 2, &x, &y, &z))
            size = Vector(x, y, z, false);
    }

    // Constructor binds the level to the live game (gameRef), so entities
    // added through the level take effect immediately.
    Game *g = static_cast<Game *>(game_get_instance());
    if (g)
    {
        level_instance = new Level(name, size, g);
    }
    else
    {
        // No game yet: default-construct and fill name/size by hand
        // (same ownership semantics as before).
        level_instance = new Level();
        if (level_instance)
        {
            level_instance->name = name;
            level_instance->size = size;
        }
    }
    level_name_owned = name != nullptr;

    if (!level_instance)
    {
        m_free(name);
        *level_obj = mjs_mk_undefined();
        return;
    }

    if (g)
    {
        g->level_add(level_instance);
        g->current_level = level_instance;
        g->is_active = true;
    }

    *level_obj = mjs_mk_object(mjs);
    // Raw level handle for engine/other-module resolution.
    mjs_set(mjs, *level_obj, "_level", ~0, mjs_mk_foreign(mjs, (void *)level_instance));
    mjs_set_getter(mjs, *level_obj, "name", ~0, level_get_name);
    mjs_set_getter(mjs, *level_obj, "size", ~0, level_get_size);
    mjs_set_getter(mjs, *level_obj, "lightDirection", ~0, level_get_light_direction);
    mjs_set_getter(mjs, *level_obj, "shadowColor", ~0, level_get_shadow_color);
    mjs_set_getter(mjs, *level_obj, "clearAllowed", ~0, level_is_clear_allowed);
    mjs_set_getter(mjs, *level_obj, "entityCount", ~0, level_get_entity_count);
    mjs_set(mjs, *level_obj, "clear", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_clear));
    mjs_set(mjs, *level_obj, "entityAdd", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_entity_add));
    mjs_set(mjs, *level_obj, "entityRemove", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_entity_remove));
    mjs_set(mjs, *level_obj, "hasCollided", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_has_collided));
    mjs_set(mjs, *level_obj, "getEntity", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_get_entity));
    mjs_set(mjs, *level_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_set));
}

void level_destroy()
{
    if (level_instance)
    {
        if (level_name_owned)
            m_free(const_cast<char *>(level_instance->name));
        // Detach from the game's non-owning level references before
        // deleting the level so the game holds no dangling pointer.
        if (Game *g = static_cast<Game *>(game_get_instance()))
        {
            for (int i = 0; i < MAX_LEVELS; i++)
                if (g->levels[i] == level_instance)
                    g->levels[i] = nullptr;
            g->current_level = nullptr;
        }
        delete level_instance;
    }
    level_instance = nullptr;
    level_name_owned = false;
}