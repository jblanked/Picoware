#include "camera.h"
#include "../engine/pico-game-engine/engine/camera.hpp"
#include "../engine/memory.h"

static Camera *camera_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Camera");
        return nullptr;
    }
    mjs_val_t camera_ptr = mjs_get(mjs, this_obj, "_camera", ~0);
    if (!mjs_is_foreign(camera_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "camera must be a Camera");
        return nullptr;
    }
    return (Camera *)mjs_get_ptr(mjs, camera_ptr);
}

void camera_destroy(struct mjs *mjs)
{
    Camera *camera = camera_get_this(mjs);
    if (!camera)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_camera", ~0, mjs_mk_undefined());
    delete camera;
    camera = nullptr;
}

mjs_val_t camera_get_object(struct mjs *mjs, void *camera_instance_ptr)
{
    Camera *camera_instance = static_cast<Camera *>(camera_instance_ptr);
    if (!camera_instance)
        return mjs_mk_undefined();

    mjs_val_t camera_obj = mjs_mk_object(mjs);
    mjs_set(mjs, camera_obj, "_camera", ~0, mjs_mk_foreign(mjs, (void *)camera_instance));
    mjs_set(mjs, camera_obj, "destroy", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)camera_destroy));
    mjs_set(mjs, camera_obj, "get", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)camera_get));
    mjs_set(mjs, camera_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)camera_set));

    return camera_obj;
}

void *camera_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t camera_arg = mjs_arg(mjs, arg);
    mjs_val_t camera_ptr = mjs_is_object(camera_arg)
                               ? mjs_get(mjs, camera_arg, "_camera", ~0)
                               : camera_arg;
    if (!mjs_is_foreign(camera_ptr))
    {
        return nullptr;
    }
    return (Camera *)mjs_get_ptr(mjs, camera_ptr);
}

void camera_get(struct mjs *mjs)
{
    Camera *camera = camera_get_this(mjs);
    if (!camera)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid camera instance");
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

    if (strcmp(name, "position") == 0)
    {
        mjs_return(mjs, mjs_mk_vector(mjs, camera->position.x, camera->position.y, camera->position.z));
    }
    else if (strcmp(name, "direction") == 0)
    {
        mjs_return(mjs, mjs_mk_vector(mjs, camera->direction.x, camera->direction.y, camera->direction.z));
    }
    else if (strcmp(name, "plane") == 0)
    {
        mjs_return(mjs, mjs_mk_vector(mjs, camera->plane.x, camera->plane.y, camera->plane.z));
    }
    else if (strcmp(name, "height") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)camera->height));
    }
    else if (strcmp(name, "distance") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)camera->distance));
    }
    else if (strcmp(name, "perspective") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)(int)camera->perspective));
    }
    else
    {
        mjs_return(mjs, mjs_mk_undefined());
    }
}

void camera_set(struct mjs *mjs)
{
    Camera *camera_instance = camera_get_this(mjs);
    if (camera_instance)
    {
        mjs_val_t name_val = mjs_arg(mjs, 0);
        if (mjs_is_undefined(name_val) || mjs_is_null(name_val))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "name must be a non-null value");
            mjs_return(mjs, mjs_mk_boolean(mjs, false));
            return;
        }

        size_t len;
        const char *name = mjs_get_string(mjs, &name_val, &len);

        if (strcmp(name, "position") == 0)
        {
            float x, y, z;
            if (mjs_get_vector(mjs, 1, &x, &y, &z))
            {
                camera_instance->position.x = x;
                camera_instance->position.y = y;
                camera_instance->position.z = z;
                mjs_return(mjs, mjs_mk_boolean(mjs, true));
                return;
            }
        }
        else if (strcmp(name, "plane") == 0)
        {
            float x, y, z;
            if (mjs_get_vector(mjs, 1, &x, &y, &z))
            {
                camera_instance->plane.x = x;
                camera_instance->plane.y = y;
                camera_instance->plane.z = z;
                mjs_return(mjs, mjs_mk_boolean(mjs, true));
                return;
            }
        }
        else if (strcmp(name, "direction") == 0)
        {
            float x, y, z;
            if (mjs_get_vector(mjs, 1, &x, &y, &z))
            {
                camera_instance->direction.x = x;
                camera_instance->direction.y = y;
                camera_instance->direction.z = z;
                mjs_return(mjs, mjs_mk_boolean(mjs, true));
                return;
            }
        }
        else if (strcmp(name, "height") == 0)
        {
            camera_instance->height = mjs_get_float(mjs, 1);
            mjs_return(mjs, mjs_mk_boolean(mjs, true));
            return;
        }
        else if (strcmp(name, "distance") == 0)
        {
            camera_instance->distance = mjs_get_float(mjs, 1);
            mjs_return(mjs, mjs_mk_boolean(mjs, true));
            return;
        }
        else if (strcmp(name, "perspective") == 0)
        {
            mjs_val_t perspective_val = mjs_arg(mjs, 1);
            camera_instance->perspective = (CameraPerspective)mjs_get_int(mjs, perspective_val);
            mjs_return(mjs, mjs_mk_boolean(mjs, true));
            return;
        }
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

