#pragma once
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C"
{
#endif

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
#include "../sd/fat32.h"
#endif

    static inline size_t storage_file_size(const char *file_path)
    {
        if (!fat32_is_mounted())
        {
            fat32_error_t err = fat32_mount();
            if (err != FAT32_OK)
            {
                PRINT("Failed to mount SD card: %s\n", fat32_error_string(err));
                return 0;
            }
        }
        fat32_file_t file;
        fat32_error_t err = fat32_open(&file, file_path);
        if (err != FAT32_OK)
        {
            PRINT("Failed to open file for size retrieval: %s\n", fat32_error_string(err));
            return 0;
        }
        const uint32_t size = (file.attributes & FAT32_ATTR_DIRECTORY) ? 0 : fat32_size(&file);
        fat32_close(&file);
        return size;
    }

    static inline size_t storage_read(const char *file_path, char *buffer, size_t buffer_size)
    {
        if (!fat32_is_mounted())
        {
            fat32_error_t err = fat32_mount();
            if (err != FAT32_OK)
            {
                PRINT("Failed to mount SD card: %s\n", fat32_error_string(err));
                return 0;
            }
        }
        fat32_file_t file;
        fat32_error_t err = fat32_open(&file, file_path);
        if (err != FAT32_OK)
        {
            PRINT("Failed to open file for reading: %s\n", fat32_error_string(err));
            return 0;
        }
        size_t bytes_read = 0;
        bool status = fat32_read(&file, buffer, buffer_size, &bytes_read) == FAT32_OK;
        buffer[bytes_read] = '\0'; // Null-terminate the buffer
        fat32_close(&file);
        return status ? bytes_read : 0;
    }

    static inline bool storage_write(const char *file_path, const void *data, size_t data_size, bool overwrite)
    {
        if (!fat32_is_mounted())
        {
            fat32_error_t err = fat32_mount();
            if (err != FAT32_OK)
            {
                PRINT("Failed to mount SD card: %s\n", fat32_error_string(err));
                return false;
            }
        }
        fat32_file_t file;
        fat32_error_t err = fat32_open(&file, file_path);
        if (err != FAT32_OK)
        {
            err = fat32_create(&file, file_path);
            if (err != FAT32_OK)
            {
                PRINT("Failed to open and create file: %s\n", fat32_error_string(err));
                return false;
            }
        }
        if (overwrite)
        {
            if (fat32_delete(file_path) != FAT32_OK)
            {
                PRINT("Failed to delete existing file.\n");
                return false;
            }
            if (fat32_create(&file, file_path) != FAT32_OK)
            {
                PRINT("Failed to create new file.\n");
                return false;
            }
            if (fat32_open(&file, file_path) != FAT32_OK)
            {
                PRINT("Failed to open new file.\n");
                return false;
            }
        }
        else
        {
            if (fat32_seek(&file, fat32_size(&file)) != FAT32_OK)
            {
                PRINT("Failed to seek to end of file.\n");
                return false;
            }
        }
        size_t bytes_written = 0;
        bool status = fat32_write(&file, data, data_size, &bytes_written) == FAT32_OK;
        fat32_close(&file);
        return status && bytes_written == data_size;
    }

#ifdef __cplusplus
}
#endif
