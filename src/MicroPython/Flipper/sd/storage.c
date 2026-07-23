#include "storage.h"
#include "sd_mp.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "py/runtime.h"
#include "py/stream.h"
#include "extmod/vfs.h"

#define STORAGE_ROOT "/sd"
#define STORAGE_PATH_MAX 512
#define STORAGE_NAME_MAX_LEN 256

typedef struct
{
    mp_obj_t file_obj;
} storage_file_handle_t;

static bool storage_ensure_mounted(void)
{
    return sd_storage_mount_if_needed();
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

    // Mkdir each path component
    for (char *cursor = path + root_len + 1; *cursor != '\0'; ++cursor)
    {
        if (*cursor != '/')
        {
            continue;
        }

        *cursor = '\0';

        if (strcmp(path, STORAGE_ROOT) != 0)
        {
            nlr_buf_t nlr;
            if (nlr_push(&nlr) == 0)
            {
                mp_obj_t dir_obj = mp_obj_new_str(path, strlen(path));
                mp_vfs_mkdir(dir_obj);
                nlr_pop();
            }
            else
            {
                nlr_pop();
            }
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
    void *handle = NULL;
    size_t bytes_read = 0;

    if (buffer == NULL || buffer_size == 0)
    {
        return 0;
    }

    handle = storage_file_open(filename);
    if (handle == NULL)
    {
        return 0;
    }

    bytes_read = storage_file_read_file_chunk(handle, buffer, buffer_size);
    storage_file_close(handle);
    return bytes_read;
}

size_t storage_file_size(const char *filename)
{
    char path[STORAGE_PATH_MAX];
    uint32_t mode = 0;
    uint32_t size = 0;

    if (!storage_ensure_mounted() ||
        !storage_build_path(filename, path, sizeof(path)))
    {
        return 0;
    }

    mp_obj_t path_obj = mp_obj_new_str(path, strlen(path));
    nlr_buf_t nlr;

    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t stat_result = mp_vfs_stat(path_obj);
        nlr_pop();
        mp_obj_tuple_t *t = MP_OBJ_TO_PTR(stat_result);
        mode = MP_OBJ_SMALL_INT_VALUE(t->items[0]);
        size = MP_OBJ_SMALL_INT_VALUE(t->items[5]);
    }
    else
    {
        nlr_pop();
        return 0;
    }

    // Regular files only
    if (mode != MP_S_IFREG)
    {
        return 0;
    }

    return (size_t)size;
}

bool storage_file_write(const char *filename, const void *buffer, size_t buffer_size)
{
    storage_file_handle_t *handle = NULL;
    bool success = false;

    if (buffer == NULL && buffer_size > 0)
    {
        return false;
    }

    handle = (storage_file_handle_t *)storage_file_write_open(filename);
    if (handle == NULL)
    {
        return false;
    }

    success = storage_file_write_file_chunk(handle, buffer, buffer_size);
    storage_file_close(handle);
    return success;
}

size_t storage_file_read_chunk(const char *filename, void *buffer,
                               size_t buffer_size, size_t offset)
{
    storage_file_handle_t *handle = NULL;
    size_t bytes_read = 0;

    if (buffer == NULL || buffer_size == 0)
    {
        return 0;
    }

    handle = (storage_file_handle_t *)storage_file_open(filename);
    if (handle == NULL)
    {
        return 0;
    }

    int errcode = 0;
    mp_stream_seek(handle->file_obj, (mp_off_t)offset, MP_SEEK_SET, &errcode);
    if (errcode == 0)
    {
        bytes_read = storage_file_read_file_chunk(handle, buffer, buffer_size);
    }

    storage_file_close(handle);
    return bytes_read;
}

uint16_t storage_file_list(const char *pattern,
                           char filenames[][256],
                           uint16_t skip,
                           uint16_t max_count)
{
    char full_pattern[STORAGE_PATH_MAX];
    char directory_path[STORAGE_PATH_MAX];
    const char *effective_pattern =
        (pattern != NULL && pattern[0] != '\0') ? pattern : "*";
    const char *name_pattern = NULL;
    uint16_t count = 0;
    uint16_t skipped = 0;

    if (max_count == 0 || filenames == NULL)
    {
        return 0;
    }

    if (!storage_ensure_mounted() ||
        !storage_build_path(effective_pattern, full_pattern, sizeof(full_pattern)) ||
        snprintf(directory_path, sizeof(directory_path), "%s", full_pattern) >=
            (int)sizeof(directory_path))
    {
        return 0;
    }

    // Split path and filename pattern
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

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        const char *list_dir = directory_path[0] != '\0' ? directory_path : STORAGE_ROOT;
        mp_obj_t dir_obj = mp_obj_new_str(list_dir, strlen(list_dir));
        mp_obj_t ilist_args[1] = {dir_obj};
        mp_obj_t iter = mp_vfs_ilistdir(1, ilist_args);

        if (iter != mp_const_none)
        {
            mp_obj_t entry;
            while ((entry = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION)
            {
                mp_obj_t *items;
                size_t len;
                mp_obj_tuple_get(entry, &len, &items);

                // Need at least (name, type)
                if (len < 2)
                {
                    continue;
                }

                const char *entry_name = mp_obj_str_get_str(items[0]);
                mp_int_t entry_type = MP_OBJ_SMALL_INT_VALUE(items[1]);

                // Skip dot entries
                if (strcmp(entry_name, ".") == 0 ||
                    strcmp(entry_name, "..") == 0)
                {
                    continue;
                }

                // Files only
                if (entry_type != MP_S_IFREG)
                {
                    continue;
                }

                if (!storage_pattern_match(name_pattern, entry_name))
                {
                    continue;
                }

                if (skipped < skip)
                {
                    ++skipped;
                    continue;
                }

                size_t entry_name_len = strlen(entry_name);

                if (entry_name_len >= STORAGE_NAME_MAX_LEN)
                {
                    continue;
                }
                memcpy(filenames[count], entry_name, entry_name_len + 1);

                ++count;
                if (count >= max_count)
                {
                    break;
                }
            }
        }
        nlr_pop();
    }
    else
    {
        nlr_pop();
        return 0;
    }

    return count;
}

void *storage_file_open(const char *filename)
{
    char path[STORAGE_PATH_MAX];

    if (!storage_ensure_mounted() ||
        !storage_build_path(filename, path, sizeof(path)))
    {
        return NULL;
    }

    mp_obj_t path_obj = mp_obj_new_str(path, strlen(path));
    mp_obj_t mode_obj = MP_OBJ_NEW_QSTR(MP_QSTR_rb);

    nlr_buf_t nlr;
    storage_file_handle_t *handle = NULL;

    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t open_args[2] = {path_obj, mode_obj};
        mp_obj_t file_obj = mp_vfs_open(2, open_args,
                                        (mp_map_t *)&mp_const_empty_map);
        nlr_pop();

        handle = (storage_file_handle_t *)m_malloc0(sizeof(storage_file_handle_t));
        if (handle != NULL)
        {
            handle->file_obj = file_obj;
        }
        return handle;
    }

    nlr_pop();
    return NULL;
}

