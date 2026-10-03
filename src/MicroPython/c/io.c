#include "io.h"

#include <string.h>

#if defined(CROWPANEL_WATCH_2_01)
#include <dirent.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

#define C_IO_PATH_MAX 512

typedef struct
{
    DIR *handle;
    char path[C_IO_PATH_MAX];
} c_io_dir_t;

static bool c_io_resolve_path(const char *path, char resolved[C_IO_PATH_MAX])
{
    return storage_resolve_path(path, resolved, C_IO_PATH_MAX);
}

int fs_load(void)
{
    return LFS_ERR_OK;
}

int fs_unload(void)
{
    return LFS_ERR_OK;
}

int fs_mount(void)
{
    return LFS_ERR_OK;
}

int fs_unmount(void)
{
    return LFS_ERR_OK;
}

int fs_remove(const char *path)
{
    char resolved[C_IO_PATH_MAX];
    return c_io_resolve_path(path, resolved) && remove(resolved) == 0 ? LFS_ERR_OK : -1;
}

int fs_rename(const char *oldpath, const char *newpath)
{
    char old_resolved[C_IO_PATH_MAX];
    char new_resolved[C_IO_PATH_MAX];
    return c_io_resolve_path(oldpath, old_resolved) &&
                   c_io_resolve_path(newpath, new_resolved) &&
                   rename(old_resolved, new_resolved) == 0
               ? LFS_ERR_OK
               : -1;
}

int fs_stat(const char *path, struct lfs_info *info)
{
    char resolved[C_IO_PATH_MAX];
    struct stat file_stat;
    if (info == NULL || !c_io_resolve_path(path, resolved) ||
        stat(resolved, &file_stat) != 0)
    {
        return -1;
    }

    info->type = S_ISDIR(file_stat.st_mode) ? LFS_TYPE_DIR : LFS_TYPE_REG;
    info->size = file_stat.st_size < 0 ? 0 : (uint32_t)file_stat.st_size;
    strncpy(info->name, resolved, sizeof(info->name) - 1);
    info->name[sizeof(info->name) - 1] = '\0';
    return LFS_ERR_OK;
}

int fs_getattr(const char *path, uint8_t type, void *buffer, uint32_t size)
{
    (void)path;
    (void)type;
    (void)buffer;
    (void)size;
    return -1;
}

int fs_setattr(const char *path, uint8_t type, const void *buffer, uint32_t size)
{
    (void)path;
    (void)type;
    (void)buffer;
    (void)size;
    return -1;
}

int fs_removeattr(const char *path, uint8_t type)
{
    (void)path;
    (void)type;
    return -1;
}

int fs_file_open(lfs_file_t *file, const char *path, int flags)
{
    char resolved[C_IO_PATH_MAX];
    if (file == NULL || !c_io_resolve_path(path, resolved))
    {
        return -1;
    }

    const int access = flags & 0xff;
    int open_flags;
    const char *mode;
    switch (access)
    {
    case LFS_O_RDONLY:
        open_flags = O_RDONLY;
        mode = "rb";
        break;
    case LFS_O_WRONLY:
        open_flags = O_WRONLY;
        mode = "wb";
        break;
    case LFS_O_RDWR:
        open_flags = O_RDWR;
        mode = "r+b";
        break;
    default:
        return -1;
    }

    if (flags & LFS_O_CREAT)
    {
        open_flags |= O_CREAT;
    }
    if (flags & LFS_O_EXCL)
    {
        open_flags |= O_EXCL;
    }
    if (flags & LFS_O_TRUNC)
    {
        open_flags |= O_TRUNC;
        mode = access == LFS_O_RDWR ? "w+b" : "wb";
    }
    if (flags & LFS_O_APPEND)
    {
        open_flags |= O_APPEND;
        mode = access == LFS_O_RDWR ? "a+b" : "ab";
    }

    const int fd = open(resolved, open_flags, 0666);
    if (fd < 0)
    {
        return -1;
    }
    FILE *handle = fdopen(fd, mode);
    if (handle == NULL)
    {
        close(fd);
        return -1;
    }
    *file = handle;
    return LFS_ERR_OK;
}

int fs_file_close(lfs_file_t *file)
{
    if (file == NULL || *file == NULL)
    {
        return -1;
    }
    FILE *handle = *file;
    *file = NULL;
    return fclose(handle) == 0 ? LFS_ERR_OK : -1;
}

int fs_file_sync(lfs_file_t *file)
{
    return file != NULL && *file != NULL && fflush(*file) == 0 ? LFS_ERR_OK : -1;
}

lfs_ssize_t fs_file_read(lfs_file_t *file, void *buffer, uint32_t size)
{
    if (file == NULL || *file == NULL || (buffer == NULL && size > 0))
    {
        return -1;
    }
    if (size > INT32_MAX)
    {
        size = INT32_MAX;
    }
    FILE *handle = *file;
    const size_t bytes_read = fread(buffer, 1, size, handle);
    return ferror(handle) ? -1 : (lfs_ssize_t)bytes_read;
}

