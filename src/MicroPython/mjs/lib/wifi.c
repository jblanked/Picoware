#include "wifi.h"

static mp_obj_t wifi_mp_instance;

static void wifi_connect(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(wifi_mp_instance, MP_QSTR_connect);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        // ssid (str), password (str), sta_mode (bool, defaults to true)
        mp_obj_t arg1 = mjs_val_to_mp_obj(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = mjs_val_to_mp_obj(mjs, mjs_arg(mjs, 1));
        mjs_val_t arg3_val = mjs_arg(mjs, 2);
        mp_obj_t arg3 = mjs_is_undefined(arg3_val) ? mp_const_true : mjs_val_to_mp_obj(mjs, arg3_val);
        mp_obj_t args[3] = {arg1, arg2, arg3};
        mp_obj_t results = mp_call_function_n_kw(func, 3, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, results));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void wifi_connect_async(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(wifi_mp_instance, MP_QSTR_connect_async);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        // ssid (str), password (str), sta_mode (bool, defaults to true)
        mp_obj_t arg1 = mjs_val_to_mp_obj(mjs, mjs_arg(mjs, 0));
        mp_obj_t arg2 = mjs_val_to_mp_obj(mjs, mjs_arg(mjs, 1));
        mjs_val_t arg3_val = mjs_arg(mjs, 2);
        mp_obj_t arg3 = mjs_is_undefined(arg3_val) ? mp_const_true : mjs_val_to_mp_obj(mjs, arg3_val);
        mp_obj_t args[3] = {arg1, arg2, arg3};
        mp_obj_t results = mp_call_function_n_kw(func, 3, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, results));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void wifi_disconnect(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(wifi_mp_instance, MP_QSTR_disconnect);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void wifi_is_connected(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(wifi_mp_instance, MP_QSTR_is_connected);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result = mp_call_function_0(func);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void wifi_reset(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(wifi_mp_instance, MP_QSTR_reset);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void wifi_scan(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(wifi_mp_instance, MP_QSTR_scan);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t results = mp_call_function_0(func);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, results));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static mjs_val_t wifi_device_ip(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, wifi_mp_instance, MP_QSTR_device_ip);
}

static mjs_val_t wifi_last_error(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, wifi_mp_instance, MP_QSTR_last_error);
}

static mjs_val_t wifi_mac_address(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, wifi_mp_instance, MP_QSTR_mac_address);
}

static mjs_val_t wifi_state(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, wifi_mp_instance, MP_QSTR_state);
}

static mjs_val_t wifi_timeout(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, wifi_mp_instance, MP_QSTR_timeout);
}

void wifi_create(struct mjs *mjs, mjs_val_t *wifi_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    mp_obj_t import_name = mp_obj_new_str("picoware.system.wifi", strlen("picoware.system.wifi"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_WiFi));
    mp_obj_t wifi_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t wifi_mp_class = mp_load_attr(wifi_mod, MP_QSTR_WiFi);
    wifi_mp_instance = mp_call_function_0(wifi_mp_class);

    *wifi_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *wifi_obj, "deviceIp", ~0, wifi_device_ip);
    mjs_set_getter(mjs, *wifi_obj, "lastError", ~0, wifi_last_error);
    mjs_set_getter(mjs, *wifi_obj, "macAddress", ~0, wifi_mac_address);
    mjs_set_getter(mjs, *wifi_obj, "state", ~0, wifi_state);
    mjs_set_getter(mjs, *wifi_obj, "timeout", ~0, wifi_timeout);
    //
    mjs_set(mjs, *wifi_obj, "connect", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)wifi_connect));
    mjs_set(mjs, *wifi_obj, "connectAsync", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)wifi_connect_async));
    mjs_set(mjs, *wifi_obj, "disconnect", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)wifi_disconnect));
    mjs_set(mjs, *wifi_obj, "isConnected", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)wifi_is_connected));
    mjs_set(mjs, *wifi_obj, "reset", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)wifi_reset));
    mjs_set(mjs, *wifi_obj, "scan", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)wifi_scan));

    nlr_pop();
}

void wifi_destroy()
{
    wifi_mp_instance = MP_OBJ_NULL;
}