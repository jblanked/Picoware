#include "psram.h"
#include "array_buf.h"
#include "color.h"

static mp_obj_t psram_mp_instance;

static mp_obj_t psram_parse_mp_int(struct mjs *mjs, mjs_val_t val)
{
    uint32_t uval;
    if (mjs_is_number(val))
    {
        uval = (uint32_t)mjs_get_double(mjs, val);
    }
    else if (mjs_is_string(val))
    {
        size_t len;
        const char *str = mjs_get_string(mjs, &val, &len);
        uval = color_parse_str(str);
    }
    else
    {
        return mp_obj_new_int(0);
    }
    return mp_obj_new_int((mp_int_t)(int32_t)uval);
}

static void psram_call_0(struct mjs *mjs, const char *attr)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, mp_obj_str_get_qstr(mp_obj_new_str(attr, strlen(attr))));
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result = mp_call_function_0(func);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static mjs_val_t psram_free_heap_size(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, psram_mp_instance, MP_QSTR_free_heap_size);
}

static mjs_val_t psram_next_free_addr(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, psram_mp_instance, MP_QSTR_next_free_addr);
}

static mjs_val_t psram_total_heap_size(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, psram_mp_instance, MP_QSTR_total_heap_size);
}

static mjs_val_t psram_used_heap_size(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, psram_mp_instance, MP_QSTR_used_heap_size);
}

static void psram_is_ready(struct mjs *mjs)
{
    psram_call_0(mjs, "is_ready");
}

static void psram_size(struct mjs *mjs)
{
    psram_call_0(mjs, "size");
}

static void psram_test(struct mjs *mjs)
{
    psram_call_0(mjs, "test");
}

static void psram_get_next_free(struct mjs *mjs)
{
    psram_call_0(mjs, "get_next_free");
}

static void psram_mem_free(struct mjs *mjs)
{
    psram_call_0(mjs, "mem_free");
}

static void psram_collect(struct mjs *mjs)
{
    psram_call_0(mjs, "collect");
}

static void psram_read_result(struct mjs *mjs, mp_obj_t result)
{
    if (mp_obj_is_int(result))
    {
        uint32_t uval = (uint32_t)mp_obj_get_int_truncated(result);
        mjs_return(mjs, mjs_mk_number(mjs, (double)uval));
        return;
    }
    mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
}

static void psram_read8(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_read8);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t result = mp_call_function_1(func, arg);
        psram_read_result(mjs, result);
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_read16(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_read16);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t result = mp_call_function_1(func, arg);
        psram_read_result(mjs, result);
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_read32(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_read32);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t result = mp_call_function_1(func, arg);
        psram_read_result(mjs, result);
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_read(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_read);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = psram_parse_mp_int(mjs, mjs_arg(mjs, 1));
        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        psram_read_result(mjs, result);
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_write8(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_write8);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = psram_parse_mp_int(mjs, mjs_arg(mjs, 1));
        mp_obj_t args[2] = {arg1, arg2};
        mp_call_function_n_kw(func, 2, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_write16(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_write16);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = psram_parse_mp_int(mjs, mjs_arg(mjs, 1));
        mp_obj_t args[2] = {arg1, arg2};
        mp_call_function_n_kw(func, 2, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_write32(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_write32);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = psram_parse_mp_int(mjs, mjs_arg(mjs, 1));
        mp_obj_t args[2] = {arg1, arg2};
        mp_call_function_n_kw(func, 2, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_write(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_write);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));

        mjs_val_t data_val = mjs_arg(mjs, 1);
        mp_obj_t arg2;
        if (mjs_is_array_buf(data_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, data_val, &len);
            arg2 = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &data_val, &len);
            arg2 = mp_obj_new_str(str, len);
        }

        mp_obj_t args[2] = {arg1, arg2};
        mp_call_function_n_kw(func, 2, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_mp_data_to_mjs_obj(struct mjs *mjs, mp_obj_t data)
{
    mjs_val_t obj = mjs_mk_object(mjs);

    mp_obj_t val_func = mp_load_attr(data, MP_QSTR_value);
    if (val_func != MP_OBJ_NULL && mp_obj_is_callable(val_func))
    {
        mp_obj_t val = mp_call_function_0(val_func);
        mjs_set(mjs, obj, "value", ~0, mjs_val_from_mp_obj(mjs, val));
    }

    mp_obj_t addr_func = mp_load_attr(data, MP_QSTR_addr);
    if (addr_func != MP_OBJ_NULL && mp_obj_is_callable(addr_func))
    {
        mp_obj_t val = mp_call_function_0(addr_func);
        mjs_set(mjs, obj, "addr", ~0, mjs_val_from_mp_obj(mjs, val));
    }

    mp_obj_t len_func = mp_load_attr(data, MP_QSTR_length);
    if (len_func != MP_OBJ_NULL && mp_obj_is_callable(len_func))
    {
        mp_obj_t val = mp_call_function_0(len_func);
        mjs_set(mjs, obj, "length", ~0, mjs_val_from_mp_obj(mjs, val));
    }

    mjs_return(mjs, obj);
}

static void psram_alloc_object(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_alloc_object);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t data_val = mjs_arg(mjs, 0);
        mp_obj_t arg;
        if (mjs_is_number(data_val) || mjs_is_boolean(data_val))
        {
            arg = mjs_val_to_mp_obj(mjs, data_val);
        }
        else if (mjs_is_array_buf(data_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, data_val, &len);
            arg = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &data_val, &len);
            arg = mp_obj_new_str(str, len);
        }

        mp_obj_t result = mp_call_function_1(func, arg);
        psram_mp_data_to_mjs_obj(mjs, result);
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_malloc(struct mjs *mjs)
{
    psram_alloc_object(mjs);
}

