#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>

size_t file_read(const char *filename, uint8_t *buffer, size_t buffer_size);
size_t file_size(const char *filename);
bool file_write(const char *filename, const uint8_t *buffer, size_t buffer_size);
size_t file_read_chunk(const char *filename, uint8_t *buffer, size_t buffer_size, size_t offset);
uint16_t file_list(const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count);
void *file_open(const char *filename);
void *file_write_open(const char *filename);
void file_close(void *handle);
size_t file_read_file_chunk(void *handle, uint8_t *buffer, size_t buffer_size);
bool file_write_file_chunk(void *handle, const uint8_t *data, size_t size);