lfs_ssize_t fs_file_write(lfs_file_t *file, const void *buffer, uint32_t size)
{
    if (file == NULL || *file == NULL || (buffer == NULL && size > 0))
    {
        return -1;
    }
    if (size > INT32_MAX)
    {
        size = INT32_MAX;
    }
    FILE *handle = *file;
    const size_t bytes_written = fwrite(buffer, 1, size, handle);
    return ferror(handle) ? -1 : (lfs_ssize_t)bytes_written;
}

lfs_soff_t fs_file_seek(lfs_file_t *file, lfs_soff_t off, int whence)
{
    if (file == NULL || *file == NULL || fseek(*file, off, whence) != 0)
    {
        return -1;
    }
    const long position = ftell(*file);
    return position < 0 || position > INT32_MAX ? -1 : (lfs_soff_t)position;
}

int fs_mkdir(const char *path)
{
    char resolved[C_IO_PATH_MAX];
    return c_io_resolve_path(path, resolved) && mkdir(resolved, 0775) == 0 ? LFS_ERR_OK : -1;
}

int fs_dir_open(lfs_dir_t *dir, const char *path)
{
    char resolved[C_IO_PATH_MAX];
    if (dir == NULL || !c_io_resolve_path(path, resolved))
    {
        return -1;
    }

    c_io_dir_t *state = calloc(1, sizeof(*state));
    if (state == NULL)
    {
        return -1;
    }
    state->handle = opendir(resolved);
    if (state->handle == NULL)
    {
        free(state);
        return -1;
    }
    memcpy(state->path, resolved, strlen(resolved) + 1);
    *dir = state;
    return LFS_ERR_OK;
}

int fs_dir_close(lfs_dir_t *dir)
{
    if (dir == NULL || *dir == NULL)
    {
        return -1;
    }
    c_io_dir_t *state = *dir;
    *dir = NULL;
    const int result = closedir(state->handle);
    free(state);
    return result == 0 ? LFS_ERR_OK : -1;
}

int fs_dir_read(lfs_dir_t *dir, struct lfs_info *info)
{
    if (dir == NULL || *dir == NULL || info == NULL)
    {
        return -1;
    }
    c_io_dir_t *state = *dir;
    struct dirent *entry;
    while ((entry = readdir(state->handle)) != NULL)
    {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
        {
            continue;
        }

        char entry_path[C_IO_PATH_MAX];
        const size_t path_length = strlen(state->path);
        const char *separator = path_length > 0 && state->path[path_length - 1] == '/' ? "" : "/";
        const int written = snprintf(entry_path, sizeof(entry_path), "%s%s%s",
                                     state->path, separator, entry->d_name);
        struct stat entry_stat;
        if (written < 0 || (size_t)written >= sizeof(entry_path) ||
            stat(entry_path, &entry_stat) != 0)
        {
            continue;
        }

        info->type = S_ISDIR(entry_stat.st_mode) ? LFS_TYPE_DIR : LFS_TYPE_REG;
        info->size = entry_stat.st_size < 0 ? 0 : (uint32_t)entry_stat.st_size;
        strncpy(info->name, entry->d_name, sizeof(info->name) - 1);
        info->name[sizeof(info->name) - 1] = '\0';
        return 1;
    }
    return 0;
}

#else

#ifdef C_STORAGE_ENABLED
static int fs_open_flags(int flags)
{
    return flags & 0xff;
}
#endif

int fs_load(void)
{
#ifdef C_STORAGE_ENABLED
    return FAT32_OK;
#else
    return 0;
#endif
}

int fs_unload(void)
{
#ifdef C_STORAGE_ENABLED
    return FAT32_OK;
#else
    return 0;
#endif
}

int fs_mount(void)
{
#ifdef C_STORAGE_ENABLED
    return fat32_mount();
#else
    return 0;
#endif
}

int fs_unmount(void)
{
#ifdef C_STORAGE_ENABLED
    fat32_unmount();
    return FAT32_OK;
#else
    return 0;
#endif
}

int fs_remove(const char *path)
{
#ifdef C_STORAGE_ENABLED
    return fat32_delete(path) == FAT32_OK ? LFS_ERR_OK : -1;
#else
    return 0;
#endif
}

int fs_rename(const char *oldpath, const char *newpath)
{
#ifdef C_STORAGE_ENABLED
    return fat32_rename(oldpath, newpath) == FAT32_OK ? LFS_ERR_OK : -1;
#else
    return 0;
#endif
}

