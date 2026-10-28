#include "triangle3d.h"
#include "../engine/pico-game-engine/engine/triangle3d.hpp"
#include "../engine/memory.h"

static Triangle3D *triangle3d_instance = nullptr;

mjs_val_t triangle3d_get_x1(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->x1 : 0.0f);
}

mjs_val_t triangle3d_get_y1(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->y1 : 0.0f);
}

mjs_val_t triangle3d_get_z1(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->z1 : 0.0f);
}

mjs_val_t triangle3d_get_x2(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->x2 : 0.0f);
}

mjs_val_t triangle3d_get_y2(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->y2 : 0.0f);
}

mjs_val_t triangle3d_get_z2(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->z2 : 0.0f);
}

mjs_val_t triangle3d_get_x3(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->x3 : 0.0f);
}

mjs_val_t triangle3d_get_y3(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->y3 : 0.0f);
}

mjs_val_t triangle3d_get_z3(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->z3 : 0.0f);
}

mjs_val_t triangle3d_get_color(struct mjs *mjs)
{
    return mjs_mk_number(mjs, triangle3d_instance ? triangle3d_instance->color : 0);
}

mjs_val_t triangle3d_get_wireframe(struct mjs *mjs)
{
    return mjs_mk_boolean(mjs, triangle3d_instance && triangle3d_instance->wireframe);
}

void triangle3d_set(struct mjs *mjs)
{
    if (triangle3d_instance)
    {
        mjs_val_t name_val = mjs_arg(mjs, 0);
        if (mjs_is_undefined(name_val) || mjs_is_null(name_val))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "name must be a non-null value");
            return;
        }

        size_t len;
        const char *name = mjs_get_string(mjs, &name_val, &len);

        if (strcmp(name, "x1") == 0)
        {
            triangle3d_instance->x1 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "y1") == 0)
        {
            triangle3d_instance->y1 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "z1") == 0)
        {
            triangle3d_instance->z1 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "x2") == 0)
        {
            triangle3d_instance->x2 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "y2") == 0)
        {
            triangle3d_instance->y2 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "z2") == 0)
        {
            triangle3d_instance->z2 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "x3") == 0)
        {
            triangle3d_instance->x3 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "y3") == 0)
        {
            triangle3d_instance->y3 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "z3") == 0)
        {
            triangle3d_instance->z3 = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "color") == 0)
        {
            triangle3d_instance->color = (uint16_t)mjs_get_int(mjs, 1);
        }
        else if (strcmp(name, "wireframe") == 0)
        {
            triangle3d_instance->wireframe = mjs_get_boolean(mjs, mjs_arg(mjs, 1));
        }
    }
}

void triangle3d_create(struct mjs *mjs, mjs_val_t *triangle3d_obj)
{
    *triangle3d_obj = mjs_mk_object(mjs);

    // shifted because parent func has the first arg as the import name
    mjs_val_t val = mjs_arg(mjs, 1);
    if (mjs_is_null(val) || mjs_is_undefined(val) || !mjs_is_object(val))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "Invalid argument 1: expected an object with x1, y1, z1, x2, y2, z2, x3, y3, z3, [color], [wireframe]");
        return;
    }
    mjs_val_t x1_val = mjs_get(mjs, val, "x1", ~0);
    mjs_val_t y1_val = mjs_get(mjs, val, "y1", ~0);
    mjs_val_t z1_val = mjs_get(mjs, val, "z1", ~0);
    mjs_val_t x2_val = mjs_get(mjs, val, "x2", ~0);
    mjs_val_t y2_val = mjs_get(mjs, val, "y2", ~0);
    mjs_val_t z2_val = mjs_get(mjs, val, "z2", ~0);
    mjs_val_t x3_val = mjs_get(mjs, val, "x3", ~0);
    mjs_val_t y3_val = mjs_get(mjs, val, "y3", ~0);
    mjs_val_t z3_val = mjs_get(mjs, val, "z3", ~0);
    mjs_val_t color_val = mjs_get(mjs, val, "color", ~0);
    mjs_val_t wireframe_val = mjs_get(mjs, val, "wireframe", ~0);

    float x1 = mjs_is_number(x1_val) ? static_cast<float>(mjs_get_double(mjs, x1_val)) : 0.0;
    float x2 = mjs_is_number(x2_val) ? static_cast<float>(mjs_get_double(mjs, x2_val)) : 0.0;
    float x3 = mjs_is_number(x3_val) ? static_cast<float>(mjs_get_double(mjs, x3_val)) : 0.0;
    float y1 = mjs_is_number(y1_val) ? static_cast<float>(mjs_get_double(mjs, y1_val)) : 0.0;
    float y2 = mjs_is_number(y2_val) ? static_cast<float>(mjs_get_double(mjs, y2_val)) : 0.0;
    float y3 = mjs_is_number(y3_val) ? static_cast<float>(mjs_get_double(mjs, y3_val)) : 0.0;
    float z1 = mjs_is_number(z1_val) ? static_cast<float>(mjs_get_double(mjs, z1_val)) : 0.0;
    float z2 = mjs_is_number(z2_val) ? static_cast<float>(mjs_get_double(mjs, z2_val)) : 0.0;
    float z3 = mjs_is_number(z3_val) ? static_cast<float>(mjs_get_double(mjs, z3_val)) : 0.0;
    uint16_t color = mjs_is_number(color_val) ? static_cast<uint16_t>(mjs_get_int(mjs, color_val)) : 0x0000;
    bool wireframe = mjs_is_boolean(wireframe_val) ? mjs_get_bool(mjs, wireframe_val) : false;

    triangle3d_instance = new Triangle3D(x1, y1, z1, x2, y2, z2, x3, y3, z3, color, wireframe);

    mjs_set_getter(mjs, *triangle3d_obj, "x1", ~0, triangle3d_get_x1);
    mjs_set_getter(mjs, *triangle3d_obj, "y1", ~0, triangle3d_get_y1);
    mjs_set_getter(mjs, *triangle3d_obj, "z1", ~0, triangle3d_get_z1);
    mjs_set_getter(mjs, *triangle3d_obj, "x2", ~0, triangle3d_get_x2);
    mjs_set_getter(mjs, *triangle3d_obj, "y2", ~0, triangle3d_get_y2);
    mjs_set_getter(mjs, *triangle3d_obj, "z2", ~0, triangle3d_get_z2);
    mjs_set_getter(mjs, *triangle3d_obj, "x3", ~0, triangle3d_get_x3);
    mjs_set_getter(mjs, *triangle3d_obj, "y3", ~0, triangle3d_get_y3);
    mjs_set_getter(mjs, *triangle3d_obj, "z3", ~0, triangle3d_get_z3);
    mjs_set_getter(mjs, *triangle3d_obj, "color", ~0, triangle3d_get_color);
    mjs_set_getter(mjs, *triangle3d_obj, "wireframe", ~0, triangle3d_get_wireframe);

    mjs_set(mjs, *triangle3d_obj, "set", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)triangle3d_set));
}

void triangle3d_destroy()
{
    triangle3d_instance = nullptr;
}