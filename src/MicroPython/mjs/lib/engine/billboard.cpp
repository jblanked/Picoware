#include "billboard.h"
#include "../engine/pico-game-engine/engine/billboard.hpp"

static Billboard *billboard_instance = nullptr;

void billboard_set(struct mjs *mjs)
{
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
                mjs_input_buffer pixels_buffer;
                mjs_input_buffer mask_buffer;

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

    billboard_instance = new Billboard();
}

void billboard_destroy()
{
    billboard_instance = nullptr;
}