int fs_stat(const char *path, struct lfs_info *info)
{
#ifdef C_STORAGE_ENABLED
    fat32_file_t file;
    if (fat32_open(&file, path) != FAT32_OK)
        return -1;
    info->type = (file.attributes & FAT32_ATTR_DIRECTORY) ? LFS_TYPE_DIR : LFS_TYPE_REG;
    info->size = file.file_size;
    strncpy(info->name, path, sizeof(info->name) - 1);
    info->name[sizeof(info->name) - 1] = '\0';
    fat32_close(&file);
    return LFS_ERR_OK;
#else
    return 0;
#endif
}

int fs_getattr(const char *path, uint8_t type, void *buffer, uint32_t size)
{
    (void)path;
    (void)type;
    (void)buffer;
    (void)size;
    return -1;
}

int fs_setattr(const char *path, uint8_t type, const void *buffer, uint32_t size)
{
    (void)path;
    (void)type;
    (void)buffer;
    (void)size;
    return -1;
}

int fs_removeattr(const char *path, uint8_t type)
{
    (void)path;
    (void)type;
    return -1;
}

int fs_file_open(lfs_file_t *file, const char *path, int flags)
{
#ifdef C_STORAGE_ENABLED
    int access = fs_open_flags(flags);
    if ((flags & LFS_O_CREAT) || (flags & LFS_O_TRUNC))
    {
        if (flags & LFS_O_EXCL)
        {
            fat32_file_t existing;
            if (fat32_open(&existing, path) == FAT32_OK)
            {
                fat32_close(&existing);
                return -1;
            }
        }
        fat32_delete(path);
        fat32_file_t created;
        if (fat32_create(&created, path) != FAT32_OK || fat32_close(&created) != FAT32_OK ||
            fat32_open(file, path) != FAT32_OK)
            return -1;
    }
    else if (fat32_open(file, path) != FAT32_OK)
    {
        return -1;
    }

    if (access == LFS_O_WRONLY || access == LFS_O_RDWR)
    {
        if (flags & LFS_O_APPEND)
            return fat32_seek(file, file->file_size) == FAT32_OK ? LFS_ERR_OK : -1;
    }
    return LFS_ERR_OK;
#else
    return 0;
#endif
}

int fs_file_close(lfs_file_t *file)
{
#ifdef C_STORAGE_ENABLED
    return fat32_close(file) == FAT32_OK ? LFS_ERR_OK : -1;
#else
    return 0;
#endif
}

int fs_file_sync(lfs_file_t *file)
{
    return fs_file_close(file);
}

lfs_ssize_t fs_file_read(lfs_file_t *file, void *buffer, uint32_t size)
{
#ifdef C_STORAGE_ENABLED
    size_t bytes_read = 0;
    if (fat32_read(file, buffer, size, &bytes_read) != FAT32_OK)
        return -1;
    return (lfs_ssize_t)bytes_read;
#else
    return 0;
#endif
}

lfs_ssize_t fs_file_write(lfs_file_t *file, const void *buffer, uint32_t size)
{
#ifdef C_STORAGE_ENABLED
    size_t bytes_written = 0;
    if (fat32_write(file, buffer, size, &bytes_written) != FAT32_OK)
        return -1;
    return (lfs_ssize_t)bytes_written;
#else
    return 0;
#endif
}

lfs_soff_t fs_file_seek(lfs_file_t *file, lfs_soff_t off, int whence)
{
#ifdef C_STORAGE_ENABLED
    int32_t position = off;
    if (whence == SEEK_CUR)
        position += (int32_t)file->position;
    else if (whence == SEEK_END)
        position += (int32_t)file->file_size;
    if (position < 0 || fat32_seek(file, (uint32_t)position) != FAT32_OK)
        return -1;
    return position;
#else
    return 0;
#endif
}

int fs_mkdir(const char *path)
{
#ifdef C_STORAGE_ENABLED
    fat32_file_t dir;
    return fat32_dir_create(&dir, path) == FAT32_OK ? LFS_ERR_OK : -1;
#else
    return 0;
#endif
}

int fs_dir_open(lfs_dir_t *dir, const char *path)
{
#ifdef C_STORAGE_ENABLED
    return fat32_open(dir, path) == FAT32_OK ? LFS_ERR_OK : -1;
#else
    return 0;
#endif
}

int fs_dir_close(lfs_dir_t *dir)
{
    return fs_file_close(dir);
}

int fs_dir_read(lfs_dir_t *dir, struct lfs_info *info)
{
#ifdef C_STORAGE_ENABLED
    fat32_entry_t entry;
    if (fat32_dir_read(dir, &entry) != FAT32_OK)
        return 0;
    info->type = (entry.attr & FAT32_ATTR_DIRECTORY) ? LFS_TYPE_DIR : LFS_TYPE_REG;
    info->size = entry.size;
    strncpy(info->name, entry.filename, sizeof(info->name) - 1);
    info->name[sizeof(info->name) - 1] = '\0';
    return 1;
#else
    return 0;
#endif
}

#endif