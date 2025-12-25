/*
 * Picoware VFS (Virtual File System) for MicroPython
 *
 * This module provides VFS integration so that the SD card can be mounted
 * as a proper filesystem, enabling use of __import__, open(), os module, etc.
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objstr.h"
#include "py/stream.h"
#include "py/mperrno.h"
#include "py/mphal.h"
#include "py/builtin.h"
#include "extmod/vfs.h"
#include "fat32.h"

#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#ifndef STATIC
#define STATIC static
#endif

// Forward declarations - use extern to avoid static/non-static conflict
extern const mp_obj_type_t picoware_vfs_type;
extern const mp_obj_type_t picoware_vfs_file_type;

// =============================================================================
// VFS File Object
// =============================================================================

#define VFS_FILE_BUFFER_SIZE 1024 * 8 // 8KB buffer for file reads

typedef struct _picoware_vfs_file_obj_t
{
    mp_obj_base_t base;
    fat32_file_t file;
    bool is_open;
    bool is_text; // text mode vs binary mode
    bool is_writable;
    bool is_readable;
    // Read buffer for efficient small reads (especially readline)
    uint8_t read_buffer[VFS_FILE_BUFFER_SIZE];
    size_t buffer_pos; // Current position in buffer
    size_t buffer_len; // Valid bytes in buffer
} picoware_vfs_file_obj_t;

// Helper to fill read buffer
STATIC mp_uint_t vfs_file_fill_buffer(picoware_vfs_file_obj_t *self, int *errcode)
{
    self->buffer_pos = 0;
    self->buffer_len = 0;

    size_t bytes_read = 0;
    fat32_error_t err = fat32_read(&self->file, self->read_buffer, VFS_FILE_BUFFER_SIZE, &bytes_read);

    if (err != FAT32_OK && bytes_read == 0)
    {
        *errcode = MP_EIO;
        return MP_STREAM_ERROR;
    }

    self->buffer_len = bytes_read;
    return bytes_read;
}

// Buffered read - uses internal buffer for efficiency
STATIC mp_uint_t vfs_file_read_buffered(picoware_vfs_file_obj_t *self, void *buf, mp_uint_t size, int *errcode)
{
    uint8_t *dest = (uint8_t *)buf;
    size_t total_read = 0;

    while (total_read < size)
    {
        // If buffer is empty, refill it
        if (self->buffer_pos >= self->buffer_len)
        {
            mp_uint_t result = vfs_file_fill_buffer(self, errcode);
            if (result == MP_STREAM_ERROR)
            {
                if (total_read > 0)
                    return total_read; // Return what we have
                return MP_STREAM_ERROR;
            }
            if (self->buffer_len == 0)
            {
                break; // EOF
            }
        }

        // Copy from buffer
        size_t available = self->buffer_len - self->buffer_pos;
        size_t to_copy = (size - total_read < available) ? (size - total_read) : available;
        memcpy(dest + total_read, self->read_buffer + self->buffer_pos, to_copy);
        self->buffer_pos += to_copy;
        total_read += to_copy;
    }

    return total_read;
}

STATIC void file_ensure_open(picoware_vfs_file_obj_t *self)
{
    if (!self->is_open)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("I/O operation on closed file"));
    }
}

STATIC mp_obj_t vfs_file_close(mp_obj_t self_in)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->is_open)
    {
        fat32_close(&self->file);
        self->is_open = false;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vfs_file_close_obj, vfs_file_close);

STATIC mp_obj_t vfs_file___exit__(size_t n_args, const mp_obj_t *args)
{
    (void)n_args;
    return vfs_file_close(args[0]);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vfs_file___exit___obj, 4, 4, vfs_file___exit__);

STATIC mp_uint_t vfs_file_read(mp_obj_t self_in, void *buf, mp_uint_t size, int *errcode)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!self->is_open)
    {
        *errcode = MP_EBADF;
        return MP_STREAM_ERROR;
    }

    if (!self->is_readable)
    {
        *errcode = MP_EPERM;
        return MP_STREAM_ERROR;
    }

    size_t bytes_read = 0;
    fat32_error_t err = fat32_read(&self->file, buf, size, &bytes_read);

    if (err != FAT32_OK && bytes_read == 0)
    {
        *errcode = MP_EIO;
        return MP_STREAM_ERROR;
    }

    return bytes_read;
}

STATIC mp_uint_t vfs_file_write(mp_obj_t self_in, const void *buf, mp_uint_t size, int *errcode)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!self->is_open)
    {
        *errcode = MP_EBADF;
        return MP_STREAM_ERROR;
    }

    if (!self->is_writable)
    {
        *errcode = MP_EPERM;
        return MP_STREAM_ERROR;
    }

    size_t bytes_written = 0;
    fat32_error_t err = fat32_write(&self->file, buf, size, &bytes_written);

    if (err != FAT32_OK)
    {
        *errcode = MP_EIO;
        return MP_STREAM_ERROR;
    }

    return bytes_written;
}

STATIC mp_uint_t vfs_file_ioctl(mp_obj_t self_in, mp_uint_t request, uintptr_t arg, int *errcode)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);

    switch (request)
    {
    case MP_STREAM_FLUSH:
        // FAT32 writes are synchronous, nothing to flush
        return 0;

    case MP_STREAM_SEEK:
    {
        struct mp_stream_seek_t *s = (struct mp_stream_seek_t *)(uintptr_t)arg;
        uint32_t new_pos;

        switch (s->whence)
        {
        case 0: // SEEK_SET
            new_pos = s->offset;
            break;
        case 1: // SEEK_CUR
            new_pos = self->file.position + s->offset;
            break;
        case 2: // SEEK_END
            new_pos = self->file.file_size + s->offset;
            break;
        default:
            *errcode = MP_EINVAL;
            return MP_STREAM_ERROR;
        }

        if (fat32_seek(&self->file, new_pos) != FAT32_OK)
        {
            *errcode = MP_EIO;
            return MP_STREAM_ERROR;
        }

        s->offset = new_pos;
        return 0;
    }

    case MP_STREAM_CLOSE:
        if (self->is_open)
        {
            fat32_close(&self->file);
            self->is_open = false;
        }
        return 0;

    default:
        *errcode = MP_EINVAL;
        return MP_STREAM_ERROR;
    }
}

STATIC mp_obj_t vfs_file_read_method(size_t n_args, const mp_obj_t *args)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    file_ensure_open(self);

    mp_int_t size = -1;
    if (n_args > 1)
    {
        size = mp_obj_get_int(args[1]);
    }

    // If size is -1, read entire file from current position
    if (size < 0)
    {
        size = self->file.file_size - self->file.position;
    }

    if (size == 0)
    {
        if (self->is_text)
        {
            return mp_obj_new_str("", 0);
        }
        else
        {
            return mp_obj_new_bytes((const byte *)"", 0);
        }
    }

    vstr_t vstr;
    vstr_init_len(&vstr, size);

    int errcode;
    mp_uint_t bytes_read = vfs_file_read(args[0], vstr.buf, size, &errcode);

    if (bytes_read == MP_STREAM_ERROR)
    {
        vstr_clear(&vstr);
        mp_raise_OSError(errcode);
    }

    vstr.len = bytes_read;

    if (self->is_text)
    {
        return mp_obj_new_str_from_vstr(&vstr);
    }
    else
    {
        return mp_obj_new_bytes_from_vstr(&vstr);
    }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vfs_file_read_method_obj, 1, 2, vfs_file_read_method);

STATIC mp_obj_t vfs_file_readline(size_t n_args, const mp_obj_t *args)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    file_ensure_open(self);

    mp_int_t max_size = -1;
    if (n_args > 1)
    {
        max_size = mp_obj_get_int(args[1]);
    }

    vstr_t vstr;
    vstr_init(&vstr, 64);

    int errcode;
    char c;
    mp_uint_t total_read = 0;

    while (max_size < 0 || total_read < (mp_uint_t)max_size)
    {
        // Use buffered read for efficiency
        mp_uint_t bytes_read = vfs_file_read_buffered(self, &c, 1, &errcode);

        if (bytes_read == MP_STREAM_ERROR)
        {
            if (vstr.len > 0)
            {
                break; // Return what we have
            }
            vstr_clear(&vstr);
            mp_raise_OSError(errcode);
        }

        if (bytes_read == 0)
        {
            break; // EOF
        }

        vstr_add_byte(&vstr, c);
        total_read++;

        if (c == '\n')
        {
            break;
        }
    }

    if (self->is_text)
    {
        return mp_obj_new_str_from_vstr(&vstr);
    }
    else
    {
        return mp_obj_new_bytes_from_vstr(&vstr);
    }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vfs_file_readline_obj, 1, 2, vfs_file_readline);

STATIC mp_obj_t vfs_file_readlines(mp_obj_t self_in)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    file_ensure_open(self);

    mp_obj_t list = mp_obj_new_list(0, NULL);
    mp_obj_t args[2] = {self_in, MP_OBJ_NEW_SMALL_INT(-1)};

    while (1)
    {
        mp_obj_t line = vfs_file_readline(2, args);
        size_t len;
        mp_obj_str_get_data(line, &len);
        if (len == 0)
        {
            break;
        }
        mp_obj_list_append(list, line);
    }

    return list;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vfs_file_readlines_obj, vfs_file_readlines);

STATIC mp_obj_t vfs_file_write_method(mp_obj_t self_in, mp_obj_t data)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    file_ensure_open(self);

    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data, &bufinfo, MP_BUFFER_READ);

    int errcode;
    mp_uint_t bytes_written = vfs_file_write(self_in, bufinfo.buf, bufinfo.len, &errcode);

    if (bytes_written == MP_STREAM_ERROR)
    {
        mp_raise_OSError(errcode);
    }

    return mp_obj_new_int(bytes_written);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(vfs_file_write_method_obj, vfs_file_write_method);

STATIC mp_obj_t vfs_file_seek(size_t n_args, const mp_obj_t *args)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    file_ensure_open(self);

    mp_int_t offset = mp_obj_get_int(args[1]);
    mp_int_t whence = 0;
    if (n_args > 2)
    {
        whence = mp_obj_get_int(args[2]);
    }

    // Invalidate read buffer on seek
    self->buffer_pos = 0;
    self->buffer_len = 0;

    struct mp_stream_seek_t seek_s = {
        .offset = offset,
        .whence = whence,
    };

    int errcode;
    mp_uint_t res = vfs_file_ioctl(args[0], MP_STREAM_SEEK, (uintptr_t)&seek_s, &errcode);

    if (res == MP_STREAM_ERROR)
    {
        mp_raise_OSError(errcode);
    }

    return mp_obj_new_int(seek_s.offset);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vfs_file_seek_obj, 2, 3, vfs_file_seek);

STATIC mp_obj_t vfs_file_tell(mp_obj_t self_in)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    file_ensure_open(self);
    return mp_obj_new_int(self->file.position);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vfs_file_tell_obj, vfs_file_tell);

STATIC mp_obj_t vfs_file_flush(mp_obj_t self_in)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    file_ensure_open(self);
    // Writes are synchronous, nothing to do
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vfs_file_flush_obj, vfs_file_flush);

STATIC mp_obj_t vfs_file___enter__(mp_obj_t self_in)
{
    return self_in;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vfs_file___enter___obj, vfs_file___enter__);

STATIC mp_obj_t vfs_file_readable(mp_obj_t self_in)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(self->is_readable);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vfs_file_readable_obj, vfs_file_readable);

STATIC mp_obj_t vfs_file_writable(mp_obj_t self_in)
{
    picoware_vfs_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(self->is_writable);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vfs_file_writable_obj, vfs_file_writable);

// File iterator support (for line in file)
STATIC mp_obj_t vfs_file_iternext(mp_obj_t self_in)
{
    mp_obj_t args[2] = {self_in, MP_OBJ_NEW_SMALL_INT(-1)};
    mp_obj_t line = vfs_file_readline(2, args);
    size_t len;
    mp_obj_str_get_data(line, &len);
    if (len == 0)
    {
        return MP_OBJ_STOP_ITERATION;
    }
    return line;
}

STATIC const mp_rom_map_elem_t vfs_file_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&vfs_file_read_method_obj)},
    {MP_ROM_QSTR(MP_QSTR_readline), MP_ROM_PTR(&vfs_file_readline_obj)},
    {MP_ROM_QSTR(MP_QSTR_readlines), MP_ROM_PTR(&vfs_file_readlines_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&vfs_file_write_method_obj)},
    {MP_ROM_QSTR(MP_QSTR_seek), MP_ROM_PTR(&vfs_file_seek_obj)},
    {MP_ROM_QSTR(MP_QSTR_tell), MP_ROM_PTR(&vfs_file_tell_obj)},
    {MP_ROM_QSTR(MP_QSTR_flush), MP_ROM_PTR(&vfs_file_flush_obj)},
    {MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&vfs_file_close_obj)},
    {MP_ROM_QSTR(MP_QSTR_readable), MP_ROM_PTR(&vfs_file_readable_obj)},
    {MP_ROM_QSTR(MP_QSTR_writable), MP_ROM_PTR(&vfs_file_writable_obj)},
    {MP_ROM_QSTR(MP_QSTR___enter__), MP_ROM_PTR(&vfs_file___enter___obj)},
    {MP_ROM_QSTR(MP_QSTR___exit__), MP_ROM_PTR(&vfs_file___exit___obj)},
};
STATIC MP_DEFINE_CONST_DICT(vfs_file_locals_dict, vfs_file_locals_dict_table);

STATIC const mp_stream_p_t vfs_file_stream_p = {
    .read = vfs_file_read,
    .write = vfs_file_write,
    .ioctl = vfs_file_ioctl,
};

MP_DEFINE_CONST_OBJ_TYPE(
    picoware_vfs_file_type,
    MP_QSTR_PicowareFile,
    MP_TYPE_FLAG_ITER_IS_ITERNEXT,
    protocol, &vfs_file_stream_p,
    iter, vfs_file_iternext,
    locals_dict, &vfs_file_locals_dict);

// =============================================================================
// VFS Object
// =============================================================================

typedef struct _picoware_vfs_obj_t
{
    mp_obj_base_t base;
    vstr_t root; // Mount point root path
    bool readonly;
} picoware_vfs_obj_t;

STATIC mp_obj_t picoware_vfs_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 1, true);

    picoware_vfs_obj_t *self = mp_obj_malloc(picoware_vfs_obj_t, type);

    vstr_init(&self->root, 0);
    self->readonly = false;

    // Initialize FAT32 if not already
    if (!fat32_is_ready())
    {
        fat32_init();
    }

    // Mount if not already mounted
    if (!fat32_is_mounted())
    {
        fat32_error_t err = fat32_mount();
        if (err != FAT32_OK)
        {
            mp_raise_OSError(MP_EIO);
        }
    }

    return MP_OBJ_FROM_PTR(self);
}

// Helper to build absolute path
STATIC void build_path(picoware_vfs_obj_t *vfs, const char *path, char *out_path, size_t max_len)
{
    if (path[0] == '/')
    {
        // Absolute path
        strncpy(out_path, path, max_len - 1);
        out_path[max_len - 1] = '\0';
    }
    else
    {
        // Relative path - prepend root
        if (vfs->root.len > 0)
        {
            snprintf(out_path, max_len, "%s/%s", vfs->root.buf, path);
        }
        else
        {
            snprintf(out_path, max_len, "/%s", path);
        }
    }
}

// mount(readonly, mkfs)
STATIC mp_obj_t picoware_vfs_mount(mp_obj_t self_in, mp_obj_t readonly, mp_obj_t mkfs)
{
    picoware_vfs_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->readonly = mp_obj_is_true(readonly);

    if (!fat32_is_mounted())
    {
        fat32_error_t err = fat32_mount();
        if (err != FAT32_OK)
        {
            mp_raise_OSError(MP_EIO);
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(picoware_vfs_mount_obj, picoware_vfs_mount);

// umount()
STATIC mp_obj_t picoware_vfs_umount(mp_obj_t self_in)
{
    (void)self_in;
    fat32_unmount();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_vfs_umount_obj, picoware_vfs_umount);

// open(path, mode)
STATIC mp_obj_t picoware_vfs_open(mp_obj_t self_in, mp_obj_t path_in, mp_obj_t mode_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *path = mp_obj_str_get_str(path_in);
    const char *mode = mp_obj_str_get_str(mode_in);

    char full_path[FAT32_MAX_PATH_LEN];
    build_path(vfs, path, full_path, sizeof(full_path));

    // Parse mode string
    bool is_read = false;
    bool is_write = false;
    bool is_append = false;
    bool is_create = false;
    bool is_truncate = false;
    bool is_text = true;

    for (const char *m = mode; *m; m++)
    {
        switch (*m)
        {
        case 'r':
            is_read = true;
            break;
        case 'w':
            is_write = true;
            is_create = true;
            is_truncate = true;
            break;
        case 'a':
            is_write = true;
            is_append = true;
            is_create = true;
            break;
        case '+':
            is_read = true;
            is_write = true;
            break;
        case 'b':
            is_text = false;
            break;
        case 't':
            is_text = true;
            break;
        case 'x':
            is_create = true;
            break;
        }
    }

    // Default to read if no mode specified
    if (!is_read && !is_write)
    {
        is_read = true;
    }

    if (vfs->readonly && is_write)
    {
        mp_raise_OSError(MP_EROFS);
    }

    picoware_vfs_file_obj_t *file_obj = mp_obj_malloc(picoware_vfs_file_obj_t, &picoware_vfs_file_type);
    memset(&file_obj->file, 0, sizeof(fat32_file_t));
    file_obj->is_open = false;
    file_obj->is_text = is_text;
    file_obj->is_readable = is_read;
    file_obj->is_writable = is_write;

    fat32_error_t err = fat32_open(&file_obj->file, full_path);

    if (err != FAT32_OK)
    {
        if (is_create)
        {
            // Try to create the file
            err = fat32_create(&file_obj->file, full_path);
            if (err != FAT32_OK)
            {
                mp_raise_OSError(MP_EIO);
            }
            // Re-open the newly created file
            err = fat32_open(&file_obj->file, full_path);
            if (err != FAT32_OK)
            {
                mp_raise_OSError(MP_ENOENT);
            }
        }
        else
        {
            mp_raise_OSError(MP_ENOENT);
        }
    }
    else if (is_truncate)
    {
        // File exists and we need to truncate - delete and recreate
        fat32_close(&file_obj->file);
        fat32_delete(full_path);
        err = fat32_create(&file_obj->file, full_path);
        if (err != FAT32_OK)
        {
            mp_raise_OSError(MP_EIO);
        }
        err = fat32_open(&file_obj->file, full_path);
        if (err != FAT32_OK)
        {
            mp_raise_OSError(MP_ENOENT);
        }
    }

    file_obj->is_open = true;
    file_obj->buffer_pos = 0;
    file_obj->buffer_len = 0;

    // Seek to end for append mode
    if (is_append)
    {
        fat32_seek(&file_obj->file, file_obj->file.file_size);
    }

    return MP_OBJ_FROM_PTR(file_obj);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(picoware_vfs_open_obj, picoware_vfs_open);

// ilistdir(path)
STATIC mp_obj_t picoware_vfs_ilistdir_func(mp_obj_t self_in, mp_obj_t path_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *path = mp_obj_str_get_str(path_in);

    char full_path[FAT32_MAX_PATH_LEN];
    build_path(vfs, path, full_path, sizeof(full_path));

    // Handle empty path or root
    if (strlen(full_path) == 0 || (strlen(full_path) == 1 && full_path[0] == '/'))
    {
        strcpy(full_path, "/");
    }

    fat32_file_t dir;
    fat32_error_t err = fat32_open(&dir, full_path);
    if (err != FAT32_OK)
    {
        mp_raise_OSError(MP_ENOENT);
    }

    if (!(dir.attributes & FAT32_ATTR_DIRECTORY))
    {
        fat32_close(&dir);
        mp_raise_OSError(MP_ENOTDIR);
    }

    mp_obj_t list = mp_obj_new_list(0, NULL);
    fat32_entry_t entry;

    while (fat32_dir_read(&dir, &entry) == FAT32_OK && entry.filename[0])
    {
        // Create tuple: (name, type, inode, size)
        mp_obj_t tuple[4];
        tuple[0] = mp_obj_new_str(entry.filename, strlen(entry.filename));
        tuple[1] = mp_obj_new_int((entry.attr & FAT32_ATTR_DIRECTORY) ? MP_S_IFDIR : MP_S_IFREG);
        tuple[2] = mp_obj_new_int(entry.start_cluster); // Use cluster as inode
        tuple[3] = mp_obj_new_int(entry.size);

        mp_obj_list_append(list, mp_obj_new_tuple(4, tuple));
    }

    fat32_close(&dir);
    // Return the list directly - lists are iterable
    return list;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_vfs_ilistdir_obj, picoware_vfs_ilistdir_func);

// mkdir(path)
STATIC mp_obj_t picoware_vfs_mkdir(mp_obj_t self_in, mp_obj_t path_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *path = mp_obj_str_get_str(path_in);

    if (vfs->readonly)
    {
        mp_raise_OSError(MP_EROFS);
    }

    char full_path[FAT32_MAX_PATH_LEN];
    build_path(vfs, path, full_path, sizeof(full_path));

    fat32_file_t dir;
    fat32_error_t err = fat32_dir_create(&dir, full_path);
    if (err != FAT32_OK)
    {
        if (err == FAT32_ERROR_FILE_EXISTS)
        {
            mp_raise_OSError(MP_EEXIST);
        }
        mp_raise_OSError(MP_EIO);
    }
    fat32_close(&dir);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_vfs_mkdir_obj, picoware_vfs_mkdir);

// rmdir(path)
STATIC mp_obj_t picoware_vfs_rmdir(mp_obj_t self_in, mp_obj_t path_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *path = mp_obj_str_get_str(path_in);

    if (vfs->readonly)
    {
        mp_raise_OSError(MP_EROFS);
    }

    char full_path[FAT32_MAX_PATH_LEN];
    build_path(vfs, path, full_path, sizeof(full_path));

    fat32_error_t err = fat32_delete(full_path);
    if (err != FAT32_OK)
    {
        if (err == FAT32_ERROR_FILE_NOT_FOUND || err == FAT32_ERROR_DIR_NOT_FOUND)
        {
            mp_raise_OSError(MP_ENOENT);
        }
        if (err == FAT32_ERROR_DIR_NOT_EMPTY)
        {
            mp_raise_OSError(MP_ENODEV); // Directory not empty
        }
        mp_raise_OSError(MP_EIO);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_vfs_rmdir_obj, picoware_vfs_rmdir);

// remove(path)
STATIC mp_obj_t picoware_vfs_remove(mp_obj_t self_in, mp_obj_t path_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *path = mp_obj_str_get_str(path_in);

    if (vfs->readonly)
    {
        mp_raise_OSError(MP_EROFS);
    }

    char full_path[FAT32_MAX_PATH_LEN];
    build_path(vfs, path, full_path, sizeof(full_path));

    fat32_error_t err = fat32_delete(full_path);
    if (err != FAT32_OK)
    {
        if (err == FAT32_ERROR_FILE_NOT_FOUND)
        {
            mp_raise_OSError(MP_ENOENT);
        }
        mp_raise_OSError(MP_EIO);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_vfs_remove_obj, picoware_vfs_remove);

// rename(old, new)
STATIC mp_obj_t picoware_vfs_rename(mp_obj_t self_in, mp_obj_t old_in, mp_obj_t new_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *old_path = mp_obj_str_get_str(old_in);
    const char *new_path = mp_obj_str_get_str(new_in);

    if (vfs->readonly)
    {
        mp_raise_OSError(MP_EROFS);
    }

    char old_full[FAT32_MAX_PATH_LEN];
    char new_full[FAT32_MAX_PATH_LEN];
    build_path(vfs, old_path, old_full, sizeof(old_full));
    build_path(vfs, new_path, new_full, sizeof(new_full));

    fat32_error_t err = fat32_rename(old_full, new_full);
    if (err != FAT32_OK)
    {
        if (err == FAT32_ERROR_FILE_NOT_FOUND)
        {
            mp_raise_OSError(MP_ENOENT);
        }
        mp_raise_OSError(MP_EIO);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(picoware_vfs_rename_obj, picoware_vfs_rename);

// stat(path)
STATIC mp_obj_t picoware_vfs_stat(mp_obj_t self_in, mp_obj_t path_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *path = mp_obj_str_get_str(path_in);

    char full_path[FAT32_MAX_PATH_LEN];
    build_path(vfs, path, full_path, sizeof(full_path));

    fat32_file_t file;
    fat32_error_t err = fat32_open(&file, full_path);
    if (err != FAT32_OK)
    {
        mp_raise_OSError(MP_ENOENT);
    }

    // Build stat tuple: (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime)
    mp_obj_tuple_t *t = MP_OBJ_TO_PTR(mp_obj_new_tuple(10, NULL));

    // mode: file type and permissions
    mp_uint_t mode = 0;
    if (file.attributes & FAT32_ATTR_DIRECTORY)
    {
        mode = MP_S_IFDIR | 0755; // Directory with rwxr-xr-x
    }
    else
    {
        mode = MP_S_IFREG | 0644; // Regular file with rw-r--r--
    }
    if (file.attributes & FAT32_ATTR_READ_ONLY)
    {
        mode &= ~0222; // Remove write permissions
    }

    t->items[0] = mp_obj_new_int(mode);               // st_mode
    t->items[1] = mp_obj_new_int(file.start_cluster); // st_ino (use cluster)
    t->items[2] = mp_obj_new_int(0);                  // st_dev
    t->items[3] = mp_obj_new_int(1);                  // st_nlink
    t->items[4] = mp_obj_new_int(0);                  // st_uid
    t->items[5] = mp_obj_new_int(0);                  // st_gid
    t->items[6] = mp_obj_new_int(file.file_size);     // st_size
    t->items[7] = mp_obj_new_int(0);                  // st_atime (not tracked)
    t->items[8] = mp_obj_new_int(0);                  // st_mtime (could decode from FAT date/time)
    t->items[9] = mp_obj_new_int(0);                  // st_ctime

    fat32_close(&file);

    return MP_OBJ_FROM_PTR(t);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_vfs_stat_obj, picoware_vfs_stat);

// statvfs(path)
STATIC mp_obj_t picoware_vfs_statvfs(mp_obj_t self_in, mp_obj_t path_in)
{
    (void)path_in;

    uint64_t total_space = 0;
    uint64_t free_space = 0;

    fat32_get_total_space(&total_space);
    fat32_get_free_space(&free_space);

    uint32_t cluster_size = fat32_get_cluster_size();
    if (cluster_size == 0)
    {
        cluster_size = 4096; // Default
    }

    // Build statvfs tuple
    mp_obj_tuple_t *t = MP_OBJ_TO_PTR(mp_obj_new_tuple(10, NULL));
    t->items[0] = mp_obj_new_int(cluster_size);               // f_bsize
    t->items[1] = mp_obj_new_int(cluster_size);               // f_frsize
    t->items[2] = mp_obj_new_int(total_space / cluster_size); // f_blocks
    t->items[3] = mp_obj_new_int(free_space / cluster_size);  // f_bfree
    t->items[4] = mp_obj_new_int(free_space / cluster_size);  // f_bavail
    t->items[5] = mp_obj_new_int(0);                          // f_files (not tracked)
    t->items[6] = mp_obj_new_int(0);                          // f_ffree
    t->items[7] = mp_obj_new_int(0);                          // f_favail
    t->items[8] = mp_obj_new_int(0);                          // f_flag
    t->items[9] = mp_obj_new_int(FAT32_MAX_FILENAME_LEN);     // f_namemax

    return MP_OBJ_FROM_PTR(t);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_vfs_statvfs_obj, picoware_vfs_statvfs);

// chdir(path)
STATIC mp_obj_t picoware_vfs_chdir(mp_obj_t self_in, mp_obj_t path_in)
{
    picoware_vfs_obj_t *vfs = MP_OBJ_TO_PTR(self_in);
    const char *path = mp_obj_str_get_str(path_in);

    char full_path[FAT32_MAX_PATH_LEN];
    build_path(vfs, path, full_path, sizeof(full_path));

    fat32_error_t err = fat32_set_current_dir(full_path);
    if (err != FAT32_OK)
    {
        mp_raise_OSError(MP_ENOENT);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_vfs_chdir_obj, picoware_vfs_chdir);

// getcwd()
STATIC mp_obj_t picoware_vfs_getcwd(mp_obj_t self_in)
{
    (void)self_in;

    char path[FAT32_MAX_PATH_LEN];
    fat32_error_t err = fat32_get_current_dir(path, sizeof(path));
    if (err != FAT32_OK)
    {
        strcpy(path, "/");
    }

    return mp_obj_new_str(path, strlen(path));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_vfs_getcwd_obj, picoware_vfs_getcwd);

STATIC const mp_rom_map_elem_t picoware_vfs_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&picoware_vfs_mount_obj)},
    {MP_ROM_QSTR(MP_QSTR_umount), MP_ROM_PTR(&picoware_vfs_umount_obj)},
    {MP_ROM_QSTR(MP_QSTR_open), MP_ROM_PTR(&picoware_vfs_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_ilistdir), MP_ROM_PTR(&picoware_vfs_ilistdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_mkdir), MP_ROM_PTR(&picoware_vfs_mkdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_rmdir), MP_ROM_PTR(&picoware_vfs_rmdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_remove), MP_ROM_PTR(&picoware_vfs_remove_obj)},
    {MP_ROM_QSTR(MP_QSTR_rename), MP_ROM_PTR(&picoware_vfs_rename_obj)},
    {MP_ROM_QSTR(MP_QSTR_stat), MP_ROM_PTR(&picoware_vfs_stat_obj)},
    {MP_ROM_QSTR(MP_QSTR_statvfs), MP_ROM_PTR(&picoware_vfs_statvfs_obj)},
    {MP_ROM_QSTR(MP_QSTR_chdir), MP_ROM_PTR(&picoware_vfs_chdir_obj)},
    {MP_ROM_QSTR(MP_QSTR_getcwd), MP_ROM_PTR(&picoware_vfs_getcwd_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_vfs_locals_dict, picoware_vfs_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    picoware_vfs_type,
    MP_QSTR_VfsPicoware,
    MP_TYPE_FLAG_NONE,
    make_new, picoware_vfs_make_new,
    locals_dict, &picoware_vfs_locals_dict);

// =============================================================================
// Module Functions
// =============================================================================

// Check if a mount point is already mounted
STATIC bool is_mount_point_in_use(const char *mount_point)
{
    // Call mp_vfs_mount with 0 args to get list of mounts
    mp_map_t kw_args;
    mp_map_init(&kw_args, 0);
    mp_obj_t mount_list = mp_vfs_mount(0, NULL, &kw_args);

    // Iterate through the list to check if mount_point exists
    size_t len;
    mp_obj_t *items;
    mp_obj_list_get(mount_list, &len, &items);

    for (size_t i = 0; i < len; i++)
    {
        mp_obj_t *tuple_items;
        size_t tuple_len;
        mp_obj_tuple_get(items[i], &tuple_len, &tuple_items);
        if (tuple_len >= 2)
        {
            const char *existing_mount = mp_obj_str_get_str(tuple_items[1]);
            if (strcmp(existing_mount, mount_point) == 0)
            {
                return true;
            }
        }
    }
    return false;
}

// Helper function to mount VFS at a given path
STATIC mp_obj_t picoware_vfs_mount_helper(size_t n_args, const mp_obj_t *args)
{
    // mount(mount_point="/sd")
    const char *mount_point = "/sd";
    if (n_args > 0)
    {
        mount_point = mp_obj_str_get_str(args[0]);
    }

    // Check if already mounted at this point
    if (is_mount_point_in_use(mount_point))
    {
        // Already mounted, return true (success)
        return mp_const_true;
    }

    // Initialize and mount FAT32
    if (!fat32_is_ready())
    {
        fat32_init();
    }

    if (!fat32_is_mounted())
    {
        fat32_error_t err = fat32_mount();
        if (err != FAT32_OK)
        {
            mp_raise_OSError(MP_EIO);
        }
    }

    // Create VFS object
    mp_obj_t vfs = picoware_vfs_make_new(&picoware_vfs_type, 0, 0, NULL);

    // Mount it using MicroPython's VFS system
    mp_obj_t mount_point_obj = mp_obj_new_str(mount_point, strlen(mount_point));

    // Build args array for mp_vfs_mount: (vfs, mount_point)
    mp_obj_t mount_args[2] = {vfs, mount_point_obj};
    mp_map_t kw_args;
    mp_map_init(&kw_args, 0);
    mp_vfs_mount(2, mount_args, &kw_args);

    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_vfs_mount_helper_obj, 0, 1, picoware_vfs_mount_helper);

// Unmount helper
STATIC mp_obj_t picoware_vfs_umount_helper(size_t n_args, const mp_obj_t *args)
{
    const char *mount_point = "/sd";
    if (n_args > 0)
    {
        mount_point = mp_obj_str_get_str(args[0]);
    }

    // Check if actually mounted before trying to unmount
    if (!is_mount_point_in_use(mount_point))
    {
        // Not mounted, return success
        return mp_const_none;
    }

    mp_obj_t mount_point_obj = mp_obj_new_str(mount_point, strlen(mount_point));
    mp_vfs_umount(mount_point_obj);
    fat32_unmount();

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_vfs_umount_helper_obj, 0, 1, picoware_vfs_umount_helper);

// =============================================================================
// Module Definition
// =============================================================================

STATIC const mp_rom_map_elem_t picoware_vfs_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_vfs)},
    {MP_ROM_QSTR(MP_QSTR_VfsPicoware), MP_ROM_PTR(&picoware_vfs_type)},
    {MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&picoware_vfs_mount_helper_obj)},
    {MP_ROM_QSTR(MP_QSTR_umount), MP_ROM_PTR(&picoware_vfs_umount_helper_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_vfs_module_globals, picoware_vfs_module_globals_table);

const mp_obj_module_t picoware_vfs_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_vfs_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_picoware_vfs, picoware_vfs_user_cmodule);
