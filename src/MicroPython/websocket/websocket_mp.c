/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#include "websocket_mp.h"
#include "py/nlr.h"
#include <stdio.h>

// GC root slots — scanned by the GC on every collection, no runtime
// register/deregister needed.  Mirror variables keep the local fast-path.
MP_REGISTER_ROOT_POINTER(mp_obj_t websocket_mp_class);
MP_REGISTER_ROOT_POINTER(mp_obj_t websocket_mp_instance);

static mp_obj_t websocket_mp_class = MP_OBJ_NULL;    // the WebSocketAsync class  (cached, reused)
static mp_obj_t websocket_mp_instance = MP_OBJ_NULL; // live WebSocketAsync(uri) instance
static bool websocket_mp_initialized = false;

// Full teardown — releases both class and instance.
static void websocket_mp_deinit(void)
{
    websocket_mp_instance = MP_STATE_VM(websocket_mp_instance) = MP_OBJ_NULL;
    websocket_mp_class = MP_STATE_VM(websocket_mp_class) = MP_OBJ_NULL;
    websocket_mp_initialized = false;
}

// Imports and caches the WebSocketAsync class (once per power-on).
// The instance is created separately in http_websocket_start().
static bool websocket_mp_init(void)
{
    if (websocket_mp_initialized)
    {
        return true;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    // import picoware.system.websocket  →  get the WebSocketAsync class
    mp_obj_t picoware = mp_import_name(MP_QSTR_picoware, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t system = mp_load_attr(picoware, MP_QSTR_system);
    mp_obj_t websocket = mp_load_attr(system, MP_QSTR_websocket);
    websocket_mp_class = MP_STATE_VM(websocket_mp_class) = mp_load_attr(websocket, MP_QSTR_WebSocketAsync);

    websocket_mp_initialized = true;
    nlr_pop();
    return true;
}

bool http_websocket_start(const char *url, uint16_t port)
{
    if (!websocket_mp_init())
    {
        return false;
    }

    // Refuse to start a second connection without stopping the first
    if (websocket_mp_instance != MP_OBJ_NULL)
    {
        return false;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    // instance = WebSocketAsync(url)
    mp_obj_t url_obj = mp_obj_new_str(url, strlen(url));
    websocket_mp_instance = MP_STATE_VM(websocket_mp_instance) = mp_call_function_1(websocket_mp_class, url_obj);

    // instance.connect()
    mp_obj_t connect_method = mp_load_attr(websocket_mp_instance, MP_QSTR_connect);
    mp_call_function_0(connect_method);

    nlr_pop();
    return true;
}

bool http_websocket_stop(void)
{
    if (websocket_mp_instance == MP_OBJ_NULL)
    {
        return false; // no active instance
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        // Null the instance even on failure to avoid a dangling reference
        websocket_mp_instance = MP_STATE_VM(websocket_mp_instance) = MP_OBJ_NULL;
        return false;
    }

    mp_obj_t close_method = mp_load_attr(websocket_mp_instance, MP_QSTR_close);
    mp_call_function_0(close_method);
    nlr_pop();

    // Release the instance but keep the class cached for the next connect.
    // The VM root slot for the instance now holds NULL, which is safe.
    websocket_mp_instance = MP_STATE_VM(websocket_mp_instance) = MP_OBJ_NULL;
    return true;
}

bool http_websocket_send(const char *message)
{
    if (websocket_mp_instance == MP_OBJ_NULL)
    {
        return false; // no active instance
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    mp_obj_t send_method = mp_load_attr(websocket_mp_instance, MP_QSTR_send);
    mp_obj_t message_obj = mp_obj_new_str(message, strlen(message));
    mp_obj_t sent = mp_call_function_1(send_method, message_obj);
    nlr_pop();
    return mp_obj_is_true(sent);
}

bool http_websocket_is_connected(void)
{
    if (websocket_mp_instance == MP_OBJ_NULL)
    {
        return false; // no active instance
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    mp_obj_t is_connected_attr = mp_load_attr(websocket_mp_instance, MP_QSTR_is_connected);
    nlr_pop();
    return mp_obj_is_true(is_connected_attr);
}

bool http_get_websocket_response(char *buffer, size_t buffer_size)
{
    if (websocket_mp_instance == MP_OBJ_NULL)
    {
        return false; // no active instance
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return false;
    }

    mp_obj_t last_received = mp_load_attr(websocket_mp_instance, MP_QSTR_last_received);
    if (last_received == mp_const_none)
    {
        nlr_pop();
        return false; // no message waiting
    }

    const char *response_str = mp_obj_str_get_str(last_received);
    snprintf(buffer, buffer_size, "%s", response_str);
    nlr_pop();
    return true;
}