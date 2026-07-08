#include "pin.h"

static mp_obj_t pin_mp_instance;

static void pin_high(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(pin_mp_instance, MP_QSTR_high);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void pin_low(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(pin_mp_instance, MP_QSTR_low);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void pin_off(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(pin_mp_instance, MP_QSTR_off);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void pin_on(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(pin_mp_instance, MP_QSTR_on);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void pin_toggle(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(pin_mp_instance, MP_QSTR_toggle);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void pin_value(struct mjs *mjs)
{
    mjs_val_t arg = mjs_arg(mjs, 0);
    if (mjs_is_undefined(arg) || mjs_is_null(arg))
    {
        mp_obj_t func = mp_load_attr(pin_mp_instance, MP_QSTR_value);
        if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
        {
            mp_obj_t result_int = mp_call_function_0(func);
            mjs_return(mjs, mjs_val_from_mp_obj(mjs, result_int));
            return;
        }
        mjs_return(mjs, mjs_mk_number(mjs, -1));
        return;
    }
    double toggle_value = mjs_get_int(mjs, arg);
    mp_obj_t func = mp_load_attr(pin_mp_instance, MP_QSTR_value);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t toggle_value_arg = mp_obj_new_int((int)toggle_value);
        mp_obj_t result_int = mp_call_function_1(func, toggle_value_arg);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result_int));
        return;
    }
    mjs_return(mjs, mjs_mk_string(mjs, "", 0, 1));
}

bool pin_create(struct mjs *mjs, mjs_val_t *pin_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    // from machine import Pin
    mp_obj_t import_name = mp_obj_new_str("machine", strlen("machine"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_Pin));
    mp_obj_t machine_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t pin_mp_class = mp_load_attr(machine_mod, MP_QSTR_Pin);

    // shifted pin because parent func has the first arg as the import name
    mjs_val_t arg1 = mjs_arg(mjs, 1); // pin number
    mjs_val_t arg2 = mjs_arg(mjs, 2); // str ("IN" or "OUT")
    mjs_val_t arg3 = mjs_arg(mjs, 3); // str ("PULL_UP" or "PULL_DOWN")

    /*
    0 = Pin.IN (Input)
    1 = Pin.OUT (Output)
    2 = Pin.OPEN_DRAIN (Open Drain)

    1 = Pin.PULL_UP
    2 = Pin.PULL_DOWN
    */

    if (mjs_is_undefined(arg1) || mjs_is_null(arg1))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 2: expected pin number");
        return false;
    }
    if (mjs_is_string(arg2))
    {
        size_t len;
        const char *direction = mjs_get_string(mjs, &arg2, &len);
        if (strcmp(direction, "IN") == 0)
        {
            arg2 = mjs_mk_number(mjs, 0); // Pin.IN
        }
        else if (strcmp(direction, "OUT") == 0)
        {
            arg2 = mjs_mk_number(mjs, 1); // Pin.OUT
        }
        else if (strcmp(direction, "OPEN_DRAIN") == 0)
        {
            arg2 = mjs_mk_number(mjs, 2); // Pin.OPEN_DRAIN
        }
        else
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 3: expected 'IN', 'OUT', or 'OPEN_DRAIN' for pin direction");
            return false;
        }
    }
    else
    {
        arg2 = mjs_mk_number(mjs, -1); // no direction
    }
    if (mjs_is_string(arg3))
    {
        size_t len;
        const char *pull = mjs_get_string(mjs, &arg3, &len);
        if (strcmp(pull, "PULL_UP") == 0)
        {
            arg3 = mjs_mk_number(mjs, 1); // Pin.PULL_UP
        }
        else if (strcmp(pull, "PULL_DOWN") == 0)
        {
            arg3 = mjs_mk_number(mjs, 2); // Pin.PULL_DOWN
        }
        else
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 4: expected 'PULL_UP' or 'PULL_DOWN' for pin pull");
            return false;
        }
    }
    else
    {
        arg3 = mjs_mk_number(mjs, -1); // No pull
    }

    mp_obj_t args[3] = {mjs_val_to_mp_obj(mjs, arg1), mjs_val_to_mp_obj(mjs, arg2), mjs_val_to_mp_obj(mjs, arg3)};
    pin_mp_instance = mp_call_function_n_kw(pin_mp_class, 3, 0, args);

    *pin_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *pin_obj, "high", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)pin_high));
    mjs_set(mjs, *pin_obj, "low", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)pin_low));
    mjs_set(mjs, *pin_obj, "off", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)pin_off));
    mjs_set(mjs, *pin_obj, "on", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)pin_on));
    mjs_set(mjs, *pin_obj, "toggle", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)pin_toggle));
    mjs_set(mjs, *pin_obj, "value", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)pin_value));

    nlr_pop();
    return true;
}

void pin_destroy()
{
    pin_mp_instance = MP_OBJ_NULL;
}