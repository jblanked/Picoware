#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C"
{
#endif

    size_t storage_file_read(const char *filename, void *buffer, size_t buffer_size);
    size_t storage_file_size(const char *filename);
    bool storage_file_write(const char *filename, const void *buffer, size_t buffer_size);
    size_t storage_file_read_chunk(const char *filename, void *buffer, size_t buffer_size, size_t offset);
    uint16_t storage_file_list(const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count);
    void *storage_file_open(const char *filename);
    void *storage_file_write_open(const char *filename);
    void storage_file_close(void *handle);
    size_t storage_file_read_file_chunk(void *handle, void *buffer, size_t buffer_size);
    bool storage_file_write_file_chunk(void *handle, const void *data, size_t size);

#ifdef __cplusplus
}
#endif