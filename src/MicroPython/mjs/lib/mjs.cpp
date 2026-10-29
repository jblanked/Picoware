#include "mjs.h"
#include "array_buf.h"
#include "color.h"
#include <math.h>

char *mjs_copy_string_arg(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t t_arg = mjs_arg(mjs, arg);
    if (!mjs_is_undefined(t_arg) && !mjs_is_null(t_arg))
    {
        size_t len;
        const char *str = mjs_get_string(mjs, &t_arg, &len);
        if (str != NULL)
        {
            char *copy = (char *)m_malloc(len + 1);
            if (copy)
            {
                memcpy(copy, str, len);
                copy[len] = '\0';
                return copy;
            }
        }
    }
    return NULL;
}

mjs_val_t mjs_val_from_attr(struct mjs *mjs, mp_obj_t base, qstr attr)
{
    mp_obj_t value = mp_load_attr(base, attr);
    if (value == MP_OBJ_NULL)
    {
        return MJS_UNDEFINED;
    }
    return mjs_val_from_mp_obj(mjs, value);
}

mjs_val_t mjs_val_from_mp_obj(struct mjs *mjs, mp_obj_t obj)
{
    if (obj == MP_OBJ_NULL || obj == mp_const_none)
    {
        return mjs_mk_undefined();
    }
    if (mp_obj_is_bool(obj))
    {
        return mjs_mk_boolean(mjs, mp_obj_is_true(obj));
    }
    if (mp_obj_is_int(obj))
    {
        return mjs_mk_number(mjs, (double)mp_obj_get_int(obj));
    }
    if (mp_obj_is_float(obj))
    {
        return mjs_mk_number(mjs, mp_obj_get_float(obj));
    }
    if (mp_obj_is_type(obj, &mp_type_tuple) || mp_obj_is_type(obj, &mp_type_list))
    {
        mp_obj_iter_buf_t iter_buf;
        mp_obj_t iterable = mp_getiter(obj, &iter_buf);
        mp_obj_t item;
        mjs_val_t arr = mjs_mk_array(mjs);
        size_t index = 0;
        while ((item = mp_iternext(iterable)) != MP_OBJ_STOP_ITERATION)
        {
            mjs_val_t val = mjs_val_from_mp_obj(mjs, item);
            mjs_array_set(mjs, arr, index++, val);
        }
        return arr;
    }
    if (mp_obj_is_type(obj, &mp_type_dict))
    {
        mp_obj_dict_t *dict = static_cast<mp_obj_dict_t *>(MP_OBJ_TO_PTR(obj));
        mjs_val_t obj_val = mjs_mk_object(mjs);
        for (size_t i = 0; i < dict->map.alloc; i++)
        {
            if (dict->map.table[i].key != MP_OBJ_NULL)
            {
                const char *key_str = mp_obj_str_get_str(dict->map.table[i].key);
                mjs_val_t val = mjs_val_from_mp_obj(mjs, dict->map.table[i].value);
                mjs_set(mjs, obj_val, key_str, strlen(key_str), val);
            }
        }
        return obj_val;
    }
    const char *value = mp_obj_str_get_str(obj);
    return mjs_mk_string(mjs, value, strlen(value), 1);
}

mp_obj_t mjs_val_to_mp_obj(struct mjs *mjs, mjs_val_t val)
{
    if (mjs_is_null(val) || mjs_is_undefined(val))
    {
        return mp_const_none;
    }
    if (mjs_is_boolean(val))
    {
        return mp_obj_new_bool(mjs_get_bool(mjs, val));
    }
    if (mjs_is_number(val))
    {
        double d = mjs_get_double(mjs, val);
        if (d == (double)(int)d)
        {
            return mp_obj_new_int((int)d);
        }
        return mp_obj_new_float(d);
    }
    if (mjs_is_object(val))
    {
        mp_obj_t dict_obj = mp_obj_new_dict(0);
        mjs_val_t key, iter = MJS_UNDEFINED;
        while ((key = mjs_next(mjs, val, &iter)) != MJS_UNDEFINED)
        {
            size_t key_len;
            const char *key_str = mjs_get_string(mjs, &key, &key_len);
            mjs_val_t value = mjs_get(mjs, val, key_str, key_len);
            mp_obj_dict_store(dict_obj, mp_obj_new_str(key_str, key_len), mjs_val_to_mp_obj(mjs, value));
        }
        return dict_obj;
    }
    if (mjs_is_array_buf(val))
    {
        size_t len;
        void *buf = (void *)mjs_array_buf_get_ptr(mjs, val, &len);
        return mp_obj_new_bytearray_by_ref(len, buf);
    }
    size_t len;
    const char *str = mjs_get_string(mjs, &val, &len);
    if (str != NULL)
    {
        return mp_obj_new_str(str, len);
    }
    return mp_const_none;
}

