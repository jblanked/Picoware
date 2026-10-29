#include "sprite3d.h"
#include "../engine/pico-game-engine/engine/sprite3d.hpp"
#include "../engine/memory.h"

static Sprite3D *sprite3d_instance = nullptr;

mjs_val_t sprite3d_get_position(struct mjs *mjs)
{
    if (!sprite3d_instance)
        return mjs_mk_undefined();
    const Vector position = sprite3d_instance->getPosition();
    return mjs_mk_vector(mjs, position.x, position.y, position.z);
}

mjs_val_t sprite3d_get_rotation(struct mjs *mjs)
{
    return mjs_mk_number(mjs, sprite3d_instance ? (double)sprite3d_instance->getRotation() : 0.0);
}

mjs_val_t sprite3d_get_scale(struct mjs *mjs)
{
    return mjs_mk_number(mjs, sprite3d_instance ? (double)sprite3d_instance->getScale() : 0.0);
}

mjs_val_t sprite3d_get_triangle_count(struct mjs *mjs)
{
    return mjs_mk_number(mjs, sprite3d_instance ? (double)sprite3d_instance->getTriangleCount() : 0.0);
}

mjs_val_t sprite3d_get_type(struct mjs *mjs)
{
    return mjs_mk_number(mjs, sprite3d_instance ? (double)sprite3d_instance->getType() : 0.0);
}

mjs_val_t sprite3d_is_active(struct mjs *mjs)
{
    return mjs_mk_boolean(mjs, sprite3d_instance ? sprite3d_instance->isActive() : false);
}

void sprite3d_add_triangle(struct mjs *mjs)
{
    if (sprite3d_instance)
    {
        const float x1 = mjs_get_float(mjs, 0);
        const float y1 = mjs_get_float(mjs, 1);
        const float z1 = mjs_get_float(mjs, 2);
        const float x2 = mjs_get_float(mjs, 3);
        const float y2 = mjs_get_float(mjs, 4);
        const float z2 = mjs_get_float(mjs, 5);
        const float x3 = mjs_get_float(mjs, 6);
        const float y3 = mjs_get_float(mjs, 7);
        const float z3 = mjs_get_float(mjs, 8);
        mjs_val_t color_val = mjs_arg(mjs, 9);
        const uint16_t color = mjs_get_color(mjs, color_val);
        mjs_val_t wireframe_val = mjs_arg(mjs, 10);
        const bool wireframe = mjs_is_boolean(wireframe_val) ? mjs_get_bool(mjs, wireframe_val) : false;
        sprite3d_instance->addTriangle(x1, y1, z1, x2, y2, z2, x3, y3, z3, color, wireframe);
    }
}

void sprite3d_bake_transform(struct mjs *mjs)
{
    if (sprite3d_instance)
    {
        sprite3d_instance->bakeTransform();
    }
}

void sprite3d_clear_triangles(struct mjs *mjs)
{
    if (sprite3d_instance)
    {
        sprite3d_instance->clearTriangles();
    }
}

void sprite3d_set(struct mjs *mjs)
{
    if (sprite3d_instance)
    {
        mjs_val_t name_val = mjs_arg(mjs, 0);
        if (mjs_is_undefined(name_val) || mjs_is_null(name_val))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "name must be a non-null value");
            return;
        }

        size_t len;
        const char *name = mjs_get_string(mjs, &name_val, &len);

        if (strcmp(name, "active") == 0)
        {
            mjs_val_t val = mjs_arg(mjs, 1);
            if (mjs_is_boolean(val))
            {
                sprite3d_instance->setActive(mjs_get_bool(mjs, val));
            }
        }
        else if (strcmp(name, "position") == 0)
        {
            float x, y, z;
            if (mjs_get_vector(mjs, 1, &x, &y, &z))
            {
                sprite3d_instance->setPosition(Vector(x, y, z, false));
            }
        }
        else if (strcmp(name, "rotation") == 0)
        {
            sprite3d_instance->setRotation(mjs_get_float(mjs, 1));
        }
        else if (strcmp(name, "scale") == 0)
        {
            sprite3d_instance->setScale(mjs_get_float(mjs, 1));
        }
        else if (strcmp(name, "wireframe") == 0)
        {
            mjs_val_t val = mjs_arg(mjs, 1);
            if (mjs_is_boolean(val))
            {
                sprite3d_instance->setWireframe(mjs_get_bool(mjs, val));
            }
        }
    }
}