void *storage_file_write_open(const char *filename)
{
    char path[STORAGE_PATH_MAX];

    if (!storage_ensure_mounted() ||
        !storage_build_path(filename, path, sizeof(path)) ||
        !storage_ensure_parent_dirs(path))
    {
        return NULL;
    }

    mp_obj_t path_obj = mp_obj_new_str(path, strlen(path));
    mp_obj_t mode_obj = MP_OBJ_NEW_QSTR(MP_QSTR_wb);

    nlr_buf_t nlr;
    storage_file_handle_t *handle = NULL;

    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t open_args[2] = {path_obj, mode_obj};
        mp_obj_t file_obj = mp_vfs_open(2, open_args,
                                        (mp_map_t *)&mp_const_empty_map);
        nlr_pop();

        handle = (storage_file_handle_t *)m_malloc0(sizeof(storage_file_handle_t));
        if (handle != NULL)
        {
            handle->file_obj = file_obj;
        }
        return handle;
    }

    nlr_pop();
    return NULL;
}

void storage_file_close(void *handle)
{
    if (handle == NULL)
    {
        return;
    }

    storage_file_handle_t *h = (storage_file_handle_t *)handle;
    mp_stream_close(h->file_obj);
    m_free(h);
}

size_t storage_file_read_file_chunk(void *handle, void *buffer,
                                    size_t buffer_size)
{
    if (handle == NULL || buffer == NULL || buffer_size == 0)
    {
        return 0;
    }

    storage_file_handle_t *h = (storage_file_handle_t *)handle;
    int errcode = 0;
    mp_uint_t n = mp_stream_rw(h->file_obj, buffer, buffer_size, &errcode,
                               MP_STREAM_RW_READ);
    return (size_t)n;
}

bool storage_file_write_file_chunk(void *handle, const void *data,
                                   size_t size)
{
    if (handle == NULL || (data == NULL && size > 0))
    {
        return false;
    }

    storage_file_handle_t *h = (storage_file_handle_t *)handle;
    int errcode = 0;
    mp_uint_t n = mp_stream_rw(h->file_obj, (void *)data, size, &errcode,
                               MP_STREAM_RW_WRITE);
    return n == size;
}
