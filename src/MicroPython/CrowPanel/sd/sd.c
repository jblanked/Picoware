/*
 * SD Driver for Crow Panel Advanced 10.1-inch ESP32-P4 HMI AI Display
 * Copyright © 2026 JBlanked
 * https://github.com/jblanked
 *
 * Adapted from https://github.com/Elecrow-RD/CrowPanel-Advanced-10.1inch-ESP32-P4-HMI-AI-Display-1024x600-IPS-Touch-Screen/blob/master/example/V1.0/idf-code/Lesson05-Touchscreen/peripheral/bsp_display/bsp_display.c
 */

#include <string.h>            // Include standard string manipulation functions
#include <sys/unistd.h>        // Include system calls for file handling
#include <sys/stat.h>          // Include functions for file status and permissions
#include "esp_vfs_fat.h"       // Include ESP-IDF FAT filesystem support for SD card
#include "sdmmc_cmd.h"         // Include SDMMC card command definitions and helpers
#include "driver/sdmmc_host.h" // Include SDMMC host driver for SD card communication
#include "sd.h"

static sdmmc_card_t *card;
const char sd_mount_point[] = SD_MOUNT_POINT;
static bool sd_initialized = false; // Flag to track if SD card has been initialized

bool sd_create(const char *filename)
{
    FILE *file = fopen(filename, "wb");
    if (!file)
    {
        printf("Failed to create file: %s\n", filename);
        return false;
    }
    fclose(file);
    return true;
}

void sd_deinit(void)
{
    if (sd_initialized)
    {
        const esp_err_t err = esp_vfs_fat_sdcard_unmount(sd_mount_point, card);
        if (err != ESP_OK)
        {
            printf("Failed to unmount SD card (%s)\n", esp_err_to_name(err));
        }
        sd_initialized = false;
    }
}

bool sd_file_close(FILE *file)
{
    return file && fclose(file) == 0;
}

FILE *sd_file_open(const char *filename, const char *mode)
{
    return fopen(filename, mode);
}

bool sd_file_read(FILE *file, void *data, size_t size)
{
    if (!file || !data)
    {
        printf("Invalid file pointer or data buffer provided for reading\n");
        return false;
    }
    return fread(data, 1, size, file) == size;
}

bool sd_file_seek(FILE *file, long offset, int whence)
{
    if (!file)
    {
        printf("Invalid file pointer provided for seeking\n");
        return false;
    }
    return fseek(file, offset, whence) == 0;
}

bool sd_file_write(FILE *file, const void *data, size_t size)
{
    if (!file || !data)
    {
        printf("Invalid file pointer or data buffer provided for writing\n");
        return false;
    }
    return fwrite(data, 1, size, file) == size;
}

bool sd_format_card(void)
{
    const esp_err_t err = esp_vfs_fat_sdcard_format(sd_mount_point, card);
    if (err != ESP_OK)
    {
        printf("Failed to format FATFS (%s)\n", esp_err_to_name(err));
        return false;
    }
    return true;
}

bool sd_init(void)
{
    if (sd_initialized)
    {
        return true;
    }

    esp_vfs_fat_sdmmc_mount_config_t mount_config = {
        .format_if_mount_failed = false,
        .max_files = 5,
        .allocation_unit_size = 16 * 1024,
    };

    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    host.slot = SDMMC_HOST_SLOT_0;
    host.max_freq_khz = 10000;

    sdmmc_slot_config_t slot_config = SDMMC_SLOT_CONFIG_DEFAULT();
    slot_config.clk = GPIO_NUM_43;
    slot_config.cmd = GPIO_NUM_44;
    slot_config.d0 = GPIO_NUM_39;
    slot_config.width = 1;
    slot_config.flags |= SDMMC_SLOT_FLAG_INTERNAL_PULLUP;

    const esp_err_t err = esp_vfs_fat_sdmmc_mount(sd_mount_point, &host, &slot_config, &mount_config, &card);
    if (err != ESP_OK)
    {
        if (err == ESP_FAIL)
        {
            printf("Failed to mount filesystem. "
                   "If you want the card to be formatted, set the EXAMPLE_FORMAT_IF_MOUNT_FAILED menuconfig option.");
        }
        else
        {
            printf("Failed to initialize the card (%s). "
                   "Make sure SD card lines have pull-up resistors in place.",
                   esp_err_to_name(err));
        }
        return false;
    }
    sd_initialized = true;
    return true;
}

size_t sd_read(const char *filename, void *data, size_t size)
{
    size_t success_size = 0;
    FILE *file = fopen(filename, "rb");
    if (!file)
    {
        printf("Failed to open file for reading: %s\n", filename);
        return 0;
    }
    success_size = fread(data, 1, size, file);
    fclose(file);
    return success_size;
}

size_t sd_size(const char *read_filename)
{
    size_t read_success_size = 0;
    size_t size = 0;
    FILE *read_file = fopen(read_filename, "rb");
    if (!read_file)
    {
        printf("Failed to open file for reading: %s\n", read_filename);
        return 0;
    }
    uint8_t buffer[1024];
    while ((read_success_size = fread(buffer, 1, sizeof(buffer), read_file)) > 0)
    {
        size += read_success_size;
    }
    fclose(read_file);
    return size;
}

bool sd_write(const char *filename, const void *data, size_t size, const char *mode)
{
    size_t success_size = 0;
    FILE *file = fopen(filename, mode);
    if (!file)
    {
        printf("Failed to open file for writing: %s\n", filename);
        return false;
    }
    success_size = fwrite(data, 1, size, file);
    fclose(file);
    return success_size == size;
}