#include "level.h"
#include "entity.h"
#include "game.h"
#include "../../engine/pico-game-engine/engine/level.hpp"
#include "../../engine/pico-game-engine/engine/game.hpp"
#include "../engine/memory.h"

static bool level_name_owned = false;

static Level *level_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Level");
        return nullptr;
    }
    mjs_val_t level_ptr = mjs_get(mjs, this_obj, "_level", ~0);
    if (!mjs_is_foreign(level_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "level must be a Level");
        return nullptr;
    }
    return (Level *)mjs_get_ptr(mjs, level_ptr);
}

void level_destroy(struct mjs *mjs)
{
    Level *level = level_get_this(mjs);
    if (!level)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_level", ~0, mjs_mk_undefined());
    mjs_slot_release(level);
    delete level;
    level = nullptr;
    level_name_owned = false;
}

void level_get(struct mjs *mjs)
{
    Level *level = level_get_this(mjs);
    if (!level)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid Level instance");
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
        mjs_return(mjs, mjs_mk_string(mjs, level->name, ~0, 1));
        return;
    }
    if (strcmp(name, "entityCount") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)level->getEntityCount()));
        return;
    }
    if (strcmp(name, "lightDirection") == 0)
    {
        const Vector light_direction = level->getLightDirection();
        mjs_return(mjs, mjs_mk_vector(mjs, light_direction.x, light_direction.y, light_direction.z));
        return;
    }
    if (strcmp(name, "size") == 0)
    {
        const Vector size = level->size;
        mjs_return(mjs, mjs_mk_vector(mjs, size.x, size.y, size.z));
        return;
    }
    if (strcmp(name, "shadowColor") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)(int)level->getShadowColor()));
        return;
    }
    if (strcmp(name, "isClearAllowed") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)level->isClearAllowed()));
        return;
    }
    if (strcmp(name, "entity") == 0)
    {
        mjs_val_t index_val = mjs_arg(mjs, 1);
        if (!mjs_is_number(index_val))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "index must be a number");
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }
        int index = mjs_get_int(mjs, index_val);

        if (index < 0 || index >= level->getEntityCount())
        {
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }

        Entity *e = level->getEntity(index);
        if (!e)
        {
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }

        mjs_return(mjs, entity_get_object(mjs, e));
        return;
    }
}

mjs_val_t level_get_object(struct mjs *mjs, void *level_instance_ptr)
{
    Level *level_instance = static_cast<Level *>(level_instance_ptr);
    if (!level_instance)
        return mjs_mk_undefined();

    mjs_val_t level_obj = mjs_mk_object(mjs);
    mjs_set(mjs, level_obj, "_level", ~0, mjs_mk_foreign(mjs, (void *)level_instance));
    mjs_set(mjs, level_obj, "destroy", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_destroy));
    mjs_set(mjs, level_obj, "get", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_get));
    mjs_set(mjs, level_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_set));

    mjs_set(mjs, level_obj, "clear", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_clear));
    mjs_set(mjs, level_obj, "entityAdd", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_entity_add));
    mjs_set(mjs, level_obj, "entityRemove", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_entity_remove));
    mjs_set(mjs, level_obj, "hasCollided", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)level_has_collided));

    return level_obj;
}

void *level_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t level_arg = mjs_arg(mjs, arg);
    mjs_val_t level_ptr = mjs_is_object(level_arg)
                              ? mjs_get(mjs, level_arg, "_level", ~0)
                              : level_arg;
    if (!mjs_is_foreign(level_ptr))
    {
        return nullptr;
    }

    return (Level *)mjs_get_ptr(mjs, level_ptr);
}

void level_has_collided(struct mjs *mjs)
{
    Level *level_instance = level_get_this(mjs);
    if (!level_instance)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        return;
    }

    Entity *entity = (Entity *)entity_get_pointer(mjs, 0);
    if (!entity)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "No entity instance");
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        return;
    }

    mjs_return(mjs, mjs_mk_boolean(mjs, (int)level_instance->has_collided(entity)));
    return;
}

void level_clear(struct mjs *mjs)
{
    Level *level_instance = level_get_this(mjs);
    if (level_instance)
        level_instance->clear();
}

void level_entity_add(struct mjs *mjs)
{
    Level *level_instance = level_get_this(mjs);
    if (!level_instance)
        return;

    Entity *entity = (Entity *)entity_get_pointer(mjs, 0);
    if (entity)
        level_instance->entity_add(entity);
}

void level_entity_remove(struct mjs *mjs)
{
    Level *level_instance = level_get_this(mjs);
    if (!level_instance)
        return;

    Entity *entity = (Entity *)entity_get_pointer(mjs, 0);
    if (entity)
        level_instance->entity_remove(entity);
}

void level_set(struct mjs *mjs)
{
    Level *level_instance = level_get_this(mjs);
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
    // Args: pointer/self, name, size, game
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

    Level *level_instance = nullptr;

    Game *g = static_cast<Game *>(game_get_pointer(mjs, 3));
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

    mjs_slot_set(level_instance);

    *level_obj = level_get_object(mjs, level_instance);
}