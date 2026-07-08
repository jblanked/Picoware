#include "mjs.h"
#include "array_buf.h"

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
        mp_obj_dict_t *dict = MP_OBJ_TO_PTR(obj);
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