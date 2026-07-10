#include "input.h"
#include <string.h>
#include "py/runtime.h"

static mp_obj_t input_mp_instance;

static void input_button_to_char(struct mjs *mjs)
{
    mjs_val_t arg = mjs_arg(mjs, 0);
    double button = mjs_get_int(mjs, arg);
    mp_obj_t func = mp_load_attr(input_mp_instance, MP_QSTR_button_to_char);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t button_arg = mp_obj_new_int((int)button);
        mp_obj_t result_str = mp_call_function_1(func, button_arg);
        if (result_str != MP_OBJ_NULL && mp_obj_is_str(result_str))
        {
            size_t result_len;
            const char *result_cstr = mp_obj_str_get_data(result_str, &result_len);
            mjs_return(mjs, mjs_mk_string(mjs, result_cstr, result_len, 1));
            return;
        }
    }
    mjs_return(mjs, mjs_mk_string(mjs, "", 0, 1));
}

static void input_read(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(input_mp_instance, MP_QSTR_read);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result_int = mp_call_function_0(func);
        mjs_return(mjs, mjs_mk_number(mjs, mp_obj_is_float(result_int) ? (double)mp_obj_get_float(result_int) : (double)mp_obj_get_int(result_int)));
        return;
    }
    mjs_return(mjs, mjs_mk_number(mjs, -1));
}

static void input_read_non_blocking(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(input_mp_instance, MP_QSTR_read_non_blocking);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result_int = mp_call_function_0(func);
        mjs_return(mjs, mjs_mk_number(mjs, mp_obj_is_float(result_int) ? (double)mp_obj_get_float(result_int) : (double)mp_obj_get_int(result_int)));
        return;
    }
    mjs_return(mjs, mjs_mk_number(mjs, -1));
}

static void input_reset(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(input_mp_instance, MP_QSTR_reset);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static mjs_val_t input_battery(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, input_mp_instance, MP_QSTR_battery);
}

static mjs_val_t input_button(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, input_mp_instance, MP_QSTR_button);
}

static mjs_val_t input_was_capitalized(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, input_mp_instance, MP_QSTR_was_capitalized);
}

void input_create(struct mjs *mjs, mjs_val_t *input_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    // from picoware.system.input import Input
    mp_obj_t import_name = mp_obj_new_str("picoware.system.input", strlen("picoware.system.input"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_Input));
    mp_obj_t input_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t input_mp_class = mp_load_attr(input_mod, MP_QSTR_Input);
    input_mp_instance = mp_call_function_0(input_mp_class);

    *input_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *input_obj, "battery", ~0, input_battery);
    mjs_set_getter(mjs, *input_obj, "button", ~0, input_button);
    mjs_set_getter(mjs, *input_obj, "wasCapitalized", ~0, input_was_capitalized);

    mjs_set(mjs, *input_obj, "buttonToChar", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)input_button_to_char));
    mjs_set(mjs, *input_obj, "read", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)input_read));
    mjs_set(mjs, *input_obj, "readNonBlocking", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)input_read_non_blocking));
    mjs_set(mjs, *input_obj, "reset", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)input_reset));

    nlr_pop();
}

void input_destroy()
{
    input_mp_instance = MP_OBJ_NULL;
}