uint16_t mjs_get_color(struct mjs *mjs, mjs_val_t value)
{
    if (mjs_is_null(value) || mjs_is_undefined(value))
    {
        return 0x0000;
    }
    if (mjs_is_number(value))
    {
        return static_cast<uint16_t>(mjs_get_double(mjs, value));
    }
    if (mjs_is_string(value))
    {
        size_t len;
        const char *str = mjs_get_string(mjs, &value, &len);
        return static_cast<uint16_t>(color_parse_str(str));
    }
    return 0x0000;
}

float mjs_get_float(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t val = mjs_arg(mjs, arg);
    if (mjs_is_null(val) || mjs_is_undefined(val) || !mjs_is_number(val))
    {
        return 0.0;
    }
    return (float)mjs_get_double(mjs, val);
}

bool mjs_get_boolean(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t val = mjs_arg(mjs, arg);
    if (mjs_is_null(val) || mjs_is_undefined(val) || !mjs_is_boolean(val))
    {
        return false;
    }
    return mjs_get_bool(mjs, val);
}

mjs_val_t mjs_mk_vector(struct mjs *mjs, float x, float y, float z)
{
    mjs_val_t vector_obj = mjs_mk_object(mjs);
    mjs_set(mjs, vector_obj, "x", ~0, mjs_mk_number(mjs, (double)x));
    mjs_set(mjs, vector_obj, "y", ~0, mjs_mk_number(mjs, (double)y));
    mjs_set(mjs, vector_obj, "z", ~0, mjs_mk_number(mjs, (double)z));
    return vector_obj;
}

bool mjs_get_vector(struct mjs *mjs, uint8_t arg, float *x, float *y, float *z)
{
    mjs_val_t val = mjs_arg(mjs, arg);
    if (mjs_is_null(val) || mjs_is_undefined(val) || !mjs_is_object(val))
    {
        return false;
    }
    mjs_val_t x_val = mjs_get(mjs, val, "x", ~0);
    mjs_val_t y_val = mjs_get(mjs, val, "y", ~0);
    mjs_val_t z_val = mjs_get(mjs, val, "z", ~0);
    *x = (float)mjs_get_double(mjs, x_val);
    *y = (float)mjs_get_double(mjs, y_val);
    *z = (float)mjs_get_double(mjs, z_val);
    return true;
}

void mjs_input_buffer_free(mjs_input_buffer *buffer)
{
    if (buffer->owned_data)
        m_free(buffer->owned_data);
    buffer->data = nullptr;
    buffer->length = 0;
    buffer->owned_data = nullptr;
}

bool mjs_read_buffer(struct mjs *mjs, mjs_val_t value, size_t expected_length,
                     bool exact_length, const char *name, mjs_input_buffer *buffer)
{
    if (mjs_is_array_buf(value))
    {
        buffer->data = static_cast<const uint8_t *>(mjs_array_buf_get_ptr(mjs, value, &buffer->length));
        if (buffer->length < expected_length || (exact_length && buffer->length != expected_length))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "incorrect image %s length", name);
            return false;
        }
        if (!buffer->data)
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "image %s buffer is null", name);
            return false;
        }
        return true;
    }

    if (!mjs_is_array(value))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "image %s must be an array or ArrayBuffer", name);
        return false;
    }

    const unsigned long array_length = mjs_array_length(mjs, value);
    if (array_length < expected_length || (exact_length && array_length != expected_length))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "incorrect image %s length", name);
        return false;
    }

    buffer->owned_data = static_cast<uint8_t *>(m_malloc0(expected_length));
    if (!buffer->owned_data)
    {
        mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "unable to allocate image %s", name);
        return false;
    }
    buffer->data = buffer->owned_data;
    buffer->length = expected_length;

    for (size_t i = 0; i < expected_length; i++)
    {
        mjs_val_t item = mjs_array_get(mjs, value, static_cast<unsigned long>(i));
        if (mjs_is_number(item))
        {
            const double byte = mjs_get_double(mjs, item);
            if (!isfinite(byte) || byte < 0 || byte > 255 || byte != static_cast<uint8_t>(byte))
            {
                mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "image %s values must be integers from 0 to 255", name);
                mjs_input_buffer_free(buffer);
                return false;
            }
            buffer->owned_data[i] = static_cast<uint8_t>(byte);
        }
        else if (mjs_is_string(item))
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &item, &len);
            uint32_t _color = color_parse_str(str);
            buffer->owned_data[i] = static_cast<uint8_t>(_color & 0xFF);
        }
        else
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "image %s values must be numbers (0 to 255) or strings", name);
            mjs_input_buffer_free(buffer);
            return false;
        }
    }

    return true;
}