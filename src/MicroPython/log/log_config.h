#pragma once

// storage info
#ifndef WAVESHARE_1_28
#define LOG_STORAGE_INCLUDE "storage.h"
#define LOG_STORAGE_READ storage_read   // (const char *file_path, char *buffer, size_t buffer_size)
#define LOG_STORAGE_WRITE storage_write // (const char *file_path, const char *data, size_t data_size, bool overwrite)
#define LOG_FILE_SIZE storage_file_size // (const char *file_path)
#endif