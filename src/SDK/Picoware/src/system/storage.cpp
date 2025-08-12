#include "../system/storage.hpp"
#include "../system/drivers/fat32.h"

Storage::Storage()
{
    fat32_init();
}

Storage::~Storage()
{
    // nothing to do
}

bool Storage::read(const char *filePath, void *buffer, size_t size)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        return false;
    }
    size_t bytes_read;
    const bool status = fat32_read(&file, buffer, size, &bytes_read) == FAT32_OK;
    fat32_close(&file);
    return status && bytes_read == size;
}

bool Storage::remove(const char *filePath)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
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
        return false;
    }
    const bool status = fat32_rename(oldPath, newPath) == FAT32_OK;
    fat32_close(&file);
    return status;
}

bool Storage::write(const char *filePath, const void *data, size_t size)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        if (fat32_create(&file, filePath) != FAT32_OK)
        {
            return false;
        }
    }
    size_t bytes_written;
    const bool status = fat32_write(&file, data, size, &bytes_written) == FAT32_OK;
    fat32_close(&file);
    return status && bytes_written == size;
}
