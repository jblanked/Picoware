#include "billboard.h"
#include "../engine/pico-game-engine/engine/billboard.hpp"
#include "../engine/memory.h"

static Billboard *billboard_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Billboard");
        return nullptr;
    }
    mjs_val_t billboard_ptr = mjs_get(mjs, this_obj, "_billboard", ~0);
    if (!mjs_is_foreign(billboard_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "billboard must be a Billboard");
        return nullptr;
    }
    return (Billboard *)mjs_get_ptr(mjs, billboard_ptr);
}

void *billboard_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t billboard_arg = mjs_arg(mjs, arg);
    mjs_val_t billboard_ptr = mjs_is_object(billboard_arg)
                                  ? mjs_get(mjs, billboard_arg, "_billboard", ~0)
                                  : billboard_arg;
    if (!mjs_is_foreign(billboard_ptr))
    {
        return nullptr;
    }

    return (Billboard *)mjs_get_ptr(mjs, billboard_ptr);
}

void billboard_destroy(struct mjs *mjs)
{
    Billboard *billboard = billboard_get_this(mjs);
    if (!billboard)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_billboard", ~0, mjs_mk_undefined());
    mjs_slot_release(billboard);
    delete billboard;
    billboard = nullptr;
}

void billboard_set(struct mjs *mjs)
{
    Billboard *billboard_instance = billboard_get_this(mjs);
    if (billboard_instance)
    {
        mjs_val_t name_val = mjs_arg(mjs, 0);
        if (mjs_is_undefined(name_val) || mjs_is_null(name_val))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "name must be a non-null value");
            return;
        }

        size_t len;
        const char *name = mjs_get_string(mjs, &name_val, &len);

        if (strcmp(name, "counts") == 0)
        {
            int directions = mjs_get_int(mjs, mjs_arg(mjs, 1));
            int poses = mjs_get_int(mjs, mjs_arg(mjs, 2));
            billboard_instance->setCounts(directions, poses);
        }
        else if (strcmp(name, "directionPose") == 0)
        {
            if (mjs_is_object(mjs_arg(mjs, 1)))
            {
                mjs_val_t direction_val = mjs_get(mjs, mjs_arg(mjs, 1), "direction", ~0);
                mjs_val_t pose_val = mjs_get(mjs, mjs_arg(mjs, 1), "pose", ~0);
                mjs_val_t width_val = mjs_get(mjs, mjs_arg(mjs, 1), "width", ~0);
                mjs_val_t height_val = mjs_get(mjs, mjs_arg(mjs, 1), "height", ~0);
                mjs_val_t pixels_val = mjs_get(mjs, mjs_arg(mjs, 1), "pixels", ~0);
                mjs_val_t mask_val = mjs_get(mjs, mjs_arg(mjs, 1), "mask", ~0);

                int direction = mjs_get_int(mjs, direction_val);
                int pose = mjs_get_int(mjs, pose_val);
                uint16_t width = static_cast<uint16_t>(mjs_get_int(mjs, width_val));
                uint16_t height = static_cast<uint16_t>(mjs_get_int(mjs, height_val));
                mjs_input_buffer pixels_buffer = {};
                mjs_input_buffer mask_buffer = {};

                if (!mjs_read_buffer(mjs, pixels_val, width * height * 4, true, "pixels", &pixels_buffer))
                    return;
                if (!mjs_read_buffer(mjs, mask_val, width * height, true, "mask", &mask_buffer))
                {
                    mjs_input_buffer_free(&pixels_buffer);
                    return;
                }
                billboard_instance->setDirectionPoseData(direction, pose, width, height, pixels_buffer.data, pixels_buffer.length, mask_buffer.data, mask_buffer.length);
            }
        }
    }
}

void billboard_create(struct mjs *mjs, mjs_val_t *billboard_obj)
{
    *billboard_obj = mjs_mk_object(mjs);

    Billboard *billboard_instance = new Billboard();
    mjs_slot_set(billboard_instance);
    mjs_set(mjs, *billboard_obj, "_billboard", ~0, mjs_mk_foreign(mjs, billboard_instance));
    mjs_set(mjs, *billboard_obj, "destroy", ~0, mjs_mk_foreign(mjs, (void *)billboard_destroy));
    mjs_set(mjs, *billboard_obj, "set", ~0, mjs_mk_foreign(mjs, (void *)billboard_set));
}