void sprite3d_reserve_triangles(struct mjs *mjs)
{
    mjs_val_t val = mjs_arg(mjs, 0);
    if (sprite3d_instance && mjs_is_number(val))
    {
        uint16_t count = (uint16_t)mjs_get_int(mjs, val);
        bool result = sprite3d_instance->reserveTriangles(count);
        mjs_return(mjs, mjs_mk_boolean(mjs, result));
        return;
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

void sprite3d_from_path(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        return;
    }
    char *path = mjs_copy_string_arg(mjs, 0);
    if (path)
    {
        mjs_val_t wireframe_val = mjs_arg(mjs, 1);
        bool wireframe = mjs_is_boolean(wireframe_val) ? mjs_get_bool(mjs, wireframe_val) : true;
        bool result = sprite3d_instance->fromPath(path, wireframe);
        m_free(path);
        mjs_return(mjs, mjs_mk_boolean(mjs, result));
        return;
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

void sprite3d_to_path(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        return;
    }
    char *path = mjs_copy_string_arg(mjs, 0);
    if (path)
    {
        bool result = sprite3d_instance->toPath(path);
        m_free(path);
        mjs_return(mjs, mjs_mk_boolean(mjs, result));
        return;
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

void sprite3d_update_triangle(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        return;
    }
    mjs_val_t index_val = mjs_arg(mjs, 0);
    if (!mjs_is_number(index_val) || mjs_get_double(mjs, index_val) < 0.0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        return;
    }
    uint16_t index = (uint16_t)mjs_get_int(mjs, index_val);
    const float x1 = mjs_get_float(mjs, 1);
    const float y1 = mjs_get_float(mjs, 2);
    const float z1 = mjs_get_float(mjs, 3);
    const float x2 = mjs_get_float(mjs, 4);
    const float y2 = mjs_get_float(mjs, 5);
    const float z2 = mjs_get_float(mjs, 6);
    const float x3 = mjs_get_float(mjs, 7);
    const float y3 = mjs_get_float(mjs, 8);
    const float z3 = mjs_get_float(mjs, 9);
    mjs_val_t color_val = mjs_arg(mjs, 10);
    const uint16_t color = mjs_get_color(mjs, color_val);
    mjs_val_t wireframe_val = mjs_arg(mjs, 11);
    const bool wireframe = mjs_is_boolean(wireframe_val) ? mjs_get_bool(mjs, wireframe_val) : true;
    bool result = sprite3d_instance->updateTriangle(index, x1, y1, z1, x2, y2, z2, x3, y3, z3, color, wireframe);
    mjs_return(mjs, mjs_mk_boolean(mjs, result));
}

void sprite3d_create_humanoid(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    float height = 1.8f;
    mjs_val_t height_val = mjs_arg(mjs, 0);
    if (mjs_is_number(height_val))
    {
        height = (float)mjs_get_double(mjs, height_val);
    }
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 1));
    sprite3d_instance->createHumanoid(height, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_tree(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    float height = 2.0f;
    mjs_val_t height_val = mjs_arg(mjs, 0);
    if (mjs_is_number(height_val))
    {
        height = (float)mjs_get_double(mjs, height_val);
    }
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 1));
    sprite3d_instance->createTree(height, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_house(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    float width = 2.0f;
    mjs_val_t width_val = mjs_arg(mjs, 0);
    if (mjs_is_number(width_val))
    {
        width = (float)mjs_get_double(mjs, width_val);
    }
    float height = 2.5f;
    mjs_val_t height_val = mjs_arg(mjs, 1);
    if (mjs_is_number(height_val))
    {
        height = (float)mjs_get_double(mjs, height_val);
    }
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 2));
    sprite3d_instance->createHouse(width, height, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_pillar(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    float height = 3.0f;
    mjs_val_t height_val = mjs_arg(mjs, 0);
    if (mjs_is_number(height_val))
    {
        height = (float)mjs_get_double(mjs, height_val);
    }
    float radius = 0.3f;
    mjs_val_t radius_val = mjs_arg(mjs, 1);
    if (mjs_is_number(radius_val))
    {
        radius = (float)mjs_get_double(mjs, radius_val);
    }
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 2));
    sprite3d_instance->createPillar(height, radius, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_wall(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    const float x = mjs_get_float(mjs, 0);
    const float y = mjs_get_float(mjs, 1);
    const float z = mjs_get_float(mjs, 2);
    float width = 4.0f;
    mjs_val_t width_val = mjs_arg(mjs, 3);
    if (mjs_is_number(width_val))
    {
        width = (float)mjs_get_double(mjs, width_val);
    }
    float height = 1.5f;
    mjs_val_t height_val = mjs_arg(mjs, 4);
    if (mjs_is_number(height_val))
    {
        height = (float)mjs_get_double(mjs, height_val);
    }
    float depth = 0.2f;
    mjs_val_t depth_val = mjs_arg(mjs, 5);
    if (mjs_is_number(depth_val))
    {
        depth = (float)mjs_get_double(mjs, depth_val);
    }
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 6));
    sprite3d_instance->createWall(x, y, z, width, height, depth, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_cube(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    const float x = mjs_get_float(mjs, 0);
    const float y = mjs_get_float(mjs, 1);
    const float z = mjs_get_float(mjs, 2);
    const float width = mjs_get_float(mjs, 3);
    const float height = mjs_get_float(mjs, 4);
    const float depth = mjs_get_float(mjs, 5);
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 6));
    sprite3d_instance->createCube(x, y, z, width, height, depth, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_cylinder(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    const float x = mjs_get_float(mjs, 0);
    const float y = mjs_get_float(mjs, 1);
    const float z = mjs_get_float(mjs, 2);
    const float radius = mjs_get_float(mjs, 3);
    const float height = mjs_get_float(mjs, 4);
    mjs_val_t segments_val = mjs_arg(mjs, 5);
    uint8_t segments = (uint8_t)(mjs_is_number(segments_val) ? mjs_get_int(mjs, segments_val) : 0);
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 6));
    sprite3d_instance->createCylinder(x, y, z, radius, height, segments, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_sphere(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    const float x = mjs_get_float(mjs, 0);
    const float y = mjs_get_float(mjs, 1);
    const float z = mjs_get_float(mjs, 2);
    const float radius = mjs_get_float(mjs, 3);
    mjs_val_t segments_val = mjs_arg(mjs, 4);
    uint8_t segments = (uint8_t)(mjs_is_number(segments_val) ? mjs_get_int(mjs, segments_val) : 0);
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 5));
    sprite3d_instance->createSphere(x, y, z, radius, segments, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create_triangular_prism(struct mjs *mjs)
{
    if (!sprite3d_instance)
    {
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    const float x = mjs_get_float(mjs, 0);
    const float y = mjs_get_float(mjs, 1);
    const float z = mjs_get_float(mjs, 2);
    const float width = mjs_get_float(mjs, 3);
    const float height = mjs_get_float(mjs, 4);
    const float depth = mjs_get_float(mjs, 5);
    uint16_t color = mjs_get_color(mjs, mjs_arg(mjs, 6));
    sprite3d_instance->createTriangularPrism(x, y, z, width, height, depth, color);
    mjs_return(mjs, MJS_UNDEFINED);
}

void sprite3d_create(struct mjs *mjs, mjs_val_t *sprite3d_obj)
{
    *sprite3d_obj = mjs_mk_object(mjs);

    sprite3d_instance = new Sprite3D();

    mjs_set_getter(mjs, *sprite3d_obj, "position", ~0, sprite3d_get_position);
    mjs_set_getter(mjs, *sprite3d_obj, "rotation", ~0, sprite3d_get_rotation);
    mjs_set_getter(mjs, *sprite3d_obj, "scale", ~0, sprite3d_get_scale);
    mjs_set_getter(mjs, *sprite3d_obj, "triangleCount", ~0, sprite3d_get_triangle_count);
    mjs_set_getter(mjs, *sprite3d_obj, "type", ~0, sprite3d_get_type);
    mjs_set_getter(mjs, *sprite3d_obj, "active", ~0, sprite3d_is_active);

    mjs_set(mjs, *sprite3d_obj, "addTriangle", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_add_triangle));
    mjs_set(mjs, *sprite3d_obj, "bakeTransform", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_bake_transform));
    mjs_set(mjs, *sprite3d_obj, "clearTriangles", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_clear_triangles));
    mjs_set(mjs, *sprite3d_obj, "reserveTriangles", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_reserve_triangles));
    mjs_set(mjs, *sprite3d_obj, "fromPath", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_from_path));
    mjs_set(mjs, *sprite3d_obj, "toPath", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_to_path));
    mjs_set(mjs, *sprite3d_obj, "updateTriangle", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_update_triangle));
    mjs_set(mjs, *sprite3d_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_set));
    mjs_set(mjs, *sprite3d_obj, "createHumanoid", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_humanoid));
    mjs_set(mjs, *sprite3d_obj, "createTree", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_tree));
    mjs_set(mjs, *sprite3d_obj, "createHouse", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_house));
    mjs_set(mjs, *sprite3d_obj, "createPillar", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_pillar));
    mjs_set(mjs, *sprite3d_obj, "createWall", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_wall));
    mjs_set(mjs, *sprite3d_obj, "createCube", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_cube));
    mjs_set(mjs, *sprite3d_obj, "createCylinder", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_cylinder));
    mjs_set(mjs, *sprite3d_obj, "createSphere", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_sphere));
    mjs_set(mjs, *sprite3d_obj, "createTriangularPrism", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)sprite3d_create_triangular_prism));
}

void sprite3d_destroy()
{
    if (sprite3d_instance)
        delete sprite3d_instance;
    sprite3d_instance = nullptr;
}