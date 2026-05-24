#include "storage.h"

#include "sdcard.h"

#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <sys/stat.h>

#define STORAGE_ROOT "/sdcard"
#define STORAGE_PATH_MAX 512
#define STORAGE_NAME_MAX_LEN 256

static bool storage_ensure_mounted(void)
{
    return sdcard_is_mounted() || sdcard_mount() == ESP_OK;
}

static bool storage_build_path(const char *filename, char *path, size_t path_size)
{
    int written = 0;

    if (filename == NULL || filename[0] == '\0' || path == NULL || path_size == 0)
    {
        return false;
    }

    if (strncmp(filename, STORAGE_ROOT, strlen(STORAGE_ROOT)) == 0)
    {
        written = snprintf(path, path_size, "%s", filename);
    }
    else if (filename[0] == '/')
    {
        written = snprintf(path, path_size, STORAGE_ROOT "%s", filename);
    }
    else
    {
        written = snprintf(path, path_size, STORAGE_ROOT "/%s", filename);
    }

    return written > 0 && (size_t)written < path_size;
}

static bool storage_ensure_parent_dirs(const char *full_path)
{
    char path[STORAGE_PATH_MAX];
    size_t root_len = strlen(STORAGE_ROOT);

    if (full_path == NULL)
    {
        return false;
    }

    if (snprintf(path, sizeof(path), "%s", full_path) >= (int)sizeof(path))
    {
        return false;
    }

    for (char *cursor = path + root_len + 1; *cursor != '\0'; ++cursor)
    {
        if (*cursor != '/')
        {
            continue;
        }

        *cursor = '\0';
        if (mkdir(path, 0775) != 0 && errno != EEXIST)
        {
            *cursor = '/';
            return false;
        }
        *cursor = '/';
    }

    return true;
}

static bool storage_pattern_match(const char *pattern, const char *text)
{
    const char *star = NULL;
    const char *match = NULL;

    if (pattern == NULL || text == NULL)
    {
        return false;
    }

    while (*text != '\0')
    {
        if (*pattern == '*')
        {
            star = pattern++;
            match = text;
            continue;
        }

        if (*pattern == '?' || *pattern == *text)
        {
            ++pattern;
            ++text;
            continue;
        }

        if (star != NULL)
        {
            pattern = star + 1;
            text = ++match;
            continue;
        }

        return false;
    }

    while (*pattern == '*')
    {
        ++pattern;
    }

    return *pattern == '\0';
}

size_t storage_file_read(const char *filename, void *buffer, size_t buffer_size)
{
    FILE *file = NULL;
    size_t bytes_read = 0;

    if (buffer == NULL || buffer_size == 0)
    {
        return 0;
    }

    file = (FILE *)storage_file_open(filename);
    if (file == NULL)
    {
        return 0;
    }

    bytes_read = fread(buffer, 1, buffer_size, file);
    fclose(file);
    return bytes_read;
}

size_t storage_file_size(const char *filename)
{
    char path[STORAGE_PATH_MAX];
    struct stat file_stat = {0};

    if (!storage_ensure_mounted() || !storage_build_path(filename, path, sizeof(path)))
    {
        return 0;
    }

    if (stat(path, &file_stat) != 0 || file_stat.st_size < 0)
    {
        return 0;
    }

    return (size_t)file_stat.st_size;
}

bool storage_file_write(const char *filename, const void *buffer, size_t buffer_size)
{
    FILE *file = NULL;
    bool success = false;

    if (buffer == NULL && buffer_size > 0)
    {
        return false;
    }

    file = (FILE *)storage_file_write_open(filename);
    if (file == NULL)
    {
        return false;
    }

    success = fwrite(buffer, 1, buffer_size, file) == buffer_size;
    fclose(file);
    return success;
}

size_t storage_file_read_chunk(const char *filename, void *buffer, size_t buffer_size, size_t offset)
{
    FILE *file = NULL;
    size_t bytes_read = 0;

    if (buffer == NULL || buffer_size == 0 || offset > LONG_MAX)
    {
        return 0;
    }

    file = (FILE *)storage_file_open(filename);
    if (file == NULL)
    {
        return 0;
    }

    if (fseek(file, (long)offset, SEEK_SET) == 0)
    {
        bytes_read = fread(buffer, 1, buffer_size, file);
    }

    fclose(file);
    return bytes_read;
}

