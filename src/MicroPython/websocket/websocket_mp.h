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

    bool http_get_websocket_response(char *buffer, size_t buffer_size); // retrieves the next message from the websocket, returns true if a message was successfully retrieved
    bool http_websocket_is_connected(void);                             // returns true if the websocket is currently connected
    bool http_websocket_send(const char *message);                      // sends a message over the websocket, returns true if the message was successfully sent
    bool http_websocket_start(const char *url, uint16_t port);          // starts a websocket connection to the given URL and port, returns true if the connection was successfully initiated
    bool http_websocket_stop(void);                                     // stops the websocket connection, returns true if the connection was successfully stopped

#ifdef __cplusplus
}
#endif