#include "sdcard_vfs_bridge.h"

#include "esp_log.h"
#include "esp_vfs.h"

#include "extmod/vfs.h"
#include "py/objstr.h"
#include "py/runtime.h"
#include "py/stream.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#define SDCARD_MOUNT_POINT "/sdcard"
#define BRIDGE_MAX_OPEN_FILES 16
#define BRIDGE_MAX_PATH 384

typedef struct
{
    bool used;
    mp_obj_t file_obj;
    char path[BRIDGE_MAX_PATH];
} bridge_file_slot_t;

typedef struct
{
    mp_obj_t iter_obj;
    struct dirent de;
} bridge_dir_t;

static bridge_file_slot_t s_file_slots[BRIDGE_MAX_OPEN_FILES] = {0};
static bool s_bridge_registered = false;

static int set_errno_from_nlr(nlr_buf_t *nlr, int fallback)
{
    int err = fallback;
    mp_obj_base_t *exc = nlr->ret_val;

    if (mp_obj_is_subclass_fast(MP_OBJ_FROM_PTR(exc->type), MP_OBJ_FROM_PTR(&mp_type_OSError)))
    {
        mp_obj_t value = mp_obj_exception_get_value(MP_OBJ_FROM_PTR(exc));
        mp_int_t parsed = 0;
        if (mp_obj_get_int_maybe(value, &parsed))
        {
            if (parsed < 0)
            {
                parsed = -parsed;
            }
            if (parsed > 0)
            {
                err = (int)parsed;
            }
        }
    }

    errno = err;
    return -1;
}

static bool bridge_mount_present(void)
{
    const char *path_out = NULL;
    mp_vfs_mount_t *vfs = mp_vfs_lookup_path(SDCARD_MOUNT_POINT, &path_out);
    return vfs != MP_VFS_NONE && vfs != MP_VFS_ROOT;
}

static int build_abs_path(const char *rel_path, char *out, size_t out_size)
{
    const char *path = rel_path;
    if (path == NULL || path[0] == '\0')
    {
        path = "/";
    }

    int written = 0;
    if (path[0] == '/')
    {
        written = snprintf(out, out_size, "%s%s", SDCARD_MOUNT_POINT, path);
    }
    else
    {
        written = snprintf(out, out_size, "%s/%s", SDCARD_MOUNT_POINT, path);
    }

    if (written < 0 || (size_t)written >= out_size)
    {
        errno = ENAMETOOLONG;
        return -1;
    }

    return 0;
}

static const char *flags_to_mode(int flags)
{
    static char mode[4];
    char base = 'r';

    if (flags & O_APPEND)
    {
        base = 'a';
    }
    else if ((flags & O_CREAT) && (flags & O_EXCL))
    {
        base = 'x';
    }
    else if (flags & O_TRUNC)
    {
        base = 'w';
    }

    int access = flags & O_ACCMODE;
    if (access == O_RDWR)
    {
        mode[0] = base;
        mode[1] = '+';
        mode[2] = 'b';
        mode[3] = '\0';
    }
    else
    {
        mode[0] = base;
        mode[1] = 'b';
        mode[2] = '\0';
    }

    return mode;
}

static int alloc_slot(mp_obj_t file_obj, const char *abs_path)
{
    for (int i = 0; i < BRIDGE_MAX_OPEN_FILES; ++i)
    {
        if (!s_file_slots[i].used)
        {
            s_file_slots[i].used = true;
            s_file_slots[i].file_obj = file_obj;
            strncpy(s_file_slots[i].path, abs_path, sizeof(s_file_slots[i].path) - 1);
            s_file_slots[i].path[sizeof(s_file_slots[i].path) - 1] = '\0';
            return i;
        }
    }

    errno = EMFILE;
    return -1;
}

static bridge_file_slot_t *get_slot(int fd)
{
    if (fd < 0 || fd >= BRIDGE_MAX_OPEN_FILES || !s_file_slots[fd].used)
    {
        errno = EBADF;
        return NULL;
    }

    return &s_file_slots[fd];
}

static void clear_slot(int fd)
{
    if (fd >= 0 && fd < BRIDGE_MAX_OPEN_FILES)
    {
        s_file_slots[fd].used = false;
        s_file_slots[fd].file_obj = MP_OBJ_NULL;
        s_file_slots[fd].path[0] = '\0';
    }
}

