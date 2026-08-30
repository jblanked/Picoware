#pragma once

#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>

#include "storage.h"
#ifdef C_STORAGE_ENABLED
typedef fat32_file_t lfs_file_t;
typedef fat32_file_t lfs_dir_t;
#else
typedef void *lfs_file_t;
typedef void *lfs_dir_t;
#define FAT32_MAX_FILENAME_LEN 255
#endif
typedef int32_t lfs_soff_t;
typedef int32_t lfs_ssize_t;

struct lfs_info
{
    uint8_t type;
    uint32_t size;
    char name[FAT32_MAX_FILENAME_LEN + 1];
};

#define LFS_ERR_OK 0
#define LFS_TYPE_REG 1
#define LFS_TYPE_DIR 2
#define LFS_O_RDONLY 1
#define LFS_O_WRONLY 2
#define LFS_O_RDWR 3
#define LFS_O_CREAT 0x0100
#define LFS_O_EXCL 0x0200
#define LFS_O_TRUNC 0x0400
#define LFS_O_APPEND 0x0800
#define LFS_SEEK_SET SEEK_SET
#define LFS_SEEK_CUR SEEK_CUR
#define LFS_SEEK_END SEEK_END

int fs_load(void);
int fs_unload(void);
int fs_mount(void);
int fs_unmount(void);
int fs_remove(const char *path);
int fs_rename(const char *oldpath, const char *newpath);
int fs_stat(const char *path, struct lfs_info *info);
int fs_getattr(const char *path, uint8_t type, void *buffer, uint32_t size);
int fs_setattr(const char *path, uint8_t type, const void *buffer, uint32_t size);
int fs_removeattr(const char *path, uint8_t type);
int fs_file_open(lfs_file_t *file, const char *path, int flags);
int fs_file_close(lfs_file_t *file);
int fs_file_sync(lfs_file_t *file);
lfs_ssize_t fs_file_read(lfs_file_t *file, void *buffer, uint32_t size);
lfs_ssize_t fs_file_write(lfs_file_t *file, const void *buffer, uint32_t size);
lfs_soff_t fs_file_seek(lfs_file_t *file, lfs_soff_t off, int whence);
int fs_mkdir(const char *path);
int fs_dir_open(lfs_dir_t *dir, const char *path);
int fs_dir_close(lfs_dir_t *dir);
int fs_dir_read(lfs_dir_t *dir, struct lfs_info *info);