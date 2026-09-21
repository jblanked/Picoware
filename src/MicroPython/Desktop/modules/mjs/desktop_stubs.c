#include <stdbool.h>
#include <stddef.h>

#include "../../desktop_bridge.h"

bool http_get_http_response(void *buffer, size_t buffer_size)
{
    return desktop_http_get_response(buffer, buffer_size);
}

bool http_is_finished(void)
{
    return desktop_http_is_finished();
}

bool http_send_request(const char *url, const char *method, const char *headers, const char *payload)
{
    return desktop_http_send_request(url, method, headers, payload);
}

bool http_get_websocket_response(void *buffer, size_t buffer_size)
{
    return desktop_http_get_websocket_response(buffer, buffer_size);
}

bool http_websocket_is_connected(void)
{
    return desktop_http_websocket_is_connected();
}

bool http_websocket_send(const char *message)
{
    return desktop_http_websocket_send(message);
}

bool http_websocket_start(const char *url, int port)
{
    return desktop_http_websocket_start(url, port);
}

bool http_websocket_stop(void)
{
    return desktop_http_websocket_stop();
}

void log_message(const char *message)
{
    desktop_log_message(message);
}

size_t storage_file_read(const char *filename, void *buffer, size_t buffer_size)
{
    return desktop_storage_file_read(filename, buffer, buffer_size);
}

size_t storage_file_size(const char *filename)
{
    return desktop_storage_file_size(filename);
}

bool storage_file_write(const char *filename, const void *buffer, size_t buffer_size)
{
    return desktop_storage_file_write(filename, buffer, buffer_size);
}