static int bridge_open(const char *path, int flags, int mode)
{
    (void)mode;

    char abs_path[BRIDGE_MAX_PATH];
    if (build_abs_path(path, abs_path, sizeof(abs_path)) != 0)
    {
        return -1;
    }

    mp_obj_t open_args[] = {
        mp_obj_new_str(abs_path, strlen(abs_path)),
        mp_obj_new_str(flags_to_mode(flags), strlen(flags_to_mode(flags))),
    };

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        return set_errno_from_nlr(&nlr, EIO);
    }

    mp_obj_t file_obj = mp_vfs_open(2, open_args, (mp_map_t *)&mp_const_empty_map);
    nlr_pop();

    int fd = alloc_slot(file_obj, abs_path);
    if (fd < 0)
    {
        int close_err = 0;
        mp_stream_rw(file_obj, NULL, 0, &close_err, MP_STREAM_RW_WRITE | MP_STREAM_RW_ONCE);
        mp_stream_close(file_obj);
        return -1;
    }

    return fd;
}

static ssize_t bridge_read(int fd, void *dst, size_t size)
{
    bridge_file_slot_t *slot = get_slot(fd);
    if (slot == NULL)
    {
        return -1;
    }

    int err = 0;
    mp_uint_t out = mp_stream_rw(slot->file_obj, dst, size, &err, MP_STREAM_RW_READ | MP_STREAM_RW_ONCE);
    if (err != 0)
    {
        errno = err;
        return -1;
    }

    return out;
}

static ssize_t bridge_write(int fd, const void *src, size_t size)
{
    bridge_file_slot_t *slot = get_slot(fd);
    if (slot == NULL)
    {
        return -1;
    }

    int err = 0;
    mp_uint_t out = mp_stream_rw(slot->file_obj, (void *)src, size, &err, MP_STREAM_RW_WRITE);
    if (err != 0)
    {
        errno = err;
        return -1;
    }

    return out;
}

static int bridge_close(int fd)
{
    bridge_file_slot_t *slot = get_slot(fd);
    if (slot == NULL)
    {
        return -1;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        clear_slot(fd);
        return set_errno_from_nlr(&nlr, EIO);
    }

    mp_stream_close(slot->file_obj);
    nlr_pop();

    clear_slot(fd);
    return 0;
}

static off_t bridge_lseek(int fd, off_t offset, int whence)
{
    bridge_file_slot_t *slot = get_slot(fd);
    if (slot == NULL)
    {
        return -1;
    }

    int err = 0;
    mp_off_t out = mp_stream_seek(slot->file_obj, offset, whence, &err);
    if (out == (mp_off_t)-1)
    {
        errno = err != 0 ? err : EIO;
        return -1;
    }

    return out;
}

static int bridge_stat_from_path(const char *abs_path, struct stat *st)
{
    mp_obj_t path_obj = mp_obj_new_str(abs_path, strlen(abs_path));

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        return set_errno_from_nlr(&nlr, ENOENT);
    }

    mp_obj_t stat_obj = mp_vfs_stat(path_obj);
    nlr_pop();

    mp_obj_t *items = NULL;
    mp_obj_get_array_fixed_n(stat_obj, 10, &items);

    memset(st, 0, sizeof(*st));
    st->st_mode = mp_obj_get_int(items[0]);
    st->st_size = mp_obj_get_int(items[6]);
    return 0;
}

static int bridge_fstat(int fd, struct stat *st)
{
    bridge_file_slot_t *slot = get_slot(fd);
    if (slot == NULL)
    {
        return -1;
    }

    return bridge_stat_from_path(slot->path, st);
}

static int bridge_stat(const char *path, struct stat *st)
{
    char abs_path[BRIDGE_MAX_PATH];
    if (build_abs_path(path, abs_path, sizeof(abs_path)) != 0)
    {
        return -1;
    }

    return bridge_stat_from_path(abs_path, st);
}

static int bridge_mkdir(const char *path, mode_t mode)
{
    (void)mode;

    char abs_path[BRIDGE_MAX_PATH];
    if (build_abs_path(path, abs_path, sizeof(abs_path)) != 0)
    {
        return -1;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        return set_errno_from_nlr(&nlr, EIO);
    }

    mp_vfs_mkdir(mp_obj_new_str(abs_path, strlen(abs_path)));
    nlr_pop();
    return 0;
}

static int bridge_unlink(const char *path)
{
    char abs_path[BRIDGE_MAX_PATH];
    if (build_abs_path(path, abs_path, sizeof(abs_path)) != 0)
    {
        return -1;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        return set_errno_from_nlr(&nlr, EIO);
    }

    mp_vfs_remove(mp_obj_new_str(abs_path, strlen(abs_path)));
    nlr_pop();
    return 0;
}

static int bridge_rmdir(const char *path)
{
    char abs_path[BRIDGE_MAX_PATH];
    if (build_abs_path(path, abs_path, sizeof(abs_path)) != 0)
    {
        return -1;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        return set_errno_from_nlr(&nlr, EIO);
    }

    mp_vfs_rmdir(mp_obj_new_str(abs_path, strlen(abs_path)));
    nlr_pop();
    return 0;
}

