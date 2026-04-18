/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "py/nlr.h"

    bool http_get_http_response(char *buffer, size_t buffer_size);                                         // retrieves the response of the last
    bool http_is_finished(void);                                                                           // returns true if the current request is finished (either successfully or with an error)
    bool http_send_request(const char *url, const char *method, const char *headers, const char *payload); // sends an HTTP request with the given parameters, returns true if the request was successfully initiated

#ifdef __cplusplus
}
#endif