#include "system.h"
#include <string.h>
#include "py/runtime.h"

static mp_obj_t system_mp_instance;

static mjs_val_t system_board_id(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_board_id);
}

static mjs_val_t system_board_name(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_board_name);
}

static mjs_val_t system_device_name(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_device_name);
}

static mjs_val_t system_free_psram(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_free_psram);
}

static mjs_val_t system_free_heap(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_free_heap);
}

static mjs_val_t system_freq(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_freq);
}

static mjs_val_t system_has_audio(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_has_audio);
}

static mjs_val_t system_has_psram(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_has_psram);
}

static mjs_val_t system_has_sd_card(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_has_sd_card);
}

static mjs_val_t system_has_touch(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_has_touch);
}

static mjs_val_t system_has_wifi(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_has_wifi);
}

static mjs_val_t system_is_circular(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_is_circular);
}

static mjs_val_t system_free_flash(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_free_flash);
}

static mjs_val_t system_total_flash(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_total_flash);
}

static mjs_val_t system_total_heap(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_total_heap);
}

static mjs_val_t system_total_psram(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_total_psram);
}

static mjs_val_t system_used_heap(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_used_heap);
}

static mjs_val_t system_used_psram(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_used_psram);
}

static mjs_val_t system_version(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, system_mp_instance, MP_QSTR_version);
}

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

    mjs_set_getter(mjs, *system_obj, "board_id", ~0, system_board_id);
    mjs_set_getter(mjs, *system_obj, "board_name", ~0, system_board_name);
    mjs_set_getter(mjs, *system_obj, "device_name", ~0, system_device_name);
    mjs_set_getter(mjs, *system_obj, "free_psram", ~0, system_free_psram);
    mjs_set_getter(mjs, *system_obj, "free_heap", ~0, system_free_heap);
    mjs_set_getter(mjs, *system_obj, "freq", ~0, system_freq);
    mjs_set_getter(mjs, *system_obj, "has_audio", ~0, system_has_audio);
    mjs_set_getter(mjs, *system_obj, "has_psram", ~0, system_has_psram);
    mjs_set_getter(mjs, *system_obj, "has_sd_card", ~0, system_has_sd_card);
    mjs_set_getter(mjs, *system_obj, "has_touch", ~0, system_has_touch);
    mjs_set_getter(mjs, *system_obj, "has_wifi", ~0, system_has_wifi);
    mjs_set_getter(mjs, *system_obj, "is_circular", ~0, system_is_circular);
    mjs_set_getter(mjs, *system_obj, "free_flash", ~0, system_free_flash);
    mjs_set_getter(mjs, *system_obj, "total_flash", ~0, system_total_flash);
    mjs_set_getter(mjs, *system_obj, "total_heap", ~0, system_total_heap);
    mjs_set_getter(mjs, *system_obj, "total_psram", ~0, system_total_psram);
    mjs_set_getter(mjs, *system_obj, "used_heap", ~0, system_used_heap);
    mjs_set_getter(mjs, *system_obj, "used_psram", ~0, system_used_psram);
    mjs_set_getter(mjs, *system_obj, "version", ~0, system_version);
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