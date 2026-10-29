#include "image.h"
#include "../engine/pico-game-engine/engine/image.hpp"
#include "../engine/memory.h"
#include "../array_buf.h"

static Image *image_instance = nullptr;

mjs_val_t image_get_data(struct mjs *mjs)
{
    const size_t data_size = image_instance->getDataSize();
    void *data = (void *)m_malloc(data_size);
    if (!data)
    {
        mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "unable to allocate image data");
        return mjs_mk_undefined();
    }
    if (!image_instance->getData(data, data_size))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "unable to get image data");
        m_free(data);
        return mjs_mk_undefined();
    }
    return mjs_mk_array_buf(mjs, data, data_size);
}

mjs_val_t image_get_data_size(struct mjs *mjs)
{
    return mjs_mk_number(mjs, image_instance ? (double)image_instance->getDataSize() : 0);
}

mjs_val_t image_get_mask(struct mjs *mjs)
{
    const size_t data_size = image_instance->getMaskSize();
    void *data = (void *)m_malloc(data_size);
    if (!data)
    {
        mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "unable to allocate mask data");
        return mjs_mk_undefined();
    }
    if (!image_instance->getMask(data, data_size))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "unable to get image mask");
        m_free(data);
        return mjs_mk_undefined();
    }
    return mjs_mk_array_buf(mjs, data, data_size);
}

mjs_val_t image_get_mask_size(struct mjs *mjs)
{
    return mjs_mk_number(mjs, image_instance ? (double)image_instance->getMaskSize() : 0);
}

mjs_val_t image_get_size(struct mjs *mjs)
{
    if (!image_instance)
    {
        return mjs_mk_undefined();
    }
    const Vector size = image_instance->size;
    mjs_val_t size_obj = mjs_mk_object(mjs);
    mjs_set(mjs, size_obj, "width", ~0, mjs_mk_number(mjs, size.x));
    mjs_set(mjs, size_obj, "height", ~0, mjs_mk_number(mjs, size.y));
    return size_obj;
}

mjs_val_t image_has_mask(struct mjs *mjs)
{
    return mjs_mk_boolean(mjs, image_instance && image_instance->hasMask());
}

void image_create(struct mjs *mjs, mjs_val_t *image_obj)
{
    *image_obj = mjs_mk_object(mjs);

    // Arguments: size (object), is_8bit (bool), data (optional), path (optional), mask (optional)
    // shifted because parent func has the first arg as the import name
    mjs_val_t size_obj = mjs_arg(mjs, 1);
    if (!mjs_is_object(size_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "size must be an object");
        return;
    }
    mjs_val_t width_val = mjs_get(mjs, size_obj, "width", ~0);
    mjs_val_t height_val = mjs_get(mjs, size_obj, "height", ~0);
    float width = (float)mjs_get_double(mjs, width_val);
    float height = (float)mjs_get_double(mjs, height_val);
    bool is_8bit = mjs_get_boolean(mjs, 2);

    const mjs_val_t data_value = mjs_arg(mjs, 3);
    mjs_val_t path_value = mjs_arg(mjs, 4);
    const mjs_val_t mask_value = mjs_arg(mjs, 5);
    const bool has_data = !mjs_is_undefined(data_value) && !mjs_is_null(data_value);
    const bool has_path = !mjs_is_undefined(path_value) && !mjs_is_null(path_value);
    const bool has_mask = !mjs_is_undefined(mask_value) && !mjs_is_null(mask_value);

    const char *path = "";
    size_t path_length = 0;
    if (has_path)
    {
        if (!mjs_is_string(path_value))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "image path must be a string");
            return;
        }
        path = mjs_get_string(mjs, &path_value, &path_length);
        if (!path)
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "image path must be a string");
            return;
        }
    }

    if (has_mask &&
        (!is_8bit || !has_data ||
         width < 1 || width > 1024 || height < 1 || height > 1024 ||
         static_cast<uint16_t>(width) != width || static_cast<uint16_t>(height) != height))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid masked image");
        return;
    }

    mjs_input_buffer data_buffer;
    mjs_input_buffer mask_buffer;
    if (has_data && !mjs_read_buffer(mjs, data_value, static_cast<size_t>(mjs_array_length(mjs, data_value)), false, "pixel data", &data_buffer))
    {
        return;
    }
    if (has_mask && !mjs_read_buffer(mjs, mask_value, static_cast<size_t>(mjs_array_length(mjs, mask_value)), true, "mask", &mask_buffer))
    {
        mjs_input_buffer_free(&data_buffer);
        return;
    }

    image_instance = new Image(Vector(width, height), has_data ? data_buffer.data : nullptr, has_path ? path : nullptr, has_mask ? mask_buffer.data : nullptr);

    mjs_input_buffer_free(&data_buffer);
    mjs_input_buffer_free(&mask_buffer);

    mjs_set_getter(mjs, *image_obj, "hasMask", ~0, image_has_mask);
    mjs_set_getter(mjs, *image_obj, "size", ~0, image_get_size);
    mjs_set_getter(mjs, *image_obj, "data", ~0, image_get_data);
    mjs_set_getter(mjs, *image_obj, "mask", ~0, image_get_mask);
    mjs_set_getter(mjs, *image_obj, "dataSize", ~0, image_get_data_size);
    mjs_set_getter(mjs, *image_obj, "maskSize", ~0, image_get_mask_size);
}

void image_destroy()
{
    image_instance = nullptr;
}