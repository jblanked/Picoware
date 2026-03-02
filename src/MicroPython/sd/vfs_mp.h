#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objstr.h"
#include "py/stream.h"
#include "py/mperrno.h"
#include "py/mphal.h"
#include "py/builtin.h"
#include "extmod/vfs.h"
#include "fat32.h"

#define VFS_FILE_BUFFER_SIZE 1024 * 16 // 16KB buffer for file reads

typedef struct
{
    mp_obj_base_t base;
    fat32_file_t file;
    bool is_open;
    bool is_text; // text mode vs binary mode
    bool is_writable;
    bool is_readable;
    uint8_t read_buffer[VFS_FILE_BUFFER_SIZE];
    size_t buffer_pos; // Current position in buffer
    size_t buffer_len; // Valid bytes in buffer
} vfs_mp_file_obj_t;

typedef struct
{
    mp_obj_base_t base;
    vstr_t root; // Mount point root path
    bool readonly;
} vfs_mp_obj_t;

extern const mp_obj_type_t vfs_mp_type;
extern const mp_obj_type_t vfs_mp_file_type;

mp_uint_t vfs_file_fill_buffer(vfs_mp_file_obj_t *self, int *errcode);
mp_uint_t vfs_file_read_buffered(vfs_mp_file_obj_t *self, void *buf, mp_uint_t size, int *errcode);
mp_obj_t vfs_file_close(mp_obj_t self_in);
mp_obj_t vfs_file___exit__(size_t n_args, const mp_obj_t *args);
mp_uint_t vfs_file_read(mp_obj_t self_in, void *buf, mp_uint_t size, int *errcode);
mp_uint_t vfs_file_write(mp_obj_t self_in, const void *buf, mp_uint_t size, int *errcode);
mp_uint_t vfs_file_ioctl(mp_obj_t self_in, mp_uint_t request, uintptr_t arg, int *errcode);
mp_obj_t vfs_file_read_method(size_t n_args, const mp_obj_t *args);
mp_obj_t vfs_file_readinto(mp_obj_t self_in, mp_obj_t buf_in);
mp_obj_t vfs_file_readline(size_t n_args, const mp_obj_t *args);
mp_obj_t vfs_file_readlines(mp_obj_t self_in);
mp_obj_t vfs_file_write_method(mp_obj_t self_in, mp_obj_t data);
mp_obj_t vfs_file_seek(size_t n_args, const mp_obj_t *args);
mp_obj_t vfs_file_tell(mp_obj_t self_in);
mp_obj_t vfs_file_flush(mp_obj_t self_in);
mp_obj_t vfs_file___enter__(mp_obj_t self_in);
mp_obj_t vfs_file_readable(mp_obj_t self_in);
mp_obj_t vfs_file_writable(mp_obj_t self_in);
mp_obj_t vfs_file_iternext(mp_obj_t self_in);

mp_obj_t vfs_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t vfs_mp_mount(mp_obj_t self_in, mp_obj_t readonly, mp_obj_t mkfs);
mp_obj_t vfs_mp_umount(mp_obj_t self_in);
mp_obj_t vfs_mp_open(mp_obj_t self_in, mp_obj_t path_in, mp_obj_t mode_in);
mp_obj_t vfs_mp_ilistdir_func(mp_obj_t self_in, mp_obj_t path_in);
mp_obj_t vfs_mp_mkdir(mp_obj_t self_in, mp_obj_t path_in);
mp_obj_t vfs_mp_rmdir(mp_obj_t self_in, mp_obj_t path_in);
mp_obj_t vfs_mp_remove(mp_obj_t self_in, mp_obj_t path_in);
mp_obj_t vfs_mp_rename(mp_obj_t self_in, mp_obj_t old_in, mp_obj_t new_in);
mp_obj_t vfs_mp_stat(mp_obj_t self_in, mp_obj_t path_in);
mp_obj_t vfs_mp_statvfs(mp_obj_t self_in, mp_obj_t path_in);
mp_obj_t vfs_mp_chdir(mp_obj_t self_in, mp_obj_t path_in);
mp_obj_t vfs_mp_getcwd(mp_obj_t self_in);

mp_obj_t vfs_mp_mount_helper(size_t n_args, const mp_obj_t *args);
mp_obj_t vfs_mp_umount_helper(size_t n_args, const mp_obj_t *args);