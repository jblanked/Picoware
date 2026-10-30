#include "entity.h"
#include "image.h"
#include "level.h"
#include "sprite3d.h"
#include "../engine/pico-game-engine/engine/entity.hpp"
#include "../engine/memory.h"

static Entity *entity_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Entity");
        return nullptr;
    }
    mjs_val_t entity_ptr = mjs_get(mjs, this_obj, "_entity", ~0);
    if (!mjs_is_foreign(entity_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "entity must be a Entity");
        return nullptr;
    }
    return (Entity *)mjs_get_ptr(mjs, entity_ptr);
}

void entity_destroy(struct mjs *mjs)
{
    Entity *entity = entity_get_this(mjs);
    if (!entity)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_entity", ~0, mjs_mk_undefined());
    mjs_slot_release(entity);
    delete entity;
    entity = nullptr;
}

void entity_get(struct mjs *mjs)
{
    Entity *entity_instance = entity_get_this(mjs);
    if (!entity_instance)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid entity instance");
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
        mjs_return(mjs, mjs_mk_string(mjs, entity_instance->name, ~0, 1));
        return;
    }
    if (strcmp(name, "type") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->type));
        return;
    }
    if (strcmp(name, "state") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->state));
        return;
    }
    if (strcmp(name, "position") == 0)
    {
        const Vector position = entity_instance->position;
        mjs_return(mjs, mjs_mk_vector(mjs, position.x, position.y, position.z));
        return;
    }
    if (strcmp(name, "oldPosition") == 0)
    {
        const Vector old_position = entity_instance->old_position;
        mjs_return(mjs, mjs_mk_vector(mjs, old_position.x, old_position.y, old_position.z));
        return;
    }
    if (strcmp(name, "size") == 0)
    {
        const Vector size = entity_instance->size;
        mjs_return(mjs, mjs_mk_vector(mjs, size.x, size.y, size.z));
        return;
    }
    if (strcmp(name, "direction") == 0)
    {
        const Vector direction = entity_instance->direction;
        mjs_return(mjs, mjs_mk_vector(mjs, direction.x, direction.y, direction.z));
        return;
    }
    if (strcmp(name, "plane") == 0)
    {
        const Vector plane = entity_instance->plane;
        mjs_return(mjs, mjs_mk_vector(mjs, plane.x, plane.y, plane.z));
        return;
    }
    if (strcmp(name, "startPosition") == 0)
    {
        const Vector start_position = entity_instance->start_position;
        mjs_return(mjs, mjs_mk_vector(mjs, start_position.x, start_position.y, start_position.z));
        return;
    }
    if (strcmp(name, "endPosition") == 0)
    {
        const Vector end_position = entity_instance->end_position;
        mjs_return(mjs, mjs_mk_vector(mjs, end_position.x, end_position.y, end_position.z));
        return;
    }
    if (strcmp(name, "aabbMin") == 0)
    {
        const Vector aabb_min = entity_instance->aabb_min;
        mjs_return(mjs, mjs_mk_vector(mjs, aabb_min.x, aabb_min.y, aabb_min.z));
        return;
    }
    if (strcmp(name, "aabbMax") == 0)
    {
        const Vector aabb_max = entity_instance->aabb_max;
        mjs_return(mjs, mjs_mk_vector(mjs, aabb_max.x, aabb_max.y, aabb_max.z));
        return;
    }
    if (strcmp(name, "is8bit") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->is_8bit));
        return;
    }
    if (strcmp(name, "isActive") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->is_active));
        return;
    }
    if (strcmp(name, "isVisible") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->is_visible));
        return;
    }
    if (strcmp(name, "isPlayer") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->is_player));
        return;
    }
    if (strcmp(name, "aabbDirty") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->aabb_dirty));
        return;
    }
    if (strcmp(name, "moved") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->moved));
        return;
    }
    if (strcmp(name, "has3DSprite") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->has3DSprite()));
        return;
    }
    if (strcmp(name, "hasChangedPosition") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, (int)entity_instance->hasChangedPosition()));
        return;
    }
    if (strcmp(name, "moveTimer") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->move_timer));
        return;
    }
    if (strcmp(name, "elapsedMoveTimer") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->elapsed_move_timer));
        return;
    }
    if (strcmp(name, "radius") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->radius));
        return;
    }
    if (strcmp(name, "speed") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->speed));
        return;
    }
    if (strcmp(name, "attackTimer") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->attack_timer));
        return;
    }
    if (strcmp(name, "elapsedAttackTimer") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->elapsed_attack_timer));
        return;
    }
    if (strcmp(name, "strength") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->strength));
        return;
    }
    if (strcmp(name, "health") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->health));
        return;
    }
    if (strcmp(name, "maxHealth") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->max_health));
        return;
    }
    if (strcmp(name, "level") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->level));
        return;
    }
    if (strcmp(name, "healthRegen") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->health_regen));
        return;
    }
    if (strcmp(name, "spriteRotation") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->sprite_rotation));
        return;
    }
    if (strcmp(name, "spriteScale") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->sprite_scale));
        return;
    }
    if (strcmp(name, "sprite3DType") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->sprite_3d_type));
        return;
    }
    if (strcmp(name, "billboardPose") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->billboard_pose));
        return;
    }
    if (strcmp(name, "billboardWorldHeight") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)entity_instance->billboard_world_height));
        return;
    }
    if (strcmp(name, "sprite3D") == 0)
    {
        mjs_return(mjs, sprite3d_get_object(mjs, entity_instance->sprite_3d));
        return;
    }

    mjs_return(mjs, mjs_mk_undefined());
}