uint16_t storage_file_list(const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count)
{
    char full_pattern[STORAGE_PATH_MAX];
    char directory_path[STORAGE_PATH_MAX];
    DIR *dir = NULL;
    struct dirent *entry = NULL;
    const char *effective_pattern = (pattern != NULL && pattern[0] != '\0') ? pattern : "*";
    const char *name_pattern = NULL;
    uint16_t count = 0;
    uint16_t skipped = 0;

    if (max_count == 0 || filenames == NULL)
    {
        return 0;
    }

    if (!storage_ensure_mounted() ||
        !storage_build_path(effective_pattern, full_pattern, sizeof(full_pattern)) ||
        snprintf(directory_path, sizeof(directory_path), "%s", full_pattern) >= (int)sizeof(directory_path))
    {
        return 0;
    }

    char *last_slash = strrchr(directory_path, '/');
    if (last_slash == NULL)
    {
        return 0;
    }

    name_pattern = last_slash + 1;
    if (*name_pattern == '\0')
    {
        name_pattern = "*";
    }
    *last_slash = '\0';

    dir = opendir(directory_path[0] != '\0' ? directory_path : STORAGE_ROOT);
    if (dir == NULL)
    {
        return 0;
    }

    while ((entry = readdir(dir)) != NULL)
    {
        char entry_path[STORAGE_PATH_MAX];
        struct stat entry_stat = {0};
        const char *relative_dir = NULL;

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
        {
            continue;
        }

        if (!storage_pattern_match(name_pattern, entry->d_name))
        {
            continue;
        }

        if (snprintf(entry_path, sizeof(entry_path), "%s/%s",
                     directory_path[0] != '\0' ? directory_path : STORAGE_ROOT, entry->d_name) >=
            (int)sizeof(entry_path))
        {
            continue;
        }

        if (stat(entry_path, &entry_stat) != 0 || !S_ISREG(entry_stat.st_mode))
        {
            continue;
        }

        if (skipped < skip)
        {
            ++skipped;
            continue;
        }

        relative_dir = directory_path;
        if (strncmp(relative_dir, STORAGE_ROOT, strlen(STORAGE_ROOT)) == 0)
        {
            relative_dir += strlen(STORAGE_ROOT);
        }

        if (*relative_dir == '\0')
        {
            size_t entry_name_len = strlen(entry->d_name);

            if (entry_name_len >= STORAGE_NAME_MAX_LEN)
            {
                continue;
            }

            memcpy(filenames[count], entry->d_name, entry_name_len + 1);
        }
        else
        {
            const char *relative_name = relative_dir[0] == '/' ? relative_dir + 1 : relative_dir;
            size_t relative_name_len = strlen(relative_name);
            size_t entry_name_len = strlen(entry->d_name);
            size_t required_len = relative_name_len + 1 + entry_name_len + 1;

            if (required_len > STORAGE_NAME_MAX_LEN)
            {
                continue;
            }

            memcpy(filenames[count], relative_name, relative_name_len);
            filenames[count][relative_name_len] = '/';
            memcpy(&filenames[count][relative_name_len + 1], entry->d_name, entry_name_len);
            filenames[count][required_len - 1] = '\0';
        }

        ++count;
        if (count >= max_count)
        {
            break;
        }
    }

    closedir(dir);
    return count;
}

void *storage_file_open(const char *filename)
{
    char path[STORAGE_PATH_MAX];

    if (!storage_ensure_mounted() || !storage_build_path(filename, path, sizeof(path)))
    {
        return NULL;
    }

    return fopen(path, "rb");
}

void *storage_file_write_open(const char *filename)
{
    char path[STORAGE_PATH_MAX];

    if (!storage_ensure_mounted() || !storage_build_path(filename, path, sizeof(path)) ||
        !storage_ensure_parent_dirs(path))
    {
        return NULL;
    }

    return fopen(path, "wb");
}

void storage_file_close(void *handle)
{
    if (handle != NULL)
    {
        fclose((FILE *)handle);
    }
}

size_t storage_file_read_file_chunk(void *handle, void *buffer, size_t buffer_size)
{
    if (handle == NULL || buffer == NULL || buffer_size == 0)
    {
        return 0;
    }

    return fread(buffer, 1, buffer_size, (FILE *)handle);
}

bool storage_file_write_file_chunk(void *handle, const void *data, size_t size)
{
    if (handle == NULL || (data == NULL && size > 0))
    {
        return false;
    }

    return fwrite(data, 1, size, (FILE *)handle) == size;
}