#include "triangle3d.h"
#include "../engine/pico-game-engine/engine/triangle3d.hpp"
#include "../engine/memory.h"

static Triangle3D *triangle3d_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Triangle3d");
        return nullptr;
    }
    mjs_val_t triangle3d_ptr = mjs_get(mjs, this_obj, "_triangle3d", ~0);
    if (!mjs_is_foreign(triangle3d_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "triangle3d must be a Triangle3d");
        return nullptr;
    }
    return (Triangle3D *)mjs_get_ptr(mjs, triangle3d_ptr);
}

void triangle3d_destroy(struct mjs *mjs)
{
    Triangle3D *triangle3d = triangle3d_get_this(mjs);
    if (!triangle3d)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_triangle3d", ~0, mjs_mk_undefined());
    mjs_slot_release(triangle3d);
    delete triangle3d;
    triangle3d = nullptr;
}

void triangle3d_get(struct mjs *mjs)
{
    Triangle3D *triangle3d = triangle3d_get_this(mjs);
    if (!triangle3d)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid triangle3d instance");
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

    if (strcmp(name, "x1") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->x1)));
        return;
    }
    else if (strcmp(name, "y1") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->y1)));
        return;
    }
    else if (strcmp(name, "z1") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->z1)));
        return;
    }
    else if (strcmp(name, "x2") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->x2)));
        return;
    }
    else if (strcmp(name, "y2") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->y2)));
        return;
    }
    else if (strcmp(name, "z2") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->z2)));
        return;
    }
    else if (strcmp(name, "x3") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->x3)));
        return;
    }
    else if (strcmp(name, "y3") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->y3)));
        return;
    }
    else if (strcmp(name, "z3") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->z3)));
        return;
    }
    else if (strcmp(name, "color") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, static_cast<double>(triangle3d->color)));
        return;
    }
    else if (strcmp(name, "wireframe") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, triangle3d->wireframe));
        return;
    }
    else
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "unknown property");
        mjs_return(mjs, mjs_mk_undefined());
        return;
    }
}

mjs_val_t triangle3d_get_object(struct mjs *mjs, void *triangle3d_instance_ptr)
{
    Triangle3D *triangle3d = static_cast<Triangle3D *>(triangle3d_instance_ptr);
    if (!triangle3d)
        return mjs_mk_undefined();

    mjs_val_t triangle3d_obj = mjs_mk_object(mjs);

    mjs_set(mjs, triangle3d_obj, "_triangle3d", ~0,
            mjs_mk_foreign(mjs, static_cast<void *>(triangle3d)));
    mjs_set(mjs, triangle3d_obj, "destroy", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)triangle3d_destroy));
    mjs_set(mjs, triangle3d_obj, "get", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)triangle3d_get));
    mjs_set(mjs, triangle3d_obj, "set", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)triangle3d_set));

    return triangle3d_obj;
}

void *triangle3d_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t triangle3d_arg = mjs_arg(mjs, arg);
    mjs_val_t triangle3d_ptr = mjs_is_object(triangle3d_arg)
                                   ? mjs_get(mjs, triangle3d_arg, "_triangle3d", ~0)
                                   : triangle3d_arg;
    if (!mjs_is_foreign(triangle3d_ptr))
    {
        return nullptr;
    }
    return (Triangle3D *)mjs_get_ptr(mjs, triangle3d_ptr);
}

void triangle3d_set(struct mjs *mjs)
{
    Triangle3D *triangle3d_instance = (Triangle3D *)triangle3d_get_this(mjs);
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
            triangle3d_instance->wireframe = mjs_get_boolean(mjs, 1);
        }
    }
}

void triangle3d_create(struct mjs *mjs, mjs_val_t *triangle3d_obj)
{
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
    uint16_t color = mjs_get_color(mjs, color_val);
    bool wireframe = mjs_is_boolean(wireframe_val) ? mjs_get_bool(mjs, wireframe_val) : false;

    Triangle3D *triangle3d_instance = new Triangle3D(x1, y1, z1, x2, y2, z2, x3, y3, z3, color, wireframe);
    mjs_slot_set(triangle3d_instance);
    *triangle3d_obj = triangle3d_get_object(mjs, static_cast<void *>(triangle3d_instance));
}