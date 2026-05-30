/*
 * SD Driver for Crow Panel Advanced 10.1-inch ESP32-P4 HMI AI Display
 * Copyright © 2026 JBlanked
 * https://github.com/jblanked
 *
 * Adapted from https://github.com/Elecrow-RD/CrowPanel-Advanced-10.1inch-ESP32-P4-HMI-AI-Display-1024x600-IPS-Touch-Screen/blob/master/example/V1.0/idf-code/Lesson05-Touchscreen/peripheral/bsp_display/bsp_display.c
 */

#pragma once
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>

#define SD_FREQUENCY 10000 // SD card clock frequency in kHz
#define SD_PIN_CLOCK 43
#define SD_PIN_CMD 44
#define SD_PIN_D0 39

#define SD_MOUNT_POINT "/sdcard" // Default SD card mount point path

#ifdef __cplusplus
extern "C"
{
#endif

    bool sd_create(const char *filename);                                                 // Function to create a new file on SD card
    void sd_deinit(void);                                                                 // Function to unmount SD card and clean up resources
    bool sd_file_close(FILE *file);                                                       // Function to close an open file on SD card
    FILE *sd_file_open(const char *filename, const char *mode);                           // Function to open a file on SD card with specified mode
    bool sd_file_read(FILE *file, void *data, size_t size);                               // Function to read data from an open file on SD card
    bool sd_file_seek(FILE *file, long offset, int whence);                               // Function to seek to a specific position in an open file on SD card
    bool sd_file_write(FILE *file, const void *data, size_t size);                        // Function to write data to an open file on SD card
    bool sd_format_card(void);                                                            // Function to format SD card (FAT filesystem)
    bool sd_init(void);                                                                   // Function to initialize and mount SD card
    size_t sd_read(const char *filename, void *data, size_t size);                        // Function to read raw data from a file
    size_t sd_size(const char *filename);                                                 // Function to read file and return its size
    bool sd_write(const char *filename, const void *data, size_t size, const char *mode); // Function to write raw data to a file

#ifdef __cplusplus
}
#endif