mjs_val_t entity_get_object(struct mjs *mjs, void *entity_instance_ptr)
{
    Entity *entity_instance = static_cast<Entity *>(entity_instance_ptr);
    if (!entity_instance)
        return mjs_mk_undefined();

    mjs_val_t entity_obj = mjs_mk_object(mjs);

    mjs_set(mjs, entity_obj, "_entity", ~0, mjs_mk_foreign(mjs, entity_instance));

    mjs_set(mjs, entity_obj, "destroy", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)entity_destroy));
    mjs_set(mjs, entity_obj, "get", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)entity_get));
    mjs_set(mjs, entity_obj, "set", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)entity_set));
    mjs_set(mjs, entity_obj, "updatePosition", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)entity_update_position));

    mjs_set(mjs, entity_obj, "ENTITY_PLAYER", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_PLAYER));
    mjs_set(mjs, entity_obj, "ENTITY_ENEMY", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ENEMY));
    mjs_set(mjs, entity_obj, "ENTITY_ICON", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ICON));
    mjs_set(mjs, entity_obj, "ENTITY_NPC", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_NPC));
    mjs_set(mjs, entity_obj, "ENTITY_3D_SPRITE", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_3D_SPRITE));

    mjs_set(mjs, entity_obj, "ENTITY_IDLE", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_IDLE));
    mjs_set(mjs, entity_obj, "ENTITY_MOVING", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_MOVING));
    mjs_set(mjs, entity_obj, "ENTITY_MOVING_TO_START", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_MOVING_TO_START));
    mjs_set(mjs, entity_obj, "ENTITY_MOVING_TO_END", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_MOVING_TO_END));
    mjs_set(mjs, entity_obj, "ENTITY_ATTACKING", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ATTACKING));
    mjs_set(mjs, entity_obj, "ENTITY_ATTACKED", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_ATTACKED));
    mjs_set(mjs, entity_obj, "ENTITY_DEAD", ~0,
            mjs_mk_number(mjs, (double)(int)ENTITY_DEAD));

    mjs_set(mjs, entity_obj, "SPRITE_3D_NONE", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_NONE));
    mjs_set(mjs, entity_obj, "SPRITE_3D_HUMANOID", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_HUMANOID));
    mjs_set(mjs, entity_obj, "SPRITE_3D_TREE", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_TREE));
    mjs_set(mjs, entity_obj, "SPRITE_3D_HOUSE", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_HOUSE));
    mjs_set(mjs, entity_obj, "SPRITE_3D_PILLAR", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_PILLAR));
    mjs_set(mjs, entity_obj, "SPRITE_3D_CUSTOM", ~0,
            mjs_mk_number(mjs, (double)(int)SPRITE_3D_CUSTOM));

    return entity_obj;
}

void *entity_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t entity_arg = mjs_arg(mjs, arg);
    mjs_val_t entity_ptr = mjs_is_object(entity_arg)
                               ? mjs_get(mjs, entity_arg, "_entity", ~0)
                               : entity_arg;
    if (!mjs_is_foreign(entity_ptr))
    {
        return nullptr;
    }

    return (Entity *)mjs_get_ptr(mjs, entity_ptr);
}

