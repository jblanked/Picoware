#include "io.h"

#include <string.h>

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