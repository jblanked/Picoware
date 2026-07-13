#include "bluetooth.h"
#include "array_buf.h"

static mp_obj_t bluetooth_mp_instance;

static mjs_val_t bluetooth_on_write_cb = MJS_UNDEFINED;
static mjs_val_t bluetooth_on_notify_cb = MJS_UNDEFINED;
static mjs_val_t bluetooth_on_scan_cb = MJS_UNDEFINED;

static mjs_val_t bluetooth_mac_address(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_mac_address);
}

static mjs_val_t bluetooth_connected_address(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_connected_address);
}

static mjs_val_t bluetooth_is_pairing(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_is_pairing);
}

static mjs_val_t bluetooth_is_scanning(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_is_scanning);
}

static mjs_val_t bluetooth_is_connected(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_is_connected);
}

static mjs_val_t bluetooth_is_peripheral_connected(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_is_peripheral_connected);
}

static mjs_val_t bluetooth_passkey(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_passkey);
}

static mjs_val_t bluetooth_services(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_services);
}

static mjs_val_t bluetooth_characteristics(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, bluetooth_mp_instance, MP_QSTR_characteristics);
}

static void bluetooth_call_0(struct mjs *mjs, const char *attr)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, mp_obj_str_get_qstr(mp_obj_new_str(attr, strlen(attr))));
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result = mp_call_function_0(func);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_advertise(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_advertise);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg1_val = mjs_arg(mjs, 0);
        mjs_val_t arg2_val = mjs_arg(mjs, 1);
        mp_obj_t arg1, arg2;

        if (mjs_is_undefined(arg1_val) || mjs_is_null(arg1_val))
        {
            arg1 = mp_const_none;
        }
        else
        {
            arg1 = mp_obj_new_int((int)mjs_get_double(mjs, arg1_val));
        }

        if (mjs_is_undefined(arg2_val))
        {
            arg2 = mp_obj_new_str("Picoware", strlen("Picoware"));
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &arg2_val, &len);
            arg2 = mp_obj_new_str(str, len);
        }

        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_connect(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_connect);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = mp_obj_new_int((int)mjs_get_double(mjs, mjs_arg(mjs, 0)));

        mjs_val_t addr_val = mjs_arg(mjs, 1);
        mp_obj_t arg2;
        if (mjs_is_array_buf(addr_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, addr_val, &len);
            arg2 = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &addr_val, &len);
            if (str)
            {
                uint8_t *bytes = (uint8_t *)m_malloc(6);
                int count = 0;
                const char *p = str;
                while (*p && count < 6)
                {
                    if (*p >= '0' && *p <= '9')
                    {
                        bytes[count] = bytes[count] * 16 + (*p - '0');
                    }
                    else if (*p >= 'A' && *p <= 'F')
                    {
                        bytes[count] = bytes[count] * 16 + (*p - 'A' + 10);
                    }
                    else if (*p >= 'a' && *p <= 'f')
                    {
                        bytes[count] = bytes[count] * 16 + (*p - 'a' + 10);
                    }
                    else if (*p == ':')
                    {
                        count++;
                    }
                    p++;
                }
                arg2 = mp_obj_new_bytes(bytes, 6);
                m_free(bytes);
            }
            else
            {
                arg2 = mp_const_none;
            }
        }

        mjs_val_t arg3_val = mjs_arg(mjs, 2);
        mp_obj_t arg3 = mjs_is_undefined(arg3_val) ? mp_obj_new_int(10000) : mp_obj_new_int((int)mjs_get_double(mjs, arg3_val));

        mjs_val_t arg4_val = mjs_arg(mjs, 3);
        mp_obj_t arg4 = mjs_is_undefined(arg4_val) ? mp_const_true : (mjs_get_bool(mjs, arg4_val) ? mp_const_true : mp_const_false);

        mp_obj_t args[4] = {arg1, arg2, arg3, arg4};
        mp_obj_t result = mp_call_function_n_kw(func, 4, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_decode_name(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_decode_name);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg_val = mjs_arg(mjs, 0);
        mp_obj_t arg;
        if (mjs_is_array_buf(arg_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, arg_val, &len);
            arg = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &arg_val, &len);
            arg = mp_obj_new_str(str, len);
        }
        mp_obj_t result = mp_call_function_1(func, arg);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_decode_services(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_decode_services);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg_val = mjs_arg(mjs, 0);
        mp_obj_t arg;
        if (mjs_is_array_buf(arg_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, arg_val, &len);
            arg = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &arg_val, &len);
            arg = mp_obj_new_str(str, len);
        }
        mp_obj_t result = mp_call_function_1(func, arg);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_disconnect(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_disconnect);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg_val = mjs_arg(mjs, 0);
        if (mjs_is_undefined(arg_val))
        {
            mp_call_function_0(func);
        }
        else
        {
            mp_obj_t arg = mjs_is_null(arg_val) ? mp_const_none : mp_obj_new_int((int)mjs_get_double(mjs, arg_val));
            mp_call_function_1(func, arg);
        }
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_discover_characteristics(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_discover_characteristics);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg1 = mp_obj_new_int((int)mjs_get_double(mjs, mjs_arg(mjs, 0)));
        mp_obj_t arg2 = mp_obj_new_int((int)mjs_get_double(mjs, mjs_arg(mjs, 1)));
        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_discover_services(struct mjs *mjs)
{
    bluetooth_call_0(mjs, "discover_services");
}