void entity_set(struct mjs *mjs)
{
    Entity *entity_instance = entity_get_this(mjs);
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

    else if (strcmp(name, "isActive") == 0)
    {
        entity_instance->is_active = mjs_get_boolean(mjs, 1);
    }
    else if (strcmp(name, "isVisible") == 0)
    {
        entity_instance->is_visible = mjs_get_boolean(mjs, 1);
    }
    else if (strcmp(name, "isPlayer") == 0)
    {
        entity_instance->is_player = mjs_get_boolean(mjs, 1);
    }

    else if (strcmp(name, "moveTimer") == 0)
        entity_instance->move_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "elapsedMoveTimer") == 0)
        entity_instance->elapsed_move_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "radius") == 0)
        entity_instance->radius = mjs_get_float(mjs, 1);
    else if (strcmp(name, "speed") == 0)
        entity_instance->speed = mjs_get_float(mjs, 1);
    else if (strcmp(name, "attackTimer") == 0)
        entity_instance->attack_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "elapsedAttackTimer") == 0)
        entity_instance->elapsed_attack_timer = mjs_get_float(mjs, 1);
    else if (strcmp(name, "strength") == 0)
        entity_instance->strength = mjs_get_float(mjs, 1);
    else if (strcmp(name, "health") == 0)
        entity_instance->health = mjs_get_float(mjs, 1);
    else if (strcmp(name, "maxHealth") == 0)
        entity_instance->max_health = mjs_get_float(mjs, 1);
    else if (strcmp(name, "level") == 0)
        entity_instance->level = mjs_get_float(mjs, 1);
    else if (strcmp(name, "xp") == 0)
        entity_instance->xp = mjs_get_float(mjs, 1);
    else if (strcmp(name, "healthRegen") == 0)
        entity_instance->health_regen = mjs_get_float(mjs, 1);
    else if (strcmp(name, "elapsedHealthRegen") == 0)
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
    else if (strcmp(name, "sprite3DType") == 0)
    {
        mjs_val_t v = mjs_arg(mjs, 1);
        if (mjs_is_number(v))
            entity_instance->sprite_3d_type = (Sprite3DType)mjs_get_int(mjs, v);
    }
    else if (strcmp(name, "billboardPose") == 0)
    {
        mjs_val_t v = mjs_arg(mjs, 1);
        if (mjs_is_number(v))
            entity_instance->setBillboardPose((int)mjs_get_int(mjs, v));
    }
    else if (strcmp(name, "billboardWorldHeight") == 0)
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
    else if (strcmp(name, "sprite3D") == 0)
    {
        entity_instance->sprite_3d = static_cast<Sprite3D *>(sprite3d_get_pointer(mjs, 1));
    }
    else
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR,
                           "Unknown property: %s", name);
    }
}

void entity_update_position(struct mjs *mjs)
{
    Entity *entity_instance = entity_get_this(mjs);
    if (!entity_instance)
        return;
    entity_instance->updateAABB();
}

void entity_create(struct mjs *mjs, mjs_val_t *entity_obj)
{
    /* Args: 1=name(string), 2=type(int), 3=position({x,y,z}), 4=size({x,y,z}), 5=sprite_data(image), 6=sprite_left_data(image), 7=sprite_right_data(image), 8=sprite_3d_type(int), 9=sprite_3d_color(int) */
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

    Image *sprite_data = (Image *)image_get_pointer(mjs, 5);
    Image *sprite_left_data = (Image *)image_get_pointer(mjs, 6);
    Image *sprite_right_data = (Image *)image_get_pointer(mjs, 7);

    int sprite_3d_type = mjs_is_number(mjs_arg(mjs, 8))
                             ? (int)mjs_get_int(mjs, mjs_arg(mjs, 8))
                             : (int)SPRITE_3D_NONE;

    int sprite_3d_color = mjs_is_number(mjs_arg(mjs, 9))
                              ? (int)mjs_get_int(mjs, mjs_arg(mjs, 9))
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
            snprintf(name_buf, 255, "entity");
        }
    }

    Entity *entity = new Entity(
        name_buf,
        (EntityType)type,
        Vector(px, py, pz, false),
        Vector(sx, sy, sz, false),
        sprite_data,
        sprite_left_data,
        sprite_right_data,
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
    mjs_slot_set(entity);
    *entity_obj = entity_get_object(mjs, entity);
}
