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

bool Storage::createDirectory(const char *dirPath)
{
    fat32_file_t dir;
    fat32_entry_t entry;
    if (fat32_dir_read(&dir, &entry) != FAT32_OK)
    {
        if (fat32_dir_create(&dir, dirPath) != FAT32_OK)
        {
            return false;
        }
    }
    fat32_close(&dir);
    return true;
}

uint32_t Storage::getFileSize(const char *filePath)
{
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
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
