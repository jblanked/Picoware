#include "websocket.h"
#include "py/runtime.h"
#include "../../websocket/websocket_mp.h"
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

void websocket_js_get_response(struct mjs *mjs)
{
    mjs_val_t arg = mjs_arg(mjs, 0);
    size_t buffer_size = mjs_is_null(arg) || mjs_is_undefined(arg) ? 2048 : (size_t)mjs_get_int(mjs, arg);
    char *buffer = (char *)m_malloc0(buffer_size);
    if (buffer == NULL || !http_get_websocket_response(buffer, buffer_size))
    {
        mjs_return(mjs, MJS_UNDEFINED);
        buffer = NULL;
        return;
    }
    mjs_return(mjs, mjs_mk_string(mjs, buffer, strlen(buffer), 1));
}

void websocket_js_is_connected(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_boolean(mjs, http_websocket_is_connected()));
}

void websocket_js_send(struct mjs *mjs)
{
    char *message = mjs_copy_string_arg(mjs, 0);
    if (message)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, http_websocket_send(message)));
        m_free(message);
        return;
    }

    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

void websocket_js_start(struct mjs *mjs)
{
    char *url = mjs_copy_string_arg(mjs, 0);
    if (url == NULL)
    {
        mjs_return(mjs, mjs_mk_boolean(mjs, false));
        return;
    }
    uint16_t port = (uint16_t)mjs_get_int(mjs, mjs_arg(mjs, 1));
    mjs_return(mjs, mjs_mk_boolean(mjs, http_websocket_start(url, port)));
    m_free(url);
}

void websocket_js_stop(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_boolean(mjs, http_websocket_stop()));
}

void websocket_create(struct mjs *mjs, mjs_val_t *websocket_obj)
{
    *websocket_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *websocket_obj, "getResponse", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)websocket_js_get_response));
    mjs_set(mjs, *websocket_obj, "isConnected", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)websocket_js_is_connected));
    mjs_set(mjs, *websocket_obj, "send", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)websocket_js_send));
    mjs_set(mjs, *websocket_obj, "start", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)websocket_js_start));
    mjs_set(mjs, *websocket_obj, "stop", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)websocket_js_stop));
}