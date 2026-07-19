#include "http.h"
#include "py/runtime.h"
#include "../../http/http_mp.h"
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

void http_js_get_response(struct mjs *mjs)
{
    size_t buffer_size = (size_t)mjs_get_int(mjs, mjs_arg(mjs, 0));
    char *buffer = (char *)m_malloc(buffer_size);
    if (buffer == NULL || !http_get_http_response(buffer, buffer_size))
    {
        mjs_return(mjs, MJS_UNDEFINED);
        if (buffer != NULL)
        {
            m_free(buffer);
            buffer = NULL;
        }
        return;
    }
    mjs_return(mjs, mjs_mk_string(mjs, buffer, strlen(buffer), 1));
    m_free(buffer);
    buffer = NULL;
}

void http_js_is_finished(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_boolean(mjs, http_is_finished()));
}

void http_js_request(struct mjs *mjs)
{
    char *url_copy = mjs_copy_string_arg(mjs, 0);
    char *method_copy = mjs_copy_string_arg(mjs, 1);
    char *headers_copy = mjs_copy_string_arg(mjs, 2);
    char *payload_copy = mjs_copy_string_arg(mjs, 3);

    const char *url = url_copy ? url_copy : "";
    const char *method = method_copy ? method_copy : "GET";
    const char *headers = headers_copy;
    const char *payload = payload_copy;

    if (strcmp(method, "POST") == 0 || strcmp(method, "PUT") == 0 || strcmp(method, "PATCH") == 0)
    {
        if (payload == NULL || strlen(payload) == 0)
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 3: expected non-empty payload for method %s", method);
            m_free(url_copy);
            m_free(method_copy);
            m_free(headers_copy);
            m_free(payload_copy);
            mjs_return(mjs, MJS_UNDEFINED);
            return;
        }
    }

    // buffer size
    mjs_val_t buffer_size_arg = mjs_arg(mjs, 4);
    size_t buffer_size = HTTP_JS_DEFAULT_BUFFER_SIZE;
    if (!mjs_is_undefined(buffer_size_arg) && !mjs_is_null(buffer_size_arg))
    {
        buffer_size = (size_t)mjs_get_int(mjs, buffer_size_arg);
    }

    if (http_send_request(url, method, headers, payload))
    {
        m_free(url_copy);
        m_free(method_copy);
        m_free(headers_copy);
        m_free(payload_copy);

        while (!http_is_finished())
        {
            // Wait for the request to finish
        }
        char *response_buffer = (char *)m_malloc(buffer_size);
        if (response_buffer == NULL)
        {
            mjs_return(mjs, MJS_UNDEFINED);
            return;
        }
        if (http_get_http_response(response_buffer, buffer_size))
        {
            mjs_return(mjs, mjs_mk_string(mjs, response_buffer, strlen(response_buffer), 0));
            m_free(response_buffer);
            return;
        }
        m_free(response_buffer);
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }

    m_free(url_copy);
    m_free(method_copy);
    m_free(headers_copy);
    m_free(payload_copy);

    mjs_return(mjs, MJS_UNDEFINED);
}

void http_js_request_start(struct mjs *mjs)
{
    char *url_copy = mjs_copy_string_arg(mjs, 0);
    char *method_copy = mjs_copy_string_arg(mjs, 1);
    char *headers_copy = mjs_copy_string_arg(mjs, 2);
    char *payload_copy = mjs_copy_string_arg(mjs, 3);

    const char *url = url_copy ? url_copy : "";
    const char *method = method_copy ? method_copy : "GET";
    const char *headers = headers_copy;
    const char *payload = payload_copy;

    if (strcmp(method, "POST") == 0 || strcmp(method, "PUT") == 0 || strcmp(method, "PATCH") == 0)
    {
        if (payload == NULL || strlen(payload) == 0)
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 3: expected non-empty payload for method %s", method);
            m_free(url_copy);
            m_free(method_copy);
            m_free(headers_copy);
            m_free(payload_copy);
            mjs_return(mjs, mjs_mk_boolean(mjs, false));
            return;
        }
    }

    bool started = http_send_request(url, method, headers, payload);

    m_free(url_copy);
    m_free(method_copy);
    m_free(headers_copy);
    m_free(payload_copy);

    mjs_return(mjs, mjs_mk_boolean(mjs, started));
}

void http_create(struct mjs *mjs, mjs_val_t *http_obj)
{
    *http_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *http_obj, "getResponse", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_get_response));
    mjs_set(mjs, *http_obj, "isFinished", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_is_finished));
    mjs_set(mjs, *http_obj, "request", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_request));
    mjs_set(mjs, *http_obj, "requestStart", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)http_js_request_start));
}