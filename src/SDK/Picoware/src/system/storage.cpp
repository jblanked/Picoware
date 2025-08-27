#include "../system/storage.hpp"
#include "../system/drivers/fat32.h"
#include "stdio.h"

Storage::Storage()
{
    fat32_init();
}

Storage::~Storage()
{
    // nothing to do
}

bool Storage::createFile(const char *filePath)
{
    fat32_file_t file;
    bool status = true;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        if (fat32_create(&file, filePath) != FAT32_OK)
        {
            printf("Failed to create file.\n");
            status = false;
        }
    }
    fat32_close(&file);
    return status;
}

bool Storage::createDirectory(const char *dirPath)
{
    fat32_file_t dir;
    if (fat32_open(&dir, dirPath) == FAT32_OK)
    {
        // Directory already exists, check if it's actually a directory
        if (dir.attributes & FAT32_ATTR_DIRECTORY)
        {
            fat32_close(&dir);
            return true;
        }
        else
        {
            fat32_close(&dir);
            printf("Path exists but is not a directory.\n");
            return false;
        }
    }

    // Directory doesn't exist, try to create it
    if (fat32_dir_create(&dir, dirPath) != FAT32_OK)
    {
        printf("Failed to create directory.\n");
        return false;
    }
    fat32_close(&dir);
    return true;
}

uint32_t Storage::getFileSize(const char *filePath)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        printf("Failed to open file for reading.\n");
        return 0;
    }
    uint32_t size = fat32_size(&file);
    fat32_close(&file);
    return size;
}

bool Storage::read(const char *filePath, void *buffer, size_t size)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        printf("Failed to open file for reading.\n");
        return false;
    }
    size_t bytes_read;
    const bool status = fat32_read(&file, buffer, size, &bytes_read) == FAT32_OK;
    fat32_close(&file);
    return status;
}

bool Storage::read(const char *filePath, void *buffer, size_t size, size_t *bytes_read)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        if (bytes_read)
            *bytes_read = 0;
        printf("Failed to open file for reading.\n");
        return false;
    }
    const bool status = fat32_read(&file, buffer, size, bytes_read) == FAT32_OK;
    fat32_close(&file);
    return status;
}

bool Storage::remove(const char *filePath)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        printf("Failed to open file for removal.\n");
        return true;
    }
    const bool status = fat32_delete(filePath) == FAT32_OK;
    fat32_close(&file);
    return status;
}

bool Storage::rename(const char *oldPath, const char *newPath)
{
    fat32_file_t file;
    if (fat32_open(&file, oldPath) != FAT32_OK)
    {
        printf("Failed to open file for renaming.\n");
        return false;
    }
    const bool status = fat32_rename(oldPath, newPath) == FAT32_OK;
    fat32_close(&file);
    return status;
}

bool Storage::write(const char *filePath, const void *data, size_t size, bool overwrite)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        if (!createFile(filePath))
        {
            printf("Failed to create file.\n");
            return false;
        }
    }
    else
    {
        if (overwrite)
        {
            if (fat32_delete(filePath) != FAT32_OK)
            {
                printf("Failed to delete existing file.\n");
                return false;
            }
            if (!createFile(filePath))
            {
                printf("Failed to create new file.\n");
                return false;
            }
            if (fat32_open(&file, filePath) != FAT32_OK)
            {
                printf("Failed to open new file.\n");
                return false;
            }
        }
    }
    size_t bytes_written;
    const bool status = fat32_write(&file, data, size, &bytes_written) == FAT32_OK;
    fat32_close(&file);
    return status && bytes_written == size;
}
