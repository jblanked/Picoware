#include "image.h"
#include "../engine/pico-game-engine/engine/image.hpp"
#include "../engine/memory.h"
#include "../array_buf.h"

static Image *image_get_this(struct mjs *mjs)
{
    mjs_val_t this_obj = mjs_get_this(mjs);
    if (!mjs_is_object(this_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "must be called on a Image");
        return nullptr;
    }
    mjs_val_t image_ptr = mjs_get(mjs, this_obj, "_image", ~0);
    if (!mjs_is_foreign(image_ptr))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "image must be a Image");
        return nullptr;
    }
    return (Image *)mjs_get_ptr(mjs, image_ptr);
}

void image_destroy(struct mjs *mjs)
{
    Image *img = image_get_this(mjs);
    if (!img)
    {
        return;
    }
    mjs_set(mjs, mjs_get_this(mjs), "_image", ~0, mjs_mk_undefined());
    delete img;
    img = nullptr;
}

void image_get(struct mjs *mjs)
{
    Image *image = image_get_this(mjs);
    if (!image)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "invalid image instance");
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

    if (strcmp(name, "width") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)image->size.x));
    }
    else if (strcmp(name, "height") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)image->size.y));
    }
    else if (strcmp(name, "size") == 0)
    {
        mjs_val_t size_obj = mjs_mk_object(mjs);
        mjs_set(mjs, size_obj, "width", ~0, mjs_mk_number(mjs, (double)image->size.x));
        mjs_set(mjs, size_obj, "height", ~0, mjs_mk_number(mjs, (double)image->size.y));
        mjs_return(mjs, size_obj);
    }
    else if (strcmp(name, "dataSize") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)image->getDataSize()));
    }
    else if (strcmp(name, "maskSize") == 0)
    {
        mjs_return(mjs, mjs_mk_number(mjs, (double)image->getMaskSize()));
    }
    else if (strcmp(name, "hasMask") == 0)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, image->hasMask()));
    }
    else if (strcmp(name, "data") == 0)
    {
        const size_t size = image->getDataSize();
        void *data = (void *)m_malloc(size);
        if (!data)
        {
            mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "unable to allocate image data");
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }
        if (!image->getData(data, size))
        {
            m_free(data);
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "unable to get image data");
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }
        mjs_return(mjs, mjs_mk_array_buf(mjs, data, size));
    }
    else if (strcmp(name, "mask") == 0)
    {
        if (!image->hasMask())
        {
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }
        const size_t size = image->getMaskSize();
        void *data = (void *)m_malloc(size);
        if (!data)
        {
            mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "unable to allocate mask data");
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }
        if (!image->getMask(data, size))
        {
            m_free(data);
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "unable to get image mask");
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }
        mjs_return(mjs, mjs_mk_array_buf(mjs, data, size));
    }
    else
    {
        mjs_return(mjs, mjs_mk_undefined());
    }
}

void *image_get_pointer(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t image_arg = mjs_arg(mjs, arg);
    mjs_val_t image_ptr = mjs_is_object(image_arg)
                              ? mjs_get(mjs, image_arg, "_image", ~0)
                              : image_arg;
    if (!mjs_is_foreign(image_ptr))
    {
        return nullptr;
    }

    return (Image *)mjs_get_ptr(mjs, image_ptr);
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

    mjs_input_buffer data_buffer = {};
    mjs_input_buffer mask_buffer = {};
    if (has_data && !mjs_read_buffer(mjs, data_value, static_cast<size_t>(mjs_array_length(mjs, data_value)), false, "pixel data", &data_buffer))
    {
        return;
    }
    if (has_mask && !mjs_read_buffer(mjs, mask_value, static_cast<size_t>(mjs_array_length(mjs, mask_value)), true, "mask", &mask_buffer))
    {
        mjs_input_buffer_free(&data_buffer);
        return;
    }

    const Vector sz = Vector(width, height);

    Image *image_instance = new Image(sz, has_data ? data_buffer.data : nullptr, has_path ? path : nullptr, has_mask ? mask_buffer.data : nullptr);

    mjs_input_buffer_free(&data_buffer);
    mjs_input_buffer_free(&mask_buffer);

    if (!image_instance)
    {
        mjs_prepend_errorf(mjs, MJS_INTERNAL_ERROR, "Failed to create image instance");
        return;
    }

    mjs_set(mjs, *image_obj, "_image", ~0, mjs_mk_foreign(mjs, image_instance));
    mjs_set(mjs, *image_obj, "destroy", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)image_destroy));
    mjs_set(mjs, *image_obj, "get", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)image_get));
}
