#include "entity.h"
#include "../engine/pico-game-engine/engine/entity.hpp"

static Entity *entity_instance = nullptr;

mjs_val_t entity_get_name(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    if (entity_instance->name)
        return mjs_mk_string(mjs, entity_instance->name, ~0, 1);
    return mjs_mk_string(mjs, "entity", ~0, 0);
}

mjs_val_t entity_get_type(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)(int)entity_instance->type);
}

mjs_val_t entity_get_state(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)(int)entity_instance->state);
}

mjs_val_t entity_get_position(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->position.x,
                         entity_instance->position.y,
                         entity_instance->position.z);
}

mjs_val_t entity_get_old_position(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->old_position.x,
                         entity_instance->old_position.y,
                         entity_instance->old_position.z);
}

mjs_val_t entity_get_size(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->size.x,
                         entity_instance->size.y,
                         entity_instance->size.z);
}

mjs_val_t entity_get_direction(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->direction.x,
                         entity_instance->direction.y,
                         entity_instance->direction.z);
}

mjs_val_t entity_get_plane(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->plane.x,
                         entity_instance->plane.y,
                         entity_instance->plane.z);
}

mjs_val_t entity_get_start_position(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->start_position.x,
                         entity_instance->start_position.y,
                         entity_instance->start_position.z);
}

mjs_val_t entity_get_end_position(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->end_position.x,
                         entity_instance->end_position.y,
                         entity_instance->end_position.z);
}

mjs_val_t entity_get_aabb_min(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->aabb_min.x,
                         entity_instance->aabb_min.y,
                         entity_instance->aabb_min.z);
}

mjs_val_t entity_get_aabb_max(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_vector(mjs,
                         entity_instance->aabb_max.x,
                         entity_instance->aabb_max.y,
                         entity_instance->aabb_max.z);
}

mjs_val_t entity_get_is_8bit(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->is_8bit);
}

mjs_val_t entity_get_is_active(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->is_active);
}

mjs_val_t entity_get_is_visible(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->is_visible);
}

mjs_val_t entity_get_is_player(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->is_player);
}

mjs_val_t entity_get_aabb_dirty(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->aabb_dirty);
}

mjs_val_t entity_get_moved(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->moved);
}

mjs_val_t entity_get_has_3d_sprite(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->has3DSprite());
}

mjs_val_t entity_get_has_changed_position(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_boolean(mjs, entity_instance->hasChangedPosition());
}

mjs_val_t entity_get_move_timer(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->move_timer);
}

mjs_val_t entity_get_elapsed_move_timer(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->elapsed_move_timer);
}

mjs_val_t entity_get_radius(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->radius);
}

mjs_val_t entity_get_speed(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->speed);
}

mjs_val_t entity_get_attack_timer(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->attack_timer);
}

mjs_val_t entity_get_elapsed_attack_timer(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->elapsed_attack_timer);
}

mjs_val_t entity_get_strength(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->strength);
}

mjs_val_t entity_get_health(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->health);
}

mjs_val_t entity_get_max_health(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->max_health);
}

mjs_val_t entity_get_level(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->level);
}

mjs_val_t entity_get_xp(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->xp);
}

mjs_val_t entity_get_health_regen(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->health_regen);
}

mjs_val_t entity_get_elapsed_health_regen(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->elapsed_health_regen);
}

mjs_val_t entity_get_sprite_rotation(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->sprite_rotation);
}

mjs_val_t entity_get_sprite_scale(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->sprite_scale);
}

mjs_val_t entity_get_sprite_3d_type(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)(int)entity_instance->sprite_3d_type);
}

mjs_val_t entity_get_billboard_pose(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)(int)entity_instance->billboard_pose);
}

mjs_val_t entity_get_billboard_world_height(struct mjs *mjs)
{
    if (!entity_instance)
        return mjs_mk_undefined();
    return mjs_mk_number(mjs, (double)entity_instance->billboard_world_height);
}