static void bluetooth_is_device_paired(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_is_device_paired);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        size_t len;
        mjs_val_t arg_val = mjs_arg(mjs, 0);
        const char *str = mjs_get_string(mjs, &arg_val, &len);
        mp_obj_t arg = mp_obj_new_str(str, len);
        mp_obj_t result = mp_call_function_1(func, arg);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_is_uart_ready(struct mjs *mjs)
{
    bluetooth_call_0(mjs, "is_uart_ready");
}

static void bluetooth_load_paired_devices(struct mjs *mjs)
{
    bluetooth_call_0(mjs, "load_paired_devices");
}

static void bluetooth_pair(struct mjs *mjs)
{
    bluetooth_call_0(mjs, "pair");
}

static void bluetooth_passkey_reply(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_passkey_reply);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg1_val = mjs_arg(mjs, 0);
        mjs_val_t arg2_val = mjs_arg(mjs, 1);

        mp_obj_t arg1 = mjs_is_undefined(arg1_val) ? mp_const_true : (mjs_get_bool(mjs, arg1_val) ? mp_const_true : mp_const_false);
        mp_obj_t arg2 = mjs_is_undefined(arg2_val) ? mp_obj_new_int(0) : mp_obj_new_int((int)mjs_get_double(mjs, arg2_val));

        mp_obj_t args[2] = {arg1, arg2};
        mp_call_function_n_kw(func, 2, 0, args);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_read(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_read);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t arg = mp_obj_new_int((int)mjs_get_double(mjs, mjs_arg(mjs, 0)));
        mp_obj_t result = mp_call_function_1(func, arg);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_register(struct mjs *mjs)
{
    bluetooth_call_0(mjs, "register");
}

static void bluetooth_remove_paired_device(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_remove_paired_device);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        size_t len;
        mjs_val_t arg_val = mjs_arg(mjs, 0);
        const char *str = mjs_get_string(mjs, &arg_val, &len);
        mp_obj_t arg = mp_obj_new_str(str, len);
        mp_obj_t result = mp_call_function_1(func, arg);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_save_paired_device(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_save_paired_device);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        size_t len;
        mjs_val_t arg1_val = mjs_arg(mjs, 0);
        const char *str = mjs_get_string(mjs, &arg1_val, &len);
        mp_obj_t arg1 = mp_obj_new_str(str, len);

        mjs_val_t arg2_val = mjs_arg(mjs, 1);
        mp_obj_t arg2;
        if (mjs_is_undefined(arg2_val))
        {
            arg2 = mp_obj_new_str("", 0);
        }
        else
        {
            size_t len2;
            const char *str2 = mjs_get_string(mjs, &arg2_val, &len2);
            arg2 = mp_obj_new_str(str2, len2);
        }

        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_scan(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_scan);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg1_val = mjs_arg(mjs, 0);
        mjs_val_t arg2_val = mjs_arg(mjs, 1);
        mjs_val_t arg3_val = mjs_arg(mjs, 2);
        mjs_val_t arg4_val = mjs_arg(mjs, 3);
        // mjs_val_t arg5_val = mjs_arg(mjs, 4); (callback, unsupported right now..)

        mp_obj_t arg1 = mjs_is_undefined(arg1_val) ? mp_obj_new_int(5000) : mp_obj_new_int((int)mjs_get_double(mjs, arg1_val));
        mp_obj_t arg2 = mjs_is_undefined(arg2_val) ? mp_obj_new_int(30000) : mp_obj_new_int((int)mjs_get_double(mjs, arg2_val));
        mp_obj_t arg3 = mjs_is_undefined(arg3_val) ? mp_obj_new_int(30000) : mp_obj_new_int((int)mjs_get_double(mjs, arg3_val));
        mp_obj_t arg4 = mjs_is_undefined(arg4_val) ? mp_const_true : (mjs_get_bool(mjs, arg4_val) ? mp_const_true : mp_const_false);
        mp_obj_t arg5 = mp_const_none;

        mp_obj_t args[5] = {arg1, arg2, arg3, arg4, arg5};
        mp_obj_t result = mp_call_function_n_kw(func, 5, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_scan_for_uart_devices(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_scan_for_uart_devices);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg2_val = mjs_arg(mjs, 1);
        mp_obj_t arg1 = mp_const_none;
        mp_obj_t arg2 = mjs_is_undefined(arg2_val) ? mp_obj_new_int(5000) : mp_obj_new_int((int)mjs_get_double(mjs, arg2_val));

        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_scan_stop(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_scan_stop);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_send(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_send);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg_val = mjs_arg(mjs, 0);
        mp_obj_t arg;
        if (mjs_is_array_buf(arg_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, arg_val, &len);
            arg = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &arg_val, &len);
            arg = mp_obj_new_str(str, len);
        }
        mp_obj_t result = mp_call_function_1(func, arg);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_start_peripheral(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_start_peripheral);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg1_val = mjs_arg(mjs, 0);
        mjs_val_t arg2_val = mjs_arg(mjs, 1);

        size_t len;
        const char *name_str;
        mp_obj_t arg1;
        if (mjs_is_undefined(arg1_val))
        {
            arg1 = mp_obj_new_str("Picoware", strlen("Picoware"));
        }
        else
        {
            name_str = mjs_get_string(mjs, &arg1_val, &len);
            arg1 = mp_obj_new_str(name_str, len);
        }

        mp_obj_t arg2 = mjs_is_undefined(arg2_val) ? mp_obj_new_int(500000) : mp_obj_new_int((int)mjs_get_double(mjs, arg2_val));

        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_stop_peripheral(struct mjs *mjs)
{
    bluetooth_call_0(mjs, "stop_peripheral");
}