void camera_create(struct mjs *mjs, mjs_val_t *camera_obj)
{
    Camera *camera_instance = nullptr;

    // Arguments: optional [position (object), direction (object), plane (object), height (float), distance (float), perspective (int)]
    // shifted because parent func has the first arg as the import name
    mjs_val_t position_obj = mjs_arg(mjs, 1);
    if (mjs_is_undefined(position_obj) || mjs_is_null(position_obj))
    {
        camera_instance = new Camera();
    }
    else
    {
        // if position is provided, everything but perspective is expected to be specified as well
        if (!mjs_is_object(position_obj))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "position must be an object");
            return;
        }
        mjs_val_t direction_obj = mjs_arg(mjs, 2);
        if (!mjs_is_object(direction_obj))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "direction must be an object");
            return;
        }
        mjs_val_t plane_obj = mjs_arg(mjs, 3);
        if (!mjs_is_object(plane_obj))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "plane must be an object");
            return;
        }
        mjs_val_t height_val = mjs_arg(mjs, 4);
        mjs_val_t distance_val = mjs_arg(mjs, 5);
        mjs_val_t perspective_val = mjs_arg(mjs, 6);
        //
        mjs_val_t position_x_val = mjs_get(mjs, position_obj, "x", ~0);
        mjs_val_t position_y_val = mjs_get(mjs, position_obj, "y", ~0);
        mjs_val_t position_z_val = mjs_get(mjs, position_obj, "z", ~0);
        float position_x = static_cast<float>(mjs_get_double(mjs, position_x_val));
        float position_y = static_cast<float>(mjs_get_double(mjs, position_y_val));
        float position_z = static_cast<float>(mjs_get_double(mjs, position_z_val));
        //
        mjs_val_t direction_x_val = mjs_get(mjs, direction_obj, "x", ~0);
        mjs_val_t direction_y_val = mjs_get(mjs, direction_obj, "y", ~0);
        mjs_val_t direction_z_val = mjs_get(mjs, direction_obj, "z", ~0);
        float direction_x = static_cast<float>(mjs_get_double(mjs, direction_x_val));
        float direction_y = static_cast<float>(mjs_get_double(mjs, direction_y_val));
        float direction_z = static_cast<float>(mjs_get_double(mjs, direction_z_val));
        //
        mjs_val_t plane_x_val = mjs_get(mjs, plane_obj, "x", ~0);
        mjs_val_t plane_y_val = mjs_get(mjs, plane_obj, "y", ~0);
        mjs_val_t plane_z_val = mjs_get(mjs, plane_obj, "z", ~0);
        float plane_x = static_cast<float>(mjs_get_double(mjs, plane_x_val));
        float plane_y = static_cast<float>(mjs_get_double(mjs, plane_y_val));
        float plane_z = static_cast<float>(mjs_get_double(mjs, plane_z_val));
        //
        float height = static_cast<float>(mjs_get_double(mjs, height_val));
        float distance = static_cast<float>(mjs_get_double(mjs, distance_val));
        CameraPerspective perspective = mjs_is_number(perspective_val) ? (CameraPerspective)mjs_get_int(mjs, perspective_val) : CAMERA_FIRST_PERSON;

        camera_instance = new Camera(
            Vector(position_x, position_y, position_z),
            Vector(direction_x, direction_y, direction_z),
            Vector(plane_x, plane_y, plane_z),
            height,
            distance,
            perspective);
    }

    if (!camera_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to create camera instance");
        return;
    }

    *camera_obj = camera_get_object(mjs, camera_instance);
}