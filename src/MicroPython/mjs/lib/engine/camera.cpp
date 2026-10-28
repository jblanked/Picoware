#include "camera.h"
#include "../engine/pico-game-engine/engine/camera.hpp"
#include "../engine/memory.h"

static Camera *camera_instance = nullptr;
static Camera *global_camera_instance = nullptr;

static mjs_val_t _camera_get_direction(struct mjs *mjs)
{
    if (!global_camera_instance)
    {
        return mjs_mk_undefined();
    }
    const Vector direction = global_camera_instance->direction;
    return mjs_mk_vector(mjs, direction.x, direction.y, direction.z);
}

mjs_val_t camera_get_direction(struct mjs *mjs)
{
    if (!camera_instance)
    {
        return mjs_mk_undefined();
    }
    const Vector direction = camera_instance->direction;
    return mjs_mk_vector(mjs, direction.x, direction.y, direction.z);
}

mjs_val_t camera_get_distance(struct mjs *mjs)
{
    return mjs_mk_number(mjs, camera_instance ? (double)camera_instance->distance : 0.0);
}

mjs_val_t camera_get_height(struct mjs *mjs)
{
    return mjs_mk_number(mjs, camera_instance ? (double)camera_instance->height : 0.0);
}

mjs_val_t camera_get_perspective(struct mjs *mjs)
{
    return mjs_mk_number(mjs, camera_instance ? (int)camera_instance->perspective : (int)CAMERA_FIRST_PERSON);
}

mjs_val_t camera_get_plane(struct mjs *mjs)
{
    if (!camera_instance)
    {
        return mjs_mk_undefined();
    }
    const Vector plane = camera_instance->plane;
    return mjs_mk_vector(mjs, plane.x, plane.y, plane.z);
}

mjs_val_t camera_get_position(struct mjs *mjs)
{
    if (!camera_instance)
    {
        return mjs_mk_undefined();
    }
    const Vector position = camera_instance->position;
    return mjs_mk_vector(mjs, position.x, position.y, position.z);
}

void camera_set(struct mjs *mjs)
{
    if (camera_instance)
    {
        mjs_val_t name_val = mjs_arg(mjs, 0);
        if (mjs_is_undefined(name_val) || mjs_is_null(name_val))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "name must be a non-null value");
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
            }
        }
        else if (strcmp(name, "height") == 0)
        {
            camera_instance->height = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "distance") == 0)
        {
            camera_instance->distance = mjs_get_float(mjs, 1);
        }
        else if (strcmp(name, "perspective") == 0)
        {
            mjs_val_t perspective_val = mjs_arg(mjs, 1);
            camera_instance->perspective = (CameraPerspective)mjs_get_int(mjs, perspective_val);
        }
    }
}

void camera_create(struct mjs *mjs, mjs_val_t *camera_obj)
{
    *camera_obj = mjs_mk_object(mjs);

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
        float position_x = mjs_get_float(mjs, position_x_val);
        float position_y = mjs_get_float(mjs, position_y_val);
        float position_z = mjs_get_float(mjs, position_z_val);
        //
        mjs_val_t direction_x_val = mjs_get(mjs, direction_obj, "x", ~0);
        mjs_val_t direction_y_val = mjs_get(mjs, direction_obj, "y", ~0);
        mjs_val_t direction_z_val = mjs_get(mjs, direction_obj, "z", ~0);
        float direction_x = mjs_get_float(mjs, direction_x_val);
        float direction_y = mjs_get_float(mjs, direction_y_val);
        float direction_z = mjs_get_float(mjs, direction_z_val);
        //
        mjs_val_t plane_x_val = mjs_get(mjs, plane_obj, "x", ~0);
        mjs_val_t plane_y_val = mjs_get(mjs, plane_obj, "y", ~0);
        mjs_val_t plane_z_val = mjs_get(mjs, plane_obj, "z", ~0);
        float plane_x = mjs_get_float(mjs, plane_x_val);
        float plane_y = mjs_get_float(mjs, plane_y_val);
        float plane_z = mjs_get_float(mjs, plane_z_val);
        //
        float height = mjs_get_float(mjs, height_val);
        float distance = mjs_get_float(mjs, distance_val);
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

    mjs_set_getter(mjs, *camera_obj, "position", ~0, camera_get_position);
    mjs_set_getter(mjs, *camera_obj, "direction", ~0, camera_get_direction);
    mjs_set_getter(mjs, *camera_obj, "plane", ~0, camera_get_plane);
    mjs_set_getter(mjs, *camera_obj, "height", ~0, camera_get_height);
    mjs_set_getter(mjs, *camera_obj, "distance", ~0, camera_get_distance);
    mjs_set_getter(mjs, *camera_obj, "perspective", ~0, camera_get_perspective);

    mjs_set(mjs, *camera_obj, "set", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)camera_set));
}

mjs_val_t camera_get_context(struct mjs *mjs, void *cameraContext)
{
    if (!cameraContext)
        return mjs_mk_undefined();
    Camera *camera = static_cast<Camera *>(cameraContext);
    if (!camera)
        return mjs_mk_undefined();
    global_camera_instance = camera;
    mjs_val_t camera_obj = mjs_mk_object(mjs);
    mjs_set_getter(mjs, camera_obj, "direction", ~0, _camera_get_direction);
    return camera_obj;
}

void camera_destroy()
{
    camera_instance = nullptr;
}