static void bluetooth_subscribe(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_subscribe);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg1_val = mjs_arg(mjs, 0);
        mjs_val_t arg2_val = mjs_arg(mjs, 1);

        mp_obj_t arg1;
        if (mjs_is_undefined(arg1_val) || mjs_is_null(arg1_val))
        {
            arg1 = mp_const_none;
        }
        else
        {
            arg1 = mp_obj_new_int((int)mjs_get_double(mjs, arg1_val));
        }

        mp_obj_t arg2 = mjs_is_undefined(arg2_val) ? mp_const_true : (mjs_get_bool(mjs, arg2_val) ? mp_const_true : mp_const_false);

        mp_obj_t args[2] = {arg1, arg2};
        mp_obj_t result = mp_call_function_n_kw(func, 2, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_write(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(bluetooth_mp_instance, MP_QSTR_write);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t arg1_val = mjs_arg(mjs, 0);
        mp_obj_t arg1;
        if (mjs_is_array_buf(arg1_val))
        {
            size_t len;
            void *buf = (void *)mjs_array_buf_get_ptr(mjs, arg1_val, &len);
            arg1 = mp_obj_new_bytes(buf, len);
        }
        else
        {
            size_t len;
            const char *str = mjs_get_string(mjs, &arg1_val, &len);
            arg1 = mp_obj_new_str(str, len);
        }

        mjs_val_t arg2_val = mjs_arg(mjs, 1);
        mp_obj_t arg2;
        if (mjs_is_undefined(arg2_val) || mjs_is_null(arg2_val))
        {
            arg2 = mp_const_none;
        }
        else
        {
            arg2 = mp_obj_new_int((int)mjs_get_double(mjs, arg2_val));
        }

        mjs_val_t arg3_val = mjs_arg(mjs, 2);
        mp_obj_t arg3 = mjs_is_undefined(arg3_val) ? mp_const_false : (mjs_get_bool(mjs, arg3_val) ? mp_const_true : mp_const_false);

        mp_obj_t args[3] = {arg1, arg2, arg3};
        mp_obj_t result = mp_call_function_n_kw(func, 3, 0, args);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result));
        return;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_on_write(struct mjs *mjs)
{
    mjs_val_t cb = mjs_arg(mjs, 0);
    if (mjs_is_function(cb))
    {
        bluetooth_on_write_cb = cb;
    }
    else
    {
        bluetooth_on_write_cb = MJS_UNDEFINED;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_on_notify(struct mjs *mjs)
{
    mjs_val_t cb = mjs_arg(mjs, 0);
    if (mjs_is_function(cb))
    {
        bluetooth_on_notify_cb = cb;
    }
    else
    {
        bluetooth_on_notify_cb = MJS_UNDEFINED;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void bluetooth_on_scan(struct mjs *mjs)
{
    mjs_val_t cb = mjs_arg(mjs, 0);
    if (mjs_is_function(cb))
    {
        bluetooth_on_scan_cb = cb;
    }
    else
    {
        bluetooth_on_scan_cb = MJS_UNDEFINED;
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

void bluetooth_create(struct mjs *mjs, mjs_val_t *bluetooth_obj)
{
    bluetooth_on_write_cb = MJS_UNDEFINED;
    bluetooth_on_notify_cb = MJS_UNDEFINED;
    bluetooth_on_scan_cb = MJS_UNDEFINED;

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    mp_obj_t import_name = mp_obj_new_str("picoware.system.bluetooth", strlen("picoware.system.bluetooth"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_Bluetooth));
    mp_obj_t bt_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t bt_mp_class = mp_load_attr(bt_mod, MP_QSTR_Bluetooth);
    bluetooth_mp_instance = mp_call_function_0(bt_mp_class);

    *bluetooth_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *bluetooth_obj, "macAddress", ~0, bluetooth_mac_address);
    mjs_set_getter(mjs, *bluetooth_obj, "connectedAddress", ~0, bluetooth_connected_address);
    mjs_set_getter(mjs, *bluetooth_obj, "isPairing", ~0, bluetooth_is_pairing);
    mjs_set_getter(mjs, *bluetooth_obj, "isScanning", ~0, bluetooth_is_scanning);
    mjs_set_getter(mjs, *bluetooth_obj, "isConnected", ~0, bluetooth_is_connected);
    mjs_set_getter(mjs, *bluetooth_obj, "isPeripheralConnected", ~0, bluetooth_is_peripheral_connected);
    mjs_set_getter(mjs, *bluetooth_obj, "passkey", ~0, bluetooth_passkey);
    mjs_set_getter(mjs, *bluetooth_obj, "services", ~0, bluetooth_services);
    mjs_set_getter(mjs, *bluetooth_obj, "characteristics", ~0, bluetooth_characteristics);

    mjs_set(mjs, *bluetooth_obj, "advertise", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_advertise));
    mjs_set(mjs, *bluetooth_obj, "connect", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_connect));
    mjs_set(mjs, *bluetooth_obj, "decodeName", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_decode_name));
    mjs_set(mjs, *bluetooth_obj, "decodeServices", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_decode_services));
    mjs_set(mjs, *bluetooth_obj, "disconnect", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_disconnect));
    mjs_set(mjs, *bluetooth_obj, "discoverCharacteristics", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_discover_characteristics));
    mjs_set(mjs, *bluetooth_obj, "discoverServices", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_discover_services));
    mjs_set(mjs, *bluetooth_obj, "isDevicePaired", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_is_device_paired));
    mjs_set(mjs, *bluetooth_obj, "isUartReady", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_is_uart_ready));
    mjs_set(mjs, *bluetooth_obj, "loadPairedDevices", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_load_paired_devices));
    mjs_set(mjs, *bluetooth_obj, "onNotify", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_on_notify));
    mjs_set(mjs, *bluetooth_obj, "onScan", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_on_scan));
    mjs_set(mjs, *bluetooth_obj, "onWrite", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_on_write));
    mjs_set(mjs, *bluetooth_obj, "pair", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_pair));
    mjs_set(mjs, *bluetooth_obj, "passkeyReply", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_passkey_reply));
    mjs_set(mjs, *bluetooth_obj, "read", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_read));
    mjs_set(mjs, *bluetooth_obj, "register", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_register));
    mjs_set(mjs, *bluetooth_obj, "removePairedDevice", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_remove_paired_device));
    mjs_set(mjs, *bluetooth_obj, "savePairedDevice", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_save_paired_device));
    mjs_set(mjs, *bluetooth_obj, "scan", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_scan));
    mjs_set(mjs, *bluetooth_obj, "scanForUartDevices", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_scan_for_uart_devices));
    mjs_set(mjs, *bluetooth_obj, "scanStop", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_scan_stop));
    mjs_set(mjs, *bluetooth_obj, "send", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_send));
    mjs_set(mjs, *bluetooth_obj, "startPeripheral", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_start_peripheral));
    mjs_set(mjs, *bluetooth_obj, "stopPeripheral", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_stop_peripheral));
    mjs_set(mjs, *bluetooth_obj, "subscribe", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_subscribe));
    mjs_set(mjs, *bluetooth_obj, "write", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)bluetooth_write));

    nlr_pop();
}

void bluetooth_destroy()
{
    bluetooth_mp_instance = MP_OBJ_NULL;
    bluetooth_on_write_cb = MJS_UNDEFINED;
    bluetooth_on_notify_cb = MJS_UNDEFINED;
    bluetooth_on_scan_cb = MJS_UNDEFINED;
}
