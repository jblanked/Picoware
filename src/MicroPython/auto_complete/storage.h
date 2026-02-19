#pragma once
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C"
{
#endif

#if defined(WAVESHARE_1_28)
#include "../Waveshare/RP2350-Touch-LCD-1.28/waveshare_sd/fat32.h"
#elif defined(WAVESHARE_1_43)
#include "../Waveshare/RP2350-Touch-LCD-1.43/waveshare_sd/fat32.h"
#elif defined(WAVESHARE_3_49)
#include "../Waveshare/RP2350-Touch-LCD-3.49/waveshare_sd/fat32.h"
#elif defined(PICOCALC)
#include "../PicoCalc/picoware_sd/fat32.h"
#endif

    static inline size_t storage_read(const char *file_path, char *buffer, size_t buffer_size)
    {
        if (!fat32_is_mounted())
        {
            fat32_error_t err = fat32_mount();
            if (err != FAT32_OK)
            {
                printf("Failed to mount SD card: %s\n", fat32_error_string(err));
                return 0;
            }
        }
        fat32_file_t file;
        fat32_error_t err = fat32_open(&file, file_path);
        if (err != FAT32_OK)
        {
            printf("Failed to open file for reading: %s\n", fat32_error_string(err));
            return 0;
        }
        size_t bytes_read = 0;
        bool status = fat32_read(&file, buffer, buffer_size, &bytes_read) == FAT32_OK;
        buffer[bytes_read] = '\0'; // Null-terminate the buffer
        fat32_close(&file);
        return status ? bytes_read : 0;
    }

#ifdef __cplusplus
}
#endif
