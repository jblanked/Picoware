#include "system.h"
#include <string.h>
#include "py/runtime.h"

static mp_obj_t system_mp_instance;

static void system_bootloader_mode(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(system_mp_instance, MP_QSTR_bootloader_mode);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void system_hard_reset(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(system_mp_instance, MP_QSTR_hard_reset);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void system_soft_reset(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(system_mp_instance, MP_QSTR_soft_reset);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static mjs_val_t system_string(struct mjs *mjs, mp_obj_t base, qstr attr)
{
    mp_obj_t value = mp_load_attr(base, attr);
    if (value == MP_OBJ_NULL)
    {
        return mjs_mk_string(mjs, "", 0, 1);
    }
    const char *str = mp_obj_str_get_str(value);
    return mjs_mk_string(mjs, str, strlen(str), 1);
}

static mjs_val_t system_int(struct mjs *mjs, mp_obj_t base, qstr attr)
{
    mp_obj_t value = mp_load_attr(base, attr);
    if (value == MP_OBJ_NULL)
    {
        return mjs_mk_number(mjs, 0);
    }
    return mjs_mk_number(mjs, mp_obj_is_float(value) ? (double)mp_obj_get_float(value) : (double)mp_obj_get_int(value));
}

static mjs_val_t system_bool(struct mjs *mjs, mp_obj_t base, qstr attr)
{
    mp_obj_t value = mp_load_attr(base, attr);
    if (value == MP_OBJ_NULL || !mp_obj_is_bool(value))
    {
        return mjs_mk_boolean(mjs, false);
    }
    return mjs_mk_boolean(mjs, mp_obj_is_true(value));
}

void system_create(struct mjs *mjs, mjs_val_t *system_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    // from picoware.system.system import System
    mp_obj_t import_name = mp_obj_new_str("picoware.system.system", strlen("picoware.system.system"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_System));
    mp_obj_t system_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t system_mp_class = mp_load_attr(system_mod, MP_QSTR_System);
    system_mp_instance = mp_call_function_0(system_mp_class);

    *system_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *system_obj, "board_id", ~0, system_int(mjs, system_mp_instance, MP_QSTR_board_id));
    mjs_set(mjs, *system_obj, "board_name", ~0, system_string(mjs, system_mp_instance, MP_QSTR_board_name));
    mjs_set(mjs, *system_obj, "device_name", ~0, system_string(mjs, system_mp_instance, MP_QSTR_device_name));
    mjs_set(mjs, *system_obj, "free_psram", ~0, system_int(mjs, system_mp_instance, MP_QSTR_free_psram));
    mjs_set(mjs, *system_obj, "free_heap", ~0, system_int(mjs, system_mp_instance, MP_QSTR_free_heap));
    mjs_set(mjs, *system_obj, "freq", ~0, system_int(mjs, system_mp_instance, MP_QSTR_freq));
    mjs_set(mjs, *system_obj, "has_audio", ~0, system_bool(mjs, system_mp_instance, MP_QSTR_has_audio));
    mjs_set(mjs, *system_obj, "has_psram", ~0, system_bool(mjs, system_mp_instance, MP_QSTR_has_psram));
    mjs_set(mjs, *system_obj, "has_sd_card", ~0, system_bool(mjs, system_mp_instance, MP_QSTR_has_sd_card));
    mjs_set(mjs, *system_obj, "has_touch", ~0, system_bool(mjs, system_mp_instance, MP_QSTR_has_touch));
    mjs_set(mjs, *system_obj, "has_wifi", ~0, system_bool(mjs, system_mp_instance, MP_QSTR_has_wifi));
    mjs_set(mjs, *system_obj, "is_circular", ~0, system_bool(mjs, system_mp_instance, MP_QSTR_is_circular));
    mjs_set(mjs, *system_obj, "free_flash", ~0, system_int(mjs, system_mp_instance, MP_QSTR_free_flash));
    mjs_set(mjs, *system_obj, "total_flash", ~0, system_int(mjs, system_mp_instance, MP_QSTR_total_flash));
    mjs_set(mjs, *system_obj, "total_heap", ~0, system_int(mjs, system_mp_instance, MP_QSTR_total_heap));
    mjs_set(mjs, *system_obj, "total_psram", ~0, system_int(mjs, system_mp_instance, MP_QSTR_total_psram));
    mjs_set(mjs, *system_obj, "used_heap", ~0, system_int(mjs, system_mp_instance, MP_QSTR_used_heap));
    mjs_set(mjs, *system_obj, "used_psram", ~0, system_int(mjs, system_mp_instance, MP_QSTR_used_psram));
    mjs_set(mjs, *system_obj, "version", ~0, system_string(mjs, system_mp_instance, MP_QSTR_version));
    //
    mjs_set(mjs, *system_obj, "bootloader_mode", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)system_bootloader_mode));
    mjs_set(mjs, *system_obj, "hard_reset", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)system_hard_reset));
    mjs_set(mjs, *system_obj, "soft_reset", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)system_soft_reset));

    nlr_pop();
}

void system_destroy()
{
    system_mp_instance = MP_OBJ_NULL;
}