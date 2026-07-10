#include "uart.h"
#include "array_buf.h"

static mp_obj_t uart_mp_instance;

static mjs_val_t uart_baud_rate(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, uart_mp_instance, MP_QSTR_baud_rate);
}

static mjs_val_t uart_has_data(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, uart_mp_instance, MP_QSTR_has_data);
}

static mjs_val_t uart_is_sending(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, uart_mp_instance, MP_QSTR_is_sending);
}

static mjs_val_t uart_rx_pin(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, uart_mp_instance, MP_QSTR_rx_pin);
}

static mjs_val_t uart_timeout(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, uart_mp_instance, MP_QSTR_timeout);
}

static mjs_val_t uart_tx_pin(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, uart_mp_instance, MP_QSTR_tx_pin);
}

static void uart_clear(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(uart_mp_instance, MP_QSTR_clear);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void uart_flush(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(uart_mp_instance, MP_QSTR_flush);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_call_function_0(func);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void uart_println(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(uart_mp_instance, MP_QSTR_println);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t data_js = mjs_arg(mjs, 0);
        if (mjs_is_undefined(data_js) || mjs_is_null(data_js))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "uart.println: data argument is undefined or null");
            mjs_return(mjs, MJS_UNDEFINED);
            return;
        }
        mp_obj_t data_mp = mjs_val_to_mp_obj(mjs, data_js);
        mp_call_function_1(func, data_mp);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

static void uart_read_into(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(uart_mp_instance, MP_QSTR_read_into);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t buffer_js = mjs_arg(mjs, 0);
        if (mjs_is_undefined(buffer_js) || mjs_is_null(buffer_js))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "uart.read_into: buffer argument is undefined or null");
            mjs_return(mjs, MJS_UNDEFINED);
            return;
        }
        mjs_val_t length_js = mjs_arg(mjs, 1);
        size_t length = mjs_is_undefined(length_js) || mjs_is_null(length_js) ? 1024 : (size_t)mjs_get_double(mjs, length_js);
        if (mjs_is_array(buffer_js))
        {
            uint8_t *tmp_buf = (uint8_t *)m_malloc(length);
            if (tmp_buf == NULL)
            {
                mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "uart.read_into: out of memory");
                mjs_return(mjs, MJS_UNDEFINED);
                return;
            }
            mjs_val_t buf_val = mjs_mk_array_buf(mjs, tmp_buf, length);
            mp_obj_t buffer_mp = mjs_val_to_mp_obj(mjs, buf_val);
            mp_obj_t result_int = mp_call_function_1(func, buffer_mp);
            int nread = mp_obj_is_int(result_int) ? mp_obj_get_int(result_int) : 0;

            if (nread > 0)
            {
                for (int i = 0; i < nread; i++)
                {
                    mjs_array_push(mjs, buffer_js, mjs_mk_number(mjs, tmp_buf[i]));
                }
            }

            m_free(tmp_buf);
            mjs_return(mjs, mjs_val_from_mp_obj(mjs, result_int));
            return;
        }

        mp_obj_t buffer_mp = mjs_val_to_mp_obj(mjs, buffer_js);
        mp_obj_t result_int = mp_call_function_1(func, buffer_mp);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result_int));
        return;
    }
    mjs_return(mjs, mjs_mk_number(mjs, -1));
}

static void uart_read_line(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(uart_mp_instance, MP_QSTR_read_line);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result_str = mp_call_function_0(func);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result_str));
        return;
    }
    mjs_return(mjs, mjs_mk_string(mjs, "", 0, 1));
}

static void uart_read_serial_line(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(uart_mp_instance, MP_QSTR_read_serial_line);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result_str = mp_call_function_0(func);
        mjs_return(mjs, mjs_val_from_mp_obj(mjs, result_str));
        return;
    }
    mjs_return(mjs, mjs_mk_string(mjs, "", 0, 1));
}

static void uart_write(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(uart_mp_instance, MP_QSTR_write);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mjs_val_t data_js = mjs_arg(mjs, 0);
        if (mjs_is_undefined(data_js) || mjs_is_null(data_js))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "uart.write: data argument is undefined or null");
            mjs_return(mjs, MJS_UNDEFINED);
            return;
        }
        mp_obj_t data_mp = mjs_val_to_mp_obj(mjs, mjs_arg(mjs, 0));
        mp_call_function_1(func, data_mp);
    }
    mjs_return(mjs, MJS_UNDEFINED);
}

void uart_create(struct mjs *mjs, mjs_val_t *uart_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    // from picoware.system.uart import UART
    mp_obj_t import_name = mp_obj_new_str("picoware.system.uart", strlen("picoware.system.uart"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_UART));
    mp_obj_t uart_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t uart_mp_class = mp_load_attr(uart_mod, MP_QSTR_UART);

    // shifted because parent func has the first arg as the import name
    mjs_val_t uart_id_js = mjs_arg(mjs, 1);
    mjs_val_t tx_pin_js = mjs_arg(mjs, 2);
    mjs_val_t rx_pin_js = mjs_arg(mjs, 3);
    mjs_val_t baud_rate_js = mjs_arg(mjs, 4);
    mjs_val_t timeout_js = mjs_arg(mjs, 5);

    mp_obj_t uart_id_mp = mjs_is_undefined(uart_id_js) ? mp_obj_new_int(0) : mjs_val_to_mp_obj(mjs, uart_id_js);
    mp_obj_t tx_pin_mp = mjs_is_undefined(tx_pin_js) ? mp_obj_new_int(0) : mjs_val_to_mp_obj(mjs, tx_pin_js);
    mp_obj_t rx_pin_mp = mjs_is_undefined(rx_pin_js) ? mp_obj_new_int(1) : mjs_val_to_mp_obj(mjs, rx_pin_js);
    mp_obj_t baud_rate_mp = mjs_is_undefined(baud_rate_js) ? mp_obj_new_int(115000) : mjs_val_to_mp_obj(mjs, baud_rate_js);
    mp_obj_t timeout_mp = mjs_is_undefined(timeout_js) ? mp_obj_new_int(2000) : mjs_val_to_mp_obj(mjs, timeout_js);

    mp_obj_t args[5] = {uart_id_mp, tx_pin_mp, rx_pin_mp, baud_rate_mp, timeout_mp};
    uart_mp_instance = mp_call_function_n_kw(uart_mp_class, 5, 0, args);

    *uart_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *uart_obj, "baudRate", ~0, uart_baud_rate);
    mjs_set_getter(mjs, *uart_obj, "hasData", ~0, uart_has_data);
    mjs_set_getter(mjs, *uart_obj, "isSending", ~0, uart_is_sending);
    mjs_set_getter(mjs, *uart_obj, "rxPin", ~0, uart_rx_pin);
    mjs_set_getter(mjs, *uart_obj, "timeout", ~0, uart_timeout);
    mjs_set_getter(mjs, *uart_obj, "txPin", ~0, uart_tx_pin);
    //
    mjs_set(mjs, *uart_obj, "clear", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)uart_clear));
    mjs_set(mjs, *uart_obj, "flush", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)uart_flush));
    mjs_set(mjs, *uart_obj, "println", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)uart_println));
    mjs_set(mjs, *uart_obj, "readInto", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)uart_read_into));
    mjs_set(mjs, *uart_obj, "readLine", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)uart_read_line));
    mjs_set(mjs, *uart_obj, "readSerialLine", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)uart_read_serial_line));
    mjs_set(mjs, *uart_obj, "write", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)uart_write));

    nlr_pop();
}

void uart_destroy()
{
    uart_mp_instance = MP_OBJ_NULL;
}