#include "http.h"
#include "py/runtime.h"
#include "../../http/http_mp.h"
#include <stdbool.h>
#include <string.h>

static const char *http_js_get_string(struct mjs *mjs, uint8_t arg)
{
    mjs_val_t t_arg = mjs_arg(mjs, arg);
    size_t len;
    return mjs_get_string(mjs, &t_arg, &len);
}

void http_js_get_response(struct mjs *mjs)
{
    size_t buffer_size = (size_t)mjs_get_int(mjs, mjs_arg(mjs, 1));
    char *buffer = (char *)m_malloc(buffer_size);
    if (buffer == NULL)
    {
        mjs_return(mjs, mjs_mk_undefined());
        return;
    }
    if (http_get_http_response(buffer, sizeof(buffer)))
    {
        mjs_return(mjs, mjs_mk_string(mjs, buffer, strlen(buffer), 1));
    }
    else
    {
        mjs_return(mjs, mjs_mk_undefined());
    }
    m_free(buffer);
}

void http_js_is_finished(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_boolean(mjs, http_is_finished()));
}

void http_js_request(struct mjs *mjs)
{
    const char *url = http_js_get_string(mjs, 0);
    const char *method = http_js_get_string(mjs, 1);
    const char *headers = http_js_get_string(mjs, 2);
    const char *payload = http_js_get_string(mjs, 3);
    size_t buffer_size = (size_t)mjs_get_int(mjs, mjs_arg(mjs, 4));

    if (http_send_request(url, method, headers, payload))
    {
        while (!http_is_finished())
        {
            // Wait for the request to finish
        }
        char *response_buffer = (char *)m_malloc(buffer_size);
        if (response_buffer == NULL)
        {
            mjs_return(mjs, mjs_mk_undefined());
            return;
        }
        if (http_get_http_response(response_buffer, buffer_size))
        {
            mjs_return(mjs, mjs_mk_string(mjs, response_buffer, strlen(response_buffer), 1));
            m_free(response_buffer);
            return;
        }
        m_free(response_buffer);
        mjs_return(mjs, mjs_mk_undefined());
        return;
    }
    mjs_return(mjs, mjs_mk_undefined());
}

void http_js_request_start(struct mjs *mjs)
{
    const char *url = http_js_get_string(mjs, 0);
    const char *method = http_js_get_string(mjs, 1);
    const char *headers = http_js_get_string(mjs, 2);
    const char *payload = http_js_get_string(mjs, 3);

    mjs_return(mjs, mjs_mk_boolean(mjs, http_send_request(url, method, headers, payload)));
}

void http_register(struct mjs *mjs)
{
    mjs_val_t http_obj = mjs_mk_object(mjs);

    mjs_set(mjs, http_obj, "getResponse", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_get_response));
    mjs_set(mjs, http_obj, "isFinished", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_is_finished));
    mjs_set(mjs, http_obj, "request", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_request));
    mjs_set(mjs, http_obj, "requestStart", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_request_start));

    mjs_set(mjs, http_obj, "http", ~0, http_obj);
}