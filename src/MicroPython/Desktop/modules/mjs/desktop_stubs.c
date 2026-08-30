#include <stdbool.h>
#include <stddef.h>

bool http_get_http_response(void *buffer, size_t buffer_size)
{
    (void)buffer;
    (void)buffer_size;
    return false;
}

bool http_is_finished(void)
{
    return true;
}

bool http_send_request(const char *url, const char *method, const char *headers, const char *payload)
{
    (void)url;
    (void)method;
    (void)headers;
    (void)payload;
    return false;
}

bool http_get_websocket_response(void *buffer, size_t buffer_size)
{
    (void)buffer;
    (void)buffer_size;
    return false;
}

bool http_websocket_is_connected(void)
{
    return false;
}

bool http_websocket_send(const char *message)
{
    (void)message;
    return false;
}

bool http_websocket_start(const char *url, int port)
{
    (void)url;
    (void)port;
    return false;
}

bool http_websocket_stop(void)
{
    return false;
}

void log_message(const char *message)
{
    (void)message;
}

size_t storage_file_read(const char *filename, void *buffer, size_t buffer_size)
{
    (void)filename;
    (void)buffer;
    (void)buffer_size;
    return 0;
}

size_t storage_file_size(const char *filename)
{
    (void)filename;
    return 0;
}

bool storage_file_write(const char *filename, const void *buffer, size_t buffer_size)
{
    (void)filename;
    (void)buffer;
    (void)buffer_size;
    return false;
}