void entity_set(struct mjs *mjs)
{
    if (!entity_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "No entity instance");
        return;
    }

    mjs_val_t name_val = mjs_arg(mjs, 0);
    if (!mjs_is_string(name_val))
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Property name must be a string");
        return;
    }
    size_t name_len = 0;
    const char *name = mjs_get_string(mjs, &name_val, &name_len);

    if (strcmp(name, "position") == 0 ||
        strcmp(name, "oldPosition") == 0 ||
        strcmp(name, "direction") == 0 ||
        strcmp(name, "plane") == 0 ||
        strcmp(name, "startPosition") == 0 ||
        strcmp(name, "endPosition") == 0 ||
        strcmp(name, "aabbMin") == 0 ||
        strcmp(name, "aabbMax") == 0)
    {
        float x, y, z;
        if (!mjs_get_vector(mjs, 1, &x, &y, &z))
        {
            mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR,
                               "Vector property requires an object with x, y, z");
            return;
        }
        if (strcmp(name, "position") == 0)
        {
            entity_instance->position_set(x, y, z, false);
        }
        else if (strcmp(name, "oldPosition") == 0)
        {
            entity_instance->old_position = Vector(x, y, z, false);
        }
        else if (strcmp(name, "direction") == 0)
        {
            entity_instance->direction = Vector(x, y, z, false);
        }
        else if (strcmp(name, "plane") == 0)
        {
            entity_instance->plane = Vector(x, y, z, false);
        }
        else if (strcmp(name, "startPosition") == 0)
        {
            entity_instance->start_position = Vector(x, y, z, false);
        }
        else if (strcmp(name, "endPosition") == 0)
        {
            entity_instance->end_position = Vector(x, y, z, false);
        }
        /* aabb_min / aabb_max require updateAABB to be called */
    }
    else if (strcmp(name, "size") == 0)
    {
        float x, y, z;
        if (mjs_get_vector(mjs, 1, &x, &y, &z))
        {
            entity_instance->size = Vector(x, y, z, false);
        }
    }

    else if (strcmp(name, "is_active") == 0)
    {
        entity_instance->is_active = (mjs_get_boolean(mjs, 1)) ? 1 : 0;
    }
    else if (strcmp(name, "is_visible") == 0)
    {
        entity_instance->is_visible = (mjs_get_boolean(mjs, 1)) ? 1 : 0;
    }
    else if (strcmp(name, "is_player") == 0)
    {
        entity_instance->is_player = (mjs_get_boolean(mjs, 1)) ? 1 : 0;
    }

    else if (strcmp(name, "move_timer") == 0)
        entity_instance->move_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "elapsed_move_timer") == 0)
        entity_instance->elapsed_move_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "radius") == 0)
        entity_instance->radius = mjs_get_float(mjs, 1);
    else if (strcmp(name, "speed") == 0)
        entity_instance->speed = mjs_get_float(mjs, 1);
    else if (strcmp(name, "attack_timer") == 0)
        entity_instance->attack_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "elapsed_attack_timer") == 0)
        entity_instance->elapsed_attack_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "strength") == 0)
        entity_instance->strength = mjs_get_float(mjs, 1);
    else if (strcmp(name, "health") == 0)
        entity_instance->health = mjs_get_float(mjs, 1);
    else if (strcmp(name, "max_health") == 0)
        entity_instance->max_health = mjs_get_float(mjs, 1);
    else if (strcmp(name, "level") == 0)
        entity_instance->level = mjs_get_float(mjs, 1);
    else if (strcmp(name, "xp") == 0)
        entity_instance->xp = mjs_get_float(mjs, 1);
    else if (strcmp(name, "health_regen") == 0)
        entity_instance->health_regen = mjs_get_float(mjs, 1);
    else if (strcmp(name, "elapsed_health_regen") == 0)
        entity_instance->elapsed_health_regen = mjs_get_float(mjs, 1);
    else if (strcmp(name, "rotation") == 0)
        entity_instance->set3DSpriteRotation(mjs_get_float(mjs, 1));
    else if (strcmp(name, "scale") == 0)
        entity_instance->set3DSpriteScale(mjs_get_float(mjs, 1));

    else if (strcmp(name, "state") == 0)
    {
        mjs_val_t v = mjs_arg(mjs, 1);
        if (mjs_is_number(v))
            entity_instance->state = (EntityState)mjs_get_int(mjs, v);
    }
    else if (strcmp(name, "type") == 0)
    {
        mjs_val_t v = mjs_arg(mjs, 1);
        if (mjs_is_number(v))
            entity_instance->type = (EntityType)mjs_get_int(mjs, v);
    }
    else if (strcmp(name, "sprite_3d_type") == 0)
    {
        mjs_val_t v = mjs_arg(mjs, 1);
        if (mjs_is_number(v))
            entity_instance->sprite_3d_type = (Sprite3DType)mjs_get_int(mjs, v);
    }
    else if (strcmp(name, "billboard_pose") == 0)
    {
        mjs_val_t v = mjs_arg(mjs, 1);
        if (mjs_is_number(v))
            entity_instance->setBillboardPose((int)mjs_get_int(mjs, v));
    }
    else if (strcmp(name, "billboard_world_height") == 0)
    {
        entity_instance->billboard_world_height = mjs_get_float(mjs, 1);
    }

    else if (strcmp(name, "name") == 0)
    {
        mjs_val_t v = mjs_arg(mjs, 1);
        size_t str_len = 0;
        const char *s = mjs_get_string(mjs, &v, &str_len);
        if (s)
        {
            char *buf = (char *)m_malloc(str_len + 1);
            if (buf)
            {
                memcpy(buf, s, str_len + 1);
                if (entity_instance->name)
                    m_free(const_cast<char *>(entity_instance->name));
                entity_instance->name = (const char *)buf;
            }
        }
    }
}