static void psram_fill(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_fill);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = psram_parse_mp_int(mjs, mjs_arg(mjs, 1));
        mp_obj_t arg3 = psram_parse_mp_int(mjs, mjs_arg(mjs, 2));
        mp_obj_t args[3] = {arg1, arg2, arg3};
        mp_call_function_n_kw(func, 3, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_memset(struct mjs *mjs)
{
    psram_fill(mjs);
}

static void psram_copy(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_copy);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = psram_parse_mp_int(mjs, mjs_arg(mjs, 1));
        mp_obj_t arg3 = psram_parse_mp_int(mjs, mjs_arg(mjs, 2));
        mp_obj_t args[3] = {arg1, arg2, arg3};
        mp_call_function_n_kw(func, 3, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_memcpy(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_memcpy);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = psram_parse_mp_int(mjs, mjs_arg(mjs, 1));
        mp_obj_t arg3 = psram_parse_mp_int(mjs, mjs_arg(mjs, 2));
        mp_obj_t args[3] = {arg1, arg2, arg3};
        mp_call_function_n_kw(func, 3, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_write32_bulk(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_write32_bulk);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));

        mjs_val_t data_val = mjs_arg(mjs, 1);
        mp_obj_t arg2;
        if (mjs_is_array_buf(data_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, data_val, &len);
            arg2 = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &data_val, &len);
            arg2 = mp_obj_new_str(str, len);
        }

        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void psram_read32_bulk(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(psram_mp_instance, MP_QSTR_read32_bulk);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = psram_parse_mp_int(mjs, mjs_arg(mjs, 0));

        mjs_val_t buf_val = mjs_arg(mjs, 1);
        mp_obj_t arg2;
        if (mjs_is_array_buf(buf_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, buf_val, &len);
            arg2 = mp_obj_new_bytearray(len, buf);
        }
        else
        {
            arg2 = mp_const_none;
        }

        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

void psram_create(struct mjs *mjs, mjs_val_t *psram_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    mp_obj_t import_name = mp_obj_new_str("picoware.system.psram", strlen("picoware.system.psram"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_PSRAM));
    mp_obj_t psram_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t psram_mp_class = mp_load_attr(psram_mod, MP_QSTR_PSRAM);
    psram_mp_instance = mp_call_function_0(psram_mp_class);

    *psram_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *psram_obj, "freeHeapSize", ~0, psram_free_heap_size);
    mjs_set_getter(mjs, *psram_obj, "nextFreeAddr", ~0, psram_next_free_addr);
    mjs_set_getter(mjs, *psram_obj, "totalHeapSize", ~0, psram_total_heap_size);
    mjs_set_getter(mjs, *psram_obj, "usedHeapSize", ~0, psram_used_heap_size);

    mjs_set(mjs, *psram_obj, "isReady", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_is_ready));
    mjs_set(mjs, *psram_obj, "size", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_size));
    mjs_set(mjs, *psram_obj, "test", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_test));
    mjs_set(mjs, *psram_obj, "write", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_write));
    mjs_set(mjs, *psram_obj, "write8", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_write8));
    mjs_set(mjs, *psram_obj, "write16", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_write16));
    mjs_set(mjs, *psram_obj, "write32", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_write32));
    mjs_set(mjs, *psram_obj, "write32Bulk", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_write32_bulk));
    mjs_set(mjs, *psram_obj, "read", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_read));
    mjs_set(mjs, *psram_obj, "read8", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_read8));
    mjs_set(mjs, *psram_obj, "read16", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_read16));
    mjs_set(mjs, *psram_obj, "read32", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_read32));
    mjs_set(mjs, *psram_obj, "read32Bulk", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_read32_bulk));
    mjs_set(mjs, *psram_obj, "fill", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_fill));
    mjs_set(mjs, *psram_obj, "copy", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_copy));
    mjs_set(mjs, *psram_obj, "allocObject", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_alloc_object));
    mjs_set(mjs, *psram_obj, "getNextFree", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_get_next_free));
    mjs_set(mjs, *psram_obj, "memFree", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_mem_free));
    mjs_set(mjs, *psram_obj, "collect", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_collect));
    mjs_set(mjs, *psram_obj, "malloc", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_malloc));
    mjs_set(mjs, *psram_obj, "memcpy", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_memcpy));
    mjs_set(mjs, *psram_obj, "memset", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)psram_memset));

    nlr_pop();
}

void psram_destroy()
{
    psram_mp_instance = MP_OBJ_NULL;
}