static int bridge_rename(const char *src, const char *dst)
{
    char abs_src[BRIDGE_MAX_PATH];
    char abs_dst[BRIDGE_MAX_PATH];
    if (build_abs_path(src, abs_src, sizeof(abs_src)) != 0)
    {
        return -1;
    }
    if (build_abs_path(dst, abs_dst, sizeof(abs_dst)) != 0)
    {
        return -1;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        return set_errno_from_nlr(&nlr, EIO);
    }

    mp_vfs_rename(mp_obj_new_str(abs_src, strlen(abs_src)), mp_obj_new_str(abs_dst, strlen(abs_dst)));
    nlr_pop();
    return 0;
}

static DIR *bridge_opendir(const char *path)
{
    char abs_path[BRIDGE_MAX_PATH];
    if (build_abs_path(path, abs_path, sizeof(abs_path)) != 0)
    {
        return NULL;
    }

    bridge_dir_t *dir = calloc(1, sizeof(*dir));
    if (dir == NULL)
    {
        errno = ENOMEM;
        return NULL;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        free(dir);
        set_errno_from_nlr(&nlr, EIO);
        return NULL;
    }

    mp_obj_t ilist_args[] = {
        mp_obj_new_str(abs_path, strlen(abs_path)),
    };
    dir->iter_obj = mp_vfs_ilistdir(1, ilist_args);
    nlr_pop();

    return (DIR *)dir;
}

static struct dirent *bridge_readdir(DIR *pdir)
{
    if (pdir == NULL)
    {
        errno = EBADF;
        return NULL;
    }

    bridge_dir_t *dir = (bridge_dir_t *)pdir;

    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        set_errno_from_nlr(&nlr, EIO);
        return NULL;
    }

    mp_obj_t next = mp_iternext(dir->iter_obj);
    if (next == MP_OBJ_STOP_ITERATION)
    {
        nlr_pop();
        return NULL;
    }

    mp_obj_t *tuple_items = NULL;
    mp_obj_get_array_fixed_n(next, 4, &tuple_items);

    size_t name_len = 0;
    const char *name = mp_obj_str_get_data(tuple_items[0], &name_len);

    memset(&dir->de, 0, sizeof(dir->de));
    memcpy(dir->de.d_name, name, name_len < sizeof(dir->de.d_name) - 1 ? name_len : sizeof(dir->de.d_name) - 1);

    mp_int_t mp_mode = mp_obj_get_int(tuple_items[1]);
    dir->de.d_type = (mp_mode & MP_S_IFDIR) ? DT_DIR : DT_REG;

    nlr_pop();
    return &dir->de;
}

static int bridge_closedir(DIR *pdir)
{
    if (pdir == NULL)
    {
        errno = EBADF;
        return -1;
    }

    free((bridge_dir_t *)pdir);
    return 0;
}

static const esp_vfs_t s_bridge_vfs = {
    .flags = ESP_VFS_FLAG_DEFAULT,
    .open = bridge_open,
    .read = bridge_read,
    .write = bridge_write,
    .close = bridge_close,
    .lseek = bridge_lseek,
    .fstat = bridge_fstat,
    .stat = bridge_stat,
    .mkdir = bridge_mkdir,
    .rmdir = bridge_rmdir,
    .unlink = bridge_unlink,
    .rename = bridge_rename,
    .opendir = bridge_opendir,
    .readdir = bridge_readdir,
    .closedir = bridge_closedir,
};

esp_err_t sdcard_vfs_bridge_register(void)
{
    if (s_bridge_registered)
    {
        return ESP_OK;
    }

    if (!bridge_mount_present())
    {
        PRINT("cannot register bridge: %s is not mounted in MicroPython VFS", SDCARD_MOUNT_POINT);
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t ret = esp_vfs_register(SDCARD_MOUNT_POINT, &s_bridge_vfs, NULL);
    if (ret != ESP_OK)
    {
        PRINT("esp_vfs_register failed: %s", esp_err_to_name(ret));
        return ret;
    }

    memset(s_file_slots, 0, sizeof(s_file_slots));
    s_bridge_registered = true;
    PRINT("registered POSIX bridge for %s", SDCARD_MOUNT_POINT);
    return ESP_OK;
}

esp_err_t sdcard_vfs_bridge_unregister(void)
{
    for (int i = 0; i < BRIDGE_MAX_OPEN_FILES; ++i)
    {
        if (!s_file_slots[i].used)
        {
            continue;
        }

        nlr_buf_t nlr;
        if (nlr_push(&nlr) == 0)
        {
            mp_stream_close(s_file_slots[i].file_obj);
            nlr_pop();
        }
        clear_slot(i);
    }

    if (!s_bridge_registered)
    {
        return ESP_OK;
    }

    esp_err_t ret = esp_vfs_unregister(SDCARD_MOUNT_POINT);
    if (ret != ESP_OK)
    {
        PRINT("esp_vfs_unregister failed: %s", esp_err_to_name(ret));
    }

    s_bridge_registered = false;
    return ret;
}