void entity_update_position(struct mjs *mjs)
{
    if (!entity_instance)
        return;
    entity_instance->updateAABB();
}

void entity_create(struct mjs *mjs, mjs_val_t *entity_obj)
{
    *entity_obj = mjs_mk_object(mjs);

    /* Args: 1=name(string), 2=type(int), 3=position({x,y,z}), 4=size({x,y,z}), 5=sprite_3d_type(int), 6=sprite_3d_color(int) */
    mjs_val_t name_val = mjs_arg(mjs, 1);

    int type = mjs_is_number(mjs_arg(mjs, 2))
                   ? (int)mjs_get_int(mjs, mjs_arg(mjs, 2))
                   : (int)ENTITY_PLAYER;

    float px = 0.0f, py = 0.0f, pz = 0.0f;
    mjs_val_t pos = mjs_arg(mjs, 3);
    if (mjs_is_object(pos))
    {
        float x, y, z;
        if (!mjs_get_vector(mjs, 3, &x, &y, &z))
        {
            mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR,
                               "Position must be {x, y, z}");
            return;
        }
        px = x;
        py = y;
        pz = z;
    }

    float sx = 64.0f, sy = 64.0f, sz = 0.0f;
    mjs_val_t szv = mjs_arg(mjs, 4);
    if (mjs_is_object(szv))
    {
        float x, y, z;
        if (!mjs_get_vector(mjs, 4, &x, &y, &z))
        {
            mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR,
                               "Size must be {x, y, z}");
            return;
        }
        sx = x;
        sy = y;
        sz = z;
    }

    int sprite_3d_type = mjs_is_number(mjs_arg(mjs, 5))
                             ? (int)mjs_get_int(mjs, mjs_arg(mjs, 5))
                             : (int)SPRITE_3D_NONE;

    int sprite_3d_color = mjs_is_number(mjs_arg(mjs, 6))
                              ? (int)mjs_get_int(mjs, mjs_arg(mjs, 6))
                              : 0;

    char *name_buf = (char *)m_malloc(256);
    if (!name_buf)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR,
                           "Failed to allocate entity name");
        return;
    }
    {
        size_t n_len = 0;
        const char *s = mjs_is_string(name_val)
                            ? mjs_get_string(mjs, &name_val, &n_len)
                            : NULL;
        if (s)
        {
            size_t copy_len = (n_len < 255) ? n_len : 255;
            memcpy(name_buf, s, copy_len);
            name_buf[copy_len] = '\0';
        }
        else
        {
            strncpy(name_buf, "entity", 255);
        }
    }

    Entity *entity = new Entity(
        name_buf,
        (EntityType)type,
        Vector(px, py, pz, false),
        Vector(sx, sy, sz, false),
        nullptr,
        nullptr,
        nullptr,
        nullptr,
        nullptr,
        nullptr,
        nullptr,
        nullptr,
        false,
        (Sprite3DType)sprite_3d_type,
        (uint16_t)sprite_3d_color);

    if (!entity)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR,
                           "Entity creation failed (out of memory)");
        m_free(name_buf);
        return;
    }
    entity_instance = entity;
    mjs_set(mjs, *entity_obj, "_entity", ~0, mjs_mk_foreign(mjs, entity));

    mjs_set_getter(mjs, *entity_obj, "name", ~0, entity_get_name);
    mjs_set_getter(mjs, *entity_obj, "type", ~0, entity_get_type);
    mjs_set_getter(mjs, *entity_obj, "state", ~0, entity_get_state);
    mjs_set_getter(mjs, *entity_obj, "position", ~0, entity_get_position);
    mjs_set_getter(mjs, *entity_obj, "oldPosition", ~0, entity_get_old_position);
    mjs_set_getter(mjs, *entity_obj, "size", ~0, entity_get_size);
    mjs_set_getter(mjs, *entity_obj, "direction", ~0, entity_get_direction);
    mjs_set_getter(mjs, *entity_obj, "plane", ~0, entity_get_plane);
    mjs_set_getter(mjs, *entity_obj, "startPosition", ~0, entity_get_start_position);
    mjs_set_getter(mjs, *entity_obj, "endPosition", ~0, entity_get_end_position);
    mjs_set_getter(mjs, *entity_obj, "aabbMin", ~0, entity_get_aabb_min);
    mjs_set_getter(mjs, *entity_obj, "aabbMax", ~0, entity_get_aabb_max);
    mjs_set_getter(mjs, *entity_obj, "is8bit", ~0, entity_get_is_8bit);
    mjs_set_getter(mjs, *entity_obj, "isActive", ~0, entity_get_is_active);
    mjs_set_getter(mjs, *entity_obj, "isVisible", ~0, entity_get_is_visible);
    mjs_set_getter(mjs, *entity_obj, "isPlayer", ~0, entity_get_is_player);
    mjs_set_getter(mjs, *entity_obj, "aabbDirty", ~0, entity_get_aabb_dirty);
    mjs_set_getter(mjs, *entity_obj, "moved", ~0, entity_get_moved);
    mjs_set_getter(mjs, *entity_obj, "has3dSprite", ~0, entity_get_has_3d_sprite);
    mjs_set_getter(mjs, *entity_obj, "hasChangedPosition", ~0, entity_get_has_changed_position);
    mjs_set_getter(mjs, *entity_obj, "moveTimer", ~0, entity_get_move_timer);
    mjs_set_getter(mjs, *entity_obj, "elapsedMoveTimer", ~0, entity_get_elapsed_move_timer);
    mjs_set_getter(mjs, *entity_obj, "radius", ~0, entity_get_radius);
    mjs_set_getter(mjs, *entity_obj, "speed", ~0, entity_get_speed);
    mjs_set_getter(mjs, *entity_obj, "attackTimer", ~0, entity_get_attack_timer);
    mjs_set_getter(mjs, *entity_obj, "elapsedAttackTimer", ~0, entity_get_elapsed_attack_timer);
    mjs_set_getter(mjs, *entity_obj, "strength", ~0, entity_get_strength);
    mjs_set_getter(mjs, *entity_obj, "health", ~0, entity_get_health);
    mjs_set_getter(mjs, *entity_obj, "maxHealth", ~0, entity_get_max_health);
    mjs_set_getter(mjs, *entity_obj, "level", ~0, entity_get_level);
    mjs_set_getter(mjs, *entity_obj, "xp", ~0, entity_get_xp);
    mjs_set_getter(mjs, *entity_obj, "healthRegen", ~0, entity_get_health_regen);
    mjs_set_getter(mjs, *entity_obj, "elapsedHealthRegen", ~0, entity_get_elapsed_health_regen);
    mjs_set_getter(mjs, *entity_obj, "spriteRotation", ~0, entity_get_sprite_rotation);
    mjs_set_getter(mjs, *entity_obj, "spriteScale", ~0, entity_get_sprite_scale);
    mjs_set_getter(mjs, *entity_obj, "sprite3dType", ~0, entity_get_sprite_3d_type);
    mjs_set_getter(mjs, *entity_obj, "billboardPose", ~0, entity_get_billboard_pose);
    mjs_set_getter(mjs, *entity_obj, "billboardWorldHeight", ~0, entity_get_billboard_world_height);

    mjs_set(mjs, *entity_obj, "set", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)entity_set));
    mjs_set(mjs, *entity_obj, "updatePosition", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)entity_update_position));

    mjs_set(mjs, *entity_obj, "ENTITY_PLAYER", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_PLAYER));
    mjs_set(mjs, *entity_obj, "ENTITY_ENEMY", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ENEMY));
    mjs_set(mjs, *entity_obj, "ENTITY_ICON", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ICON));
    mjs_set(mjs, *entity_obj, "ENTITY_NPC", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_NPC));
    mjs_set(mjs, *entity_obj, "ENTITY_3D_SPRITE", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_3D_SPRITE));

    mjs_set(mjs, *entity_obj, "ENTITY_IDLE", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_IDLE));
    mjs_set(mjs, *entity_obj, "ENTITY_MOVING", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_MOVING));
    mjs_set(mjs, *entity_obj, "ENTITY_MOVING_TO_START", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_MOVING_TO_START));
    mjs_set(mjs, *entity_obj, "ENTITY_MOVING_TO_END", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_MOVING_TO_END));
    mjs_set(mjs, *entity_obj, "ENTITY_ATTACKING", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ATTACKING));
    mjs_set(mjs, *entity_obj, "ENTITY_ATTACKED", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ATTACKED));
    mjs_set(mjs, *entity_obj, "ENTITY_DEAD", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_DEAD));

    mjs_set(mjs, *entity_obj, "SPRITE_3D_NONE", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_NONE));
    mjs_set(mjs, *entity_obj, "SPRITE_3D_HUMANOID", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_HUMANOID));
    mjs_set(mjs, *entity_obj, "SPRITE_3D_TREE", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_TREE));
    mjs_set(mjs, *entity_obj, "SPRITE_3D_HOUSE", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_HOUSE));
    mjs_set(mjs, *entity_obj, "SPRITE_3D_PILLAR", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_PILLAR));
    mjs_set(mjs, *entity_obj, "SPRITE_3D_CUSTOM", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_CUSTOM));
}

void entity_destroy()
{
    entity_instance = nullptr;
}
