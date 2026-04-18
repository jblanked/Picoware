/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#include "http_mp.h"
#include "py/nlr.h"
#include <stdio.h>

// GC root slots — scanned by the GC on every collection, no runtime
// register/deregister needed.  Mirror variables keep the local fast-path.
MP_REGISTER_ROOT_POINTER(mp_obj_t http_mp_class);
MP_REGISTER_ROOT_POINTER(mp_obj_t http_mp_instance);

static mp_obj_t http_mp_class = MP_OBJ_NULL;    // the HTTP class object
static mp_obj_t http_mp_instance = MP_OBJ_NULL; // live HTTP() instance
static bool http_mp_initialized = false;

static void http_mp_deinit(void)
{
    // Close the live instance before releasing it
    if (http_mp_instance != MP_OBJ_NULL)
    {
        nlr_buf_t nlr;
        if (nlr_push(&nlr) == 0)
        {
            mp_obj_t close_func = mp_load_attr(http_mp_instance, MP_QSTR_close);
            mp_call_function_0(close_func);
            nlr_pop();
        }
        else
        {
            // Swallow — we are tearing down anyway
            mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        }
    }

    http_mp_instance = MP_STATE_VM(http_mp_instance) = MP_OBJ_NULL;
    http_mp_class = MP_STATE_VM(http_mp_class) = MP_OBJ_NULL;
    http_mp_initialized = false;
}

static bool http_mp_init(void)
{
    if (http_mp_initialized)
    {
        return true;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    // import picoware.system.http  →  get the HTTP class
    mp_obj_t picoware = mp_import_name(MP_QSTR_picoware, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t system = mp_load_attr(picoware, MP_QSTR_system);
    mp_obj_t http = mp_load_attr(system, MP_QSTR_http);
    http_mp_class = MP_STATE_VM(http_mp_class) = mp_load_attr(http, MP_QSTR_HTTP);

    // Instantiate:  instance = HTTP()
    http_mp_instance = MP_STATE_VM(http_mp_instance) = mp_call_function_0(http_mp_class);

    http_mp_initialized = true;
    nlr_pop();
    return true;
}

bool http_send_request(const char *url, const char *method, const char *headers, const char *payload)
{
    if (!http_mp_init())
    {
        return false;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    mp_obj_t request_async = mp_load_attr(http_mp_instance, MP_QSTR_request_async);

    mp_obj_t args[4];
    args[0] = mp_obj_new_str(method, strlen(method));
    args[1] = mp_obj_new_str(url, strlen(url));
    args[2] = mp_obj_new_str(payload, strlen(payload));
    args[3] = mp_obj_new_str(headers, strlen(headers));

    mp_obj_t result = mp_call_function_n_kw(request_async, 4, 0, args);
    nlr_pop();
    return mp_obj_is_true(result);
}

bool http_is_finished(void)
{
    if (!http_mp_init())
    {
        return false;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    mp_obj_t result = mp_load_attr(http_mp_instance, MP_QSTR_is_finished);
    nlr_pop();
    return mp_obj_is_true(result);
}

bool http_get_http_response(char *buffer, size_t buffer_size)
{
    // Must be called AFTER http_is_finished() returns true.
    // Cleans up the instance when done — call order must be:
    //   http_send_request → poll http_is_finished → http_get_http_response
    if (!http_mp_init())
    {
        return false;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    mp_obj_t response = mp_load_attr(http_mp_instance, MP_QSTR_response);
    if (response == mp_const_none)
    {
        nlr_pop();
        return false; // request not yet complete or failed with no body
    }

    const char *response_str = mp_obj_str_get_str(response);
    snprintf(buffer, buffer_size, "%s", response_str);
    nlr_pop();

    // Release everything — mirrors:  r.close(); del r; r = None
    http_mp_deinit();
    return true;
}