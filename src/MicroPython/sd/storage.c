#include "storage.h"
#include "fat32.h"
#include <stdlib.h>
#include <ctype.h>
#include "py/runtime.h"

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

size_t storage_file_read(const char *filename, void *buffer, size_t buffer_size)
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
    fat32_error_t err = fat32_open(&file, filename);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open file for reading: %s\n", fat32_error_string(err));
        return 0;
    }
    size_t bytes_read = 0;
    bool status = fat32_read(&file, buffer, buffer_size, &bytes_read) == FAT32_OK;
    fat32_close(&file);
    return status ? bytes_read : 0;
}

size_t storage_file_size(const char *filename)
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
    fat32_error_t err = fat32_open(&file, filename);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open file for size retrieval: %s\n", fat32_error_string(err));
        return 0;
    }
    const uint32_t size = (file.attributes & FAT32_ATTR_DIRECTORY) ? 0 : fat32_size(&file);
    fat32_close(&file);
    return size;
}

bool storage_file_write(const char *filename, const void *buffer, size_t buffer_size)
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
    fat32_error_t err = fat32_open(&file, filename);
    if (err != FAT32_OK)
    {
        err = fat32_create(&file, filename);
        if (err != FAT32_OK)
        {
            PRINT("Failed to open and create file: %s\n", fat32_error_string(err));
            return false;
        }
    }
    bool overwrite = true; // For now, we always overwrite. We can add an option later if needed.
    if (overwrite)
    {
        if (fat32_delete(filename) != FAT32_OK)
        {
            PRINT("Failed to delete existing file.\n");
            return false;
        }
        if (fat32_create(&file, filename) != FAT32_OK)
        {
            PRINT("Failed to create new file.\n");
            return false;
        }
        if (fat32_open(&file, filename) != FAT32_OK)
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
    bool status = fat32_write(&file, buffer, buffer_size, &bytes_written) == FAT32_OK;
    fat32_close(&file);
    return status && bytes_written == buffer_size;
}

size_t storage_file_read_chunk(const char *filename, void *buffer, size_t buffer_size, size_t offset)
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
    fat32_error_t err = fat32_open(&file, filename);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open file for chunk read: %s\n", fat32_error_string(err));
        return 0;
    }
    if (offset > 0)
    {
        err = fat32_seek(&file, (uint32_t)offset);
        if (err != FAT32_OK)
        {
            PRINT("Failed to seek: %s\n", fat32_error_string(err));
            fat32_close(&file);
            return 0;
        }
    }
    size_t bytes_read = 0;
    fat32_read(&file, buffer, buffer_size, &bytes_read);
    fat32_close(&file);
    return bytes_read;
}

static bool storage_glob_match(const char *pattern, const char *str)
{
    while (*pattern)
    {
        if (*pattern == '*')
        {
            while (*pattern == '*')
                pattern++;
            if (*pattern == '\0')
                return true;
            while (*str)
            {
                if (storage_glob_match(pattern, str))
                    return true;
                str++;
            }
            return false;
        }
        if (*pattern == '?' || tolower((unsigned char)*pattern) == tolower((unsigned char)*str))
        {
            pattern++;
            str++;
        }
        else
        {
            return false;
        }
    }
    return *str == '\0';
}

uint16_t storage_file_list(const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count)
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

    char dir_path[256];
    const char *name_glob = NULL;
    if (pattern && pattern[0])
    {
        const char *last_slash = strrchr(pattern, '/');
        if (last_slash)
        {
            size_t dir_len = (size_t)(last_slash - pattern) + 1; // include trailing '/'
            if (dir_len >= sizeof(dir_path))
                dir_len = sizeof(dir_path) - 1;
            strncpy(dir_path, pattern, dir_len);
            dir_path[dir_len] = '\0';
            // strip trailing slash for fat32_open
            if (dir_len > 1)
                dir_path[dir_len - 1] = '\0';
            name_glob = last_slash + 1;
        }
        else
        {
            // No directory component — use current dir
            dir_path[0] = '.';
            dir_path[1] = '\0';
            name_glob = pattern;
        }
    }
    else
    {
        dir_path[0] = '.';
        dir_path[1] = '\0';
    }

    fat32_file_t dir;
    fat32_error_t err = fat32_open(&dir, dir_path);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open directory: %s\n", fat32_error_string(err));
        return 0;
    }
    fat32_entry_t entry;
    uint16_t skipped = 0;
    uint16_t num_files = 0;
    while (fat32_dir_read(&dir, &entry) == FAT32_OK && entry.filename[0])
    {
        if (entry.filename[0] == '.' || (entry.attr & FAT32_ATTR_DIRECTORY))
            continue;
        if (name_glob && name_glob[0] && !storage_glob_match(name_glob, entry.filename))
            continue;
        if (skipped < skip)
        {
            skipped++;
            continue;
        }
        if (num_files >= max_count)
            break;
        strncpy(filenames[num_files], entry.filename, 255);
        filenames[num_files][255] = '\0';
        num_files++;
    }
    fat32_close(&dir);
    return num_files;
}

void *storage_file_open(const char *filename)
{
    if (!fat32_is_mounted())
    {
        fat32_error_t err = fat32_mount();
        if (err != FAT32_OK)
        {
            PRINT("Failed to mount SD card: %s\n", fat32_error_string(err));
            return NULL;
        }
    }
    fat32_file_t *file = (fat32_file_t *)m_malloc(sizeof(fat32_file_t));
    if (!file)
    {
        PRINT("Failed to allocate file handle\n");
        return NULL;
    }
    fat32_error_t err = fat32_open(file, filename);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open file: %s\n", fat32_error_string(err));
        m_free(file);
        return NULL;
    }
    return file;
}

void *storage_file_write_open(const char *filename)
{
    if (!fat32_is_mounted())
    {
        fat32_error_t err = fat32_mount();
        if (err != FAT32_OK)
        {
            PRINT("Failed to mount SD card: %s\n", fat32_error_string(err));
            return NULL;
        }
    }
    fat32_file_t *file = (fat32_file_t *)m_malloc(sizeof(fat32_file_t));
    if (!file)
    {
        PRINT("Failed to allocate file handle\n");
        return NULL;
    }
    /* Truncate-and-create semantics (equivalent to FA_CREATE_ALWAYS | FA_WRITE) */
    fat32_delete(filename); /* ignore error — file may not exist yet */
    fat32_error_t err = fat32_create(file, filename);
    if (err != FAT32_OK)
    {
        PRINT("Failed to create file for writing: %s\n", fat32_error_string(err));
        m_free(file);
        return NULL;
    }
    err = fat32_open(file, filename);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open created file: %s\n", fat32_error_string(err));
        m_free(file);
        return NULL;
    }
    return file;
}

void storage_file_close(void *handle)
{
    if (handle)
    {
        fat32_file_t *file = (fat32_file_t *)handle;
        fat32_close(file);
        m_free(file);
    }
}

size_t storage_file_read_file_chunk(void *handle, void *buffer, size_t buffer_size)
{
    if (!handle)
        return 0;
    size_t bytes_read = 0;
    fat32_read((fat32_file_t *)handle, buffer, buffer_size, &bytes_read);
    return bytes_read;
}

bool storage_file_write_file_chunk(void *handle, const void *data, size_t size)
{
    if (!handle)
        return false;
    size_t bytes_written = 0;
    fat32_error_t err = fat32_write((fat32_file_t *)handle, data, size, &bytes_written);
    return err == FAT32_OK && bytes_written == size;
}