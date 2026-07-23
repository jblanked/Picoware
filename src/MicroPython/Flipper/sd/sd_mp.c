#include "sd_mp.h"
#include "sd.h"
#include "storage.h"
#include "log_mp.h"

#include "extmod/vfs.h"
#include "extmod/vfs_fat.h"
#include "py/stream.h"

#include "flipper_sd_blockdev.h"

#include <string.h>
#include <stdio.h>

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#define SD_MOUNT_POINT "/sd"

static spi_sdcard_t s_sd_card;
static bool s_card_initialised = false;
static bool s_vfs_mounted = false;

static const char *sd_path(const char *user_path)
{
    static char buf[256];
    if (user_path[0] == '/')
    {
        return user_path;
    }
    snprintf(buf, sizeof(buf), SD_MOUNT_POINT "/%s", user_path);
    return buf;
}

static mp_obj_t sd_path_obj(const char *user_path)
{
    return mp_obj_new_str(sd_path(user_path), strlen(sd_path(user_path)));
}

static bool vfs_stat_path(mp_obj_t path_obj, uint32_t *out_mode, uint32_t *out_size)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t stat_result = mp_vfs_stat(path_obj);
        nlr_pop();
        mp_obj_tuple_t *t = MP_OBJ_TO_PTR(stat_result);
        if (out_mode)
            *out_mode = MP_OBJ_SMALL_INT_VALUE(t->items[0]);
        if (out_size)
            *out_size = MP_OBJ_SMALL_INT_VALUE(t->items[5]);
        return true;
    }
    nlr_pop();
    return false;
}

static bool vfs_read_all(mp_obj_t file_obj, uint8_t **out_buf, size_t *out_len)
{
    int errcode = 0;
    const size_t chunk = 256;
    size_t total = 0;
    size_t cap = chunk;
    uint8_t *buf = m_new(uint8_t, cap);
    for (;;)
    {
        if (total + chunk > cap)
        {
            cap *= 2;
            buf = m_renew(uint8_t, buf, cap, cap);
        }
        mp_uint_t n = mp_stream_rw(file_obj, buf + total, chunk, &errcode, MP_STREAM_RW_READ);
        total += n;
        if (n < chunk)
            break;
    }
    if (errcode != 0 && total == 0)
    {
        m_del(uint8_t, buf, cap);
        return false;
    }
    *out_buf = buf;
    *out_len = total;
    return true;
}

static bool is_dot_entry(const char *name)
{
    return (strcmp(name, ".") == 0) || (strcmp(name, "..") == 0);
}

const mp_obj_type_t mp_flipper_file_type;

static inline mp_flipper_file_obj_t *file_from_obj(mp_obj_t self_in)
{
    return (mp_flipper_file_obj_t *)MP_OBJ_TO_PTR(self_in);
}

void mp_fat32_file_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    mp_flipper_file_obj_t *self = file_from_obj(self_in);
    mp_print_str(print, "fat32_file(is_open=");
    mp_print_str(print, self->file.is_open ? "True" : "False");
    mp_print_str(print, ")");
}

mp_obj_t mp_fat32_file_make_new(const mp_obj_type_t *type, size_t n_args,
                                size_t n_kw, const mp_obj_t *args)
{
    (void)n_args;
    (void)n_kw;
    (void)args;
    mp_flipper_file_obj_t *self = mp_obj_malloc_with_finaliser(
        mp_flipper_file_obj_t, &mp_flipper_file_type);
    self->base.type = &mp_flipper_file_type;
    memset(&self->file, 0, sizeof(fat32_file_t));
    self->vfs_file = MP_OBJ_NULL;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t mp_fat32_file_del(mp_obj_t self_in)
{
    mp_flipper_file_obj_t *self = file_from_obj(self_in);
    if (self && self->vfs_file != MP_OBJ_NULL)
    {
        mp_stream_close(self->vfs_file);
        self->vfs_file = MP_OBJ_NULL;
    }
    self->file.is_open = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mp_fat32_file_del_obj, mp_fat32_file_del);

void mp_fat32_file_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    mp_flipper_file_obj_t *self = file_from_obj(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        if (attribute == MP_QSTR_is_open)
        {
            destination[0] = mp_obj_new_bool(self->file.is_open);
        }
        else if (attribute == MP_QSTR_last_entry_read)
        {
            destination[0] = mp_obj_new_bool(self->file.last_entry_read);
        }
        else if (attribute == MP_QSTR_attributes)
        {
            destination[0] = mp_obj_new_int(self->file.attributes);
        }
        else if (attribute == MP_QSTR_start_cluster)
        {
            destination[0] = mp_obj_new_int_from_uint(self->file.start_cluster);
        }
        else if (attribute == MP_QSTR_current_cluster)
        {
            destination[0] = mp_obj_new_int_from_uint(self->file.current_cluster);
        }
        else if (attribute == MP_QSTR_file_size)
        {
            destination[0] = mp_obj_new_int_from_uint(self->file.file_size);
        }
        else if (attribute == MP_QSTR_position)
        {
            destination[0] = mp_obj_new_int_from_uint(self->file.position);
        }
        else if (attribute == MP_QSTR_dir_entry_sector)
        {
            destination[0] = mp_obj_new_int_from_uint(self->file.dir_entry_sector);
        }
        else if (attribute == MP_QSTR_dir_entry_offset)
        {
            destination[0] = mp_obj_new_int_from_uint(self->file.dir_entry_offset);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&mp_fat32_file_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        if (attribute == MP_QSTR_position)
        {
            self->file.position = mp_obj_get_int(destination[1]);
            if (self->vfs_file != MP_OBJ_NULL)
            {
                int errcode;
                mp_stream_seek(self->vfs_file, (mp_off_t)self->file.position, MP_SEEK_SET, &errcode);
            }
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t mp_fat32_file_set_position(mp_obj_t self_in, mp_obj_t position_obj)
{
    mp_flipper_file_obj_t *self = file_from_obj(self_in);
    uint32_t position = mp_obj_get_int(position_obj);
    self->file.position = position;
    if (self->vfs_file != MP_OBJ_NULL)
    {
        int errcode;
        mp_stream_seek(self->vfs_file, (mp_off_t)position, MP_SEEK_SET, &errcode);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mp_fat32_file_set_position_obj, mp_fat32_file_set_position);

static const mp_rom_map_elem_t mp_fat32_file_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_position), MP_ROM_PTR(&mp_fat32_file_set_position_obj)},
};
static MP_DEFINE_CONST_DICT(mp_fat32_file_locals_dict, mp_fat32_file_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    mp_flipper_file_type,
    MP_QSTR_fat32_file,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, mp_fat32_file_print,
    make_new, mp_fat32_file_make_new,
    attr, mp_fat32_file_attr,
    locals_dict, &mp_fat32_file_locals_dict);

mp_obj_t sd_mp_init(void)
{
    if (s_card_initialised)
        return mp_const_none;

    if (!spi_sdcard_card_present())
    {
        PRINT("SD card not present\n");
        return mp_const_false;
    }

    if (!spi_sdcard_init(&s_sd_card))
    {
        PRINT("SD card init failed\n");
        return mp_const_false;
    }
    s_card_initialised = true;
    PRINT("SD card initialised, capacity=%lu blocks\n", (unsigned long)s_sd_card.capacity_blocks);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_init_obj, sd_mp_init);

mp_obj_t sd_mp_mount(void)
{
    if (!s_card_initialised)
        return mp_const_false;
    if (s_vfs_mounted)
        return mp_const_true;

    // Create block device wrapping the SPI SD card
    mp_obj_t bdev = mp_call_function_n_kw(
        MP_OBJ_FROM_PTR(&flipper_sd_blockdev_type), 0, 0, NULL);
    flipper_sd_blockdev_set_card(bdev, &s_sd_card,
                                 s_sd_card.capacity_blocks, 512);

    // Wrap in MicroPython built-in VfsFat
    nlr_buf_t nlr;
    mp_obj_t vfs_fat = MP_OBJ_NULL;
    if (nlr_push(&nlr) == 0)
    {
        vfs_fat = mp_call_function_n_kw(
            MP_OBJ_FROM_PTR(&mp_fat_vfs_type), 1, 0, &bdev);
        nlr_pop();
    }
    else
    {
        nlr_pop();
        PRINT("SD mount failed: cannot create VfsFat\n");
        return mp_const_false;
    }

    if (vfs_fat == MP_OBJ_NULL)
    {
        PRINT("SD mount failed: VfsFat returned NULL\n");
        return mp_const_false;
    }

    // Register at /sd
    mp_obj_t mount_point = mp_obj_new_str(SD_MOUNT_POINT, strlen(SD_MOUNT_POINT));
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t mount_args[2] = {vfs_fat, mount_point};
        mp_vfs_mount(2, mount_args, (mp_map_t *)&mp_const_empty_map);
        nlr_pop();
    }
    else
    {
        nlr_pop();
        PRINT("SD mount failed: mp_vfs_mount error\n");
        return mp_const_false;
    }

    s_vfs_mounted = true;
    PRINT("SD card mounted at %s\n", SD_MOUNT_POINT);
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_mount_obj, sd_mp_mount);

bool sd_storage_mount_if_needed(void)
{
    if (s_card_initialised && s_vfs_mounted)
        return true;

    if (!s_card_initialised)
    {
        if (!spi_sdcard_card_present())
            return false;
        if (!spi_sdcard_init(&s_sd_card))
            return false;
        s_card_initialised = true;
    }

    if (!s_vfs_mounted)
    {
        mp_obj_t bdev = mp_call_function_n_kw(
            MP_OBJ_FROM_PTR(&flipper_sd_blockdev_type), 0, 0, NULL);
        flipper_sd_blockdev_set_card(bdev, &s_sd_card,
                                     s_sd_card.capacity_blocks, 512);

        nlr_buf_t nlr;
        if (nlr_push(&nlr) == 0)
        {
            mp_obj_t vfs_fat = mp_call_function_n_kw(
                MP_OBJ_FROM_PTR(&mp_fat_vfs_type), 1, 0, &bdev);
            nlr_pop();
            if (vfs_fat != MP_OBJ_NULL)
            {
                mp_obj_t mount_point = mp_obj_new_str(SD_MOUNT_POINT, strlen(SD_MOUNT_POINT));
                if (nlr_push(&nlr) == 0)
                {
                    mp_obj_t mount_args[2] = {vfs_fat, mount_point};
                    mp_vfs_mount(2, mount_args, (mp_map_t *)&mp_const_empty_map);
                    nlr_pop();
                    s_vfs_mounted = true;
                    return true;
                }
                else
                {
                    nlr_pop();
                }
            }
        }
        else
        {
            nlr_pop();
        }
    }

    return s_vfs_mounted;
}

mp_obj_t sd_mp_unmount(void)
{
    if (s_vfs_mounted)
    {
        nlr_buf_t nlr;
        mp_obj_t mount_point = mp_obj_new_str(SD_MOUNT_POINT, strlen(SD_MOUNT_POINT));
        if (nlr_push(&nlr) == 0)
        {
            mp_vfs_umount(mount_point);
            nlr_pop();
        }
        else
        {
            nlr_pop();
            PRINT("SD unmount: mp_vfs_umount error (nothing mounted?)\n");
        }
        s_vfs_mounted = false;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_unmount_obj, sd_mp_unmount);

mp_obj_t sd_mp_is_initialized(void)
{
    return mp_obj_new_bool(s_card_initialised);
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_is_initialized_obj, sd_mp_is_initialized);

mp_obj_t sd_mp_get_free_space(void)
{
    if (!s_card_initialised)
        return mp_obj_new_int(0);
    return mp_obj_new_int_from_uint(
        (mp_uint_t)s_sd_card.capacity_blocks * 512 / 2);
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_get_free_space_obj, sd_mp_get_free_space);

mp_obj_t sd_mp_get_total_space(void)
{
    if (!s_card_initialised)
        return mp_obj_new_int(0);
    return mp_obj_new_int_from_uint(
        (mp_uint_t)s_sd_card.capacity_blocks * 512);
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_get_total_space_obj, sd_mp_get_total_space);

mp_obj_t sd_mp_exists(mp_obj_t path_obj)
{
    uint32_t mode;
    return mp_obj_new_bool(vfs_stat_path(sd_path_obj(mp_obj_str_get_str(path_obj)), &mode, NULL));
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_exists_obj, sd_mp_exists);

mp_obj_t sd_mp_is_file(mp_obj_t path_obj)
{
    uint32_t mode;
    if (!vfs_stat_path(sd_path_obj(mp_obj_str_get_str(path_obj)), &mode, NULL))
        return mp_const_false;
    return mp_obj_new_bool(mode == MP_S_IFREG);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_is_file_obj, sd_mp_is_file);

mp_obj_t sd_mp_is_directory(mp_obj_t path_obj)
{
    uint32_t mode;
    if (!vfs_stat_path(sd_path_obj(mp_obj_str_get_str(path_obj)), &mode, NULL))
        return mp_const_false;
    return mp_obj_new_bool(mode == MP_S_IFDIR);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_is_directory_obj, sd_mp_is_directory);

mp_obj_t sd_mp_get_file_size(mp_obj_t filepath_obj)
{
    uint32_t size = 0;
    if (!vfs_stat_path(sd_path_obj(mp_obj_str_get_str(filepath_obj)), NULL, &size))
        return mp_obj_new_int(-1);
    return mp_obj_new_int_from_uint(size);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_get_file_size_obj, sd_mp_get_file_size);

mp_obj_t sd_mp_create_directory(mp_obj_t dirpath_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_vfs_mkdir(sd_path_obj(mp_obj_str_get_str(dirpath_obj)));
        nlr_pop();
        return mp_const_true;
    }
    nlr_pop();
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_create_directory_obj, sd_mp_create_directory);

mp_obj_t sd_mp_create_file(mp_obj_t filepath_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t args[2] = {sd_path_obj(mp_obj_str_get_str(filepath_obj)),
                            MP_OBJ_NEW_QSTR(MP_QSTR_wb)};
        mp_obj_t f = mp_vfs_open(2, args, (mp_map_t *)&mp_const_empty_map);
        mp_stream_close(f);
        nlr_pop();
        return mp_const_true;
    }
    nlr_pop();
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_create_file_obj, sd_mp_create_file);

mp_obj_t sd_mp_remove(mp_obj_t filepath_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_vfs_remove(sd_path_obj(mp_obj_str_get_str(filepath_obj)));
        nlr_pop();
        return mp_const_true;
    }
    nlr_pop();
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_remove_obj, sd_mp_remove);

mp_obj_t sd_mp_rename(size_t n_args, const mp_obj_t *args)
{
    if (n_args != 2)
        mp_raise_ValueError(MP_ERROR_TEXT("rename takes old_path, new_path"));
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_vfs_rename(sd_path_obj(mp_obj_str_get_str(args[0])),
                      sd_path_obj(mp_obj_str_get_str(args[1])));
        nlr_pop();
        return mp_const_none;
    }
    nlr_pop();
    mp_raise_OSError(MP_EIO);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_rename_obj, 2, 2, sd_mp_rename);

mp_obj_t sd_mp_list_directory(mp_obj_t dirpath_obj)
{
    mp_obj_t list = mp_obj_new_list(0, NULL);
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t ilist_args[1] = {sd_path_obj(mp_obj_str_get_str(dirpath_obj))};
        mp_obj_t iter = mp_vfs_ilistdir(1, ilist_args);
        if (iter != mp_const_none)
        {
            mp_obj_t entry;
            while ((entry = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION)
            {
                mp_obj_t *items;
                size_t len;
                mp_obj_tuple_get(entry, &len, &items);
                if (len >= 2)
                {
                    const char *name = mp_obj_str_get_str(items[0]);
                    if (!is_dot_entry(name))
                        mp_obj_list_append(list, mp_obj_new_str(name, strlen(name)));
                }
            }
        }
        nlr_pop();
    }
    else
    {
        nlr_pop();
    }
    return list;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_list_directory_obj, sd_mp_list_directory);

mp_obj_t sd_mp_read_directory(mp_obj_t dirpath_obj)
{
    return sd_mp_list_directory(dirpath_obj);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_read_directory_obj, sd_mp_read_directory);

mp_obj_t sd_mp_file_open(mp_obj_t filepath_obj)
{
    mp_flipper_file_obj_t *self = mp_obj_malloc_with_finaliser(
        mp_flipper_file_obj_t, &mp_flipper_file_type);
    self->base.type = &mp_flipper_file_type;
    memset(&self->file, 0, sizeof(fat32_file_t));

    uint32_t mode, size;
    if (vfs_stat_path(sd_path_obj(mp_obj_str_get_str(filepath_obj)), &mode, &size))
    {
        self->file.file_size = size;
        self->file.attributes = (mode == MP_S_IFDIR) ? FAT32_ATTR_DIRECTORY : FAT32_ATTR_ARCHIVE;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t open_args[2] = {sd_path_obj(mp_obj_str_get_str(filepath_obj)),
                                 MP_OBJ_NEW_QSTR(MP_QSTR_rb)};
        self->vfs_file = mp_vfs_open(2, open_args, (mp_map_t *)&mp_const_empty_map);
        nlr_pop();
        self->file.is_open = true;
        return MP_OBJ_FROM_PTR(self);
    }
    nlr_pop();
    mp_raise_OSError(MP_ENOENT);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_file_open_obj, sd_mp_file_open);

mp_obj_t sd_mp_file_close(mp_obj_t file_obj)
{
    mp_flipper_file_obj_t *self = file_from_obj(file_obj);
    if (self->vfs_file != MP_OBJ_NULL)
    {
        mp_stream_close(self->vfs_file);
        self->vfs_file = MP_OBJ_NULL;
    }
    self->file.is_open = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_file_close_obj, sd_mp_file_close);

mp_obj_t sd_mp_file_read(size_t n_args, const mp_obj_t *args)
{
    if (n_args < 1 || n_args > 3)
        mp_raise_ValueError(MP_ERROR_TEXT("file_read takes file_obj, [offset], [count]"));
    mp_flipper_file_obj_t *self = file_from_obj(args[0]);
    if (self->vfs_file == MP_OBJ_NULL)
        mp_raise_OSError(MP_EIO);

    size_t offset = (n_args >= 2) ? mp_obj_get_int(args[1]) : 0;
    size_t count = (n_args >= 3) ? mp_obj_get_int(args[2]) : 0;

    if (offset > 0 || count == 0)
    {
        int errcode;
        mp_stream_seek(self->vfs_file, (mp_off_t)offset, MP_SEEK_SET, &errcode);
    }
    if (count == 0)
    {
        uint8_t *buf;
        size_t len;
        if (vfs_read_all(self->vfs_file, &buf, &len))
        {
            mp_obj_t result = mp_obj_new_bytes(buf, len);
            m_del(uint8_t, buf, len);
            self->file.position = offset + (uint32_t)len;
            return result;
        }
        return mp_obj_new_bytes((const byte *)"", 0);
    }
    uint8_t *buf = m_new(uint8_t, count + 1);
    int errcode = 0;
    mp_uint_t n = mp_stream_rw(self->vfs_file, buf, count, &errcode, MP_STREAM_RW_READ);
    buf[n] = '\0';
    mp_obj_t result = mp_obj_new_bytes(buf, n);
    m_del(uint8_t, buf, count + 1);
    self->file.position = offset + (uint32_t)n;
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_read_obj, 1, 3, sd_mp_file_read);

mp_obj_t sd_mp_file_readinto(size_t n_args, const mp_obj_t *args)
{
    if (n_args != 2)
        mp_raise_ValueError(MP_ERROR_TEXT("file_readinto takes file_obj, buffer"));
    mp_flipper_file_obj_t *self = file_from_obj(args[0]);
    if (self->vfs_file == MP_OBJ_NULL)
        mp_raise_OSError(MP_EIO);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_WRITE);
    int errcode = 0;
    mp_uint_t n = mp_stream_rw(self->vfs_file, bufinfo.buf, bufinfo.len, &errcode, MP_STREAM_RW_READ);
    self->file.position += (uint32_t)n;
    return mp_obj_new_int(n);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_readinto_obj, 2, 2, sd_mp_file_readinto);

mp_obj_t sd_mp_file_seek(size_t n_args, const mp_obj_t *args)
{
    if (n_args != 2)
        mp_raise_ValueError(MP_ERROR_TEXT("file_seek takes file_obj, position"));
    mp_flipper_file_obj_t *self = file_from_obj(args[0]);
    uint32_t position = mp_obj_get_int(args[1]);
    if (self->vfs_file != MP_OBJ_NULL)
    {
        int errcode;
        mp_stream_seek(self->vfs_file, (mp_off_t)position, MP_SEEK_SET, &errcode);
    }
    self->file.position = position;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_seek_obj, 2, 2, sd_mp_file_seek);

mp_obj_t sd_mp_file_write(size_t n_args, const mp_obj_t *args)
{
    if (n_args != 2)
        mp_raise_ValueError(MP_ERROR_TEXT("file_write takes file_obj, data"));
    mp_flipper_file_obj_t *self = file_from_obj(args[0]);
    if (self->vfs_file == MP_OBJ_NULL)
        mp_raise_OSError(MP_EIO);
    mp_buffer_info_t bufinfo;
    if (mp_get_buffer(args[1], &bufinfo, MP_BUFFER_READ))
    {
        int errcode = 0;
        mp_uint_t n = mp_stream_rw(self->vfs_file, bufinfo.buf, bufinfo.len, &errcode, MP_STREAM_RW_WRITE);
        self->file.position += (uint32_t)n;
        if (self->file.position > self->file.file_size)
            self->file.file_size = self->file.position;
        return mp_obj_new_int(n);
    }
    mp_raise_ValueError(MP_ERROR_TEXT("data must support buffer protocol"));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_write_obj, 2, 2, sd_mp_file_write);

mp_obj_t sd_mp_file_copy(size_t n_args, const mp_obj_t *args)
{
    if (n_args < 2 || n_args > 3)
        mp_raise_ValueError(MP_ERROR_TEXT("file_copy takes file_obj, dest, [chunk]"));
    mp_flipper_file_obj_t *self = file_from_obj(args[0]);
    const char *dest_path = mp_obj_str_get_str(args[1]);
    (void)dest_path;
    if (self->vfs_file == MP_OBJ_NULL)
        mp_raise_OSError(MP_EIO);

    int errcode;
    mp_off_t saved_pos = mp_stream_seek(self->vfs_file, 0, MP_SEEK_CUR, &errcode);
    mp_stream_seek(self->vfs_file, 0, MP_SEEK_SET, &errcode);

    uint8_t *src_buf;
    size_t src_len;
    if (!vfs_read_all(self->vfs_file, &src_buf, &src_len))
    {
        mp_stream_seek(self->vfs_file, saved_pos, MP_SEEK_SET, &errcode);
        mp_raise_OSError(MP_EIO);
    }

    mp_obj_t dest_path_obj = sd_path_obj(dest_path);
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t open_args[2] = {dest_path_obj, MP_OBJ_NEW_QSTR(MP_QSTR_wb)};
        mp_obj_t dst_file = mp_vfs_open(2, open_args, (mp_map_t *)&mp_const_empty_map);
        int werr = 0;
        mp_stream_rw(dst_file, src_buf, src_len, &werr, MP_STREAM_RW_WRITE);
        mp_stream_close(dst_file);
        nlr_pop();
    }
    else
    {
        nlr_pop();
        m_del(uint8_t, src_buf, src_len);
        mp_stream_seek(self->vfs_file, saved_pos, MP_SEEK_SET, &errcode);
        mp_raise_OSError(MP_EIO);
    }
    m_del(uint8_t, src_buf, src_len);
    mp_stream_seek(self->vfs_file, saved_pos, MP_SEEK_SET, &errcode);
    self->file.position = (uint32_t)saved_pos;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_copy_obj, 2, 3, sd_mp_file_copy);

mp_obj_t sd_mp_file_move(size_t n_args, const mp_obj_t *args)
{
    if (n_args != 2)
        mp_raise_ValueError(MP_ERROR_TEXT("file_move takes file_obj, dest"));
    mp_flipper_file_obj_t *self = file_from_obj(args[0]);
    const char *dest_path = mp_obj_str_get_str(args[1]);
    mp_obj_t dest_obj = sd_path_obj(dest_path);

    if (self->vfs_file != MP_OBJ_NULL)
    {
        mp_stream_close(self->vfs_file);
        self->vfs_file = MP_OBJ_NULL;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_vfs_rename(args[0], dest_obj);
        nlr_pop();
        return mp_const_none;
    }
    else
    {
        nlr_pop();
    }
    mp_raise_OSError(MP_EIO);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_move_obj, 2, 2, sd_mp_file_move);

mp_obj_t sd_mp_read(size_t n_args, const mp_obj_t *args)
{
    if (n_args < 1 || n_args > 3)
        mp_raise_ValueError(MP_ERROR_TEXT("read takes path, [offset], [count]"));
    const char *path = mp_obj_str_get_str(args[0]);
    size_t offset = (n_args >= 2) ? mp_obj_get_int(args[1]) : 0;
    size_t count = (n_args >= 3) ? mp_obj_get_int(args[2]) : 0;

    if (count == 0)
    {
        mp_obj_t fobj = sd_mp_file_open(mp_obj_new_str(path, strlen(path)));
        mp_obj_t result = sd_mp_file_read(1, &fobj);
        sd_mp_file_close(fobj);
        return result;
    }
    mp_obj_t fargs[3] = {
        sd_mp_file_open(mp_obj_new_str(path, strlen(path))),
        mp_obj_new_int(offset),
        mp_obj_new_int(count)};
    mp_obj_t result = sd_mp_file_read(3, fargs);
    sd_mp_file_close(fargs[0]);
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_read_obj, 1, 3, sd_mp_read);

mp_obj_t sd_mp_readinto(mp_obj_t filepath_obj, mp_obj_t buffer_obj)
{
    mp_obj_t fobj = sd_mp_file_open(filepath_obj);
    mp_obj_t fargs[2] = {fobj, buffer_obj};
    mp_obj_t result = sd_mp_file_readinto(2, fargs);
    sd_mp_file_close(fobj);
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_2(sd_mp_readinto_obj, sd_mp_readinto);

mp_obj_t sd_mp_write(size_t n_args, const mp_obj_t *args)
{
    if (n_args < 2 || n_args > 3)
        mp_raise_ValueError(MP_ERROR_TEXT("write takes path, data, [overwrite]"));
    const char *path = mp_obj_str_get_str(args[0]);
    bool overwrite = (n_args >= 3) ? mp_obj_is_true(args[2]) : true;

    mp_obj_t fobj;
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t open_args[2] = {
            sd_path_obj(path),
            MP_OBJ_NEW_QSTR(overwrite ? MP_QSTR_wb : MP_QSTR_ab)};
        fobj = mp_vfs_open(2, open_args, (mp_map_t *)&mp_const_empty_map);
        nlr_pop();
    }
    else
    {
        nlr_pop();
        return mp_const_false;
    }

    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(args[1], &bufinfo, MP_BUFFER_READ))
    {
        mp_stream_close(fobj);
        return mp_const_false;
    }
    int errcode = 0;
    mp_stream_rw(fobj, bufinfo.buf, bufinfo.len, &errcode, MP_STREAM_RW_WRITE);
    mp_stream_close(fobj);
    return mp_obj_new_bool(errcode == 0);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_write_obj, 2, 3, sd_mp_write);

mp_obj_t sd_mp_copy(size_t n_args, const mp_obj_t *args)
{
    if (n_args < 2 || n_args > 3)
        mp_raise_ValueError(MP_ERROR_TEXT("copy takes src, dest, [chunk]"));
    const char *src_path = mp_obj_str_get_str(args[0]);
    const char *dest_path = mp_obj_str_get_str(args[1]);
    mp_obj_t fobj = sd_mp_file_open(mp_obj_new_str(src_path, strlen(src_path)));
    mp_obj_t fargs[3] = {fobj, mp_obj_new_str(dest_path, strlen(dest_path)), mp_obj_new_int(2048)};
    mp_obj_t result = sd_mp_file_copy(3, fargs);
    sd_mp_file_close(fobj);
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_copy_obj, 2, 3, sd_mp_copy);

mp_obj_t sd_mp_move(size_t n_args, const mp_obj_t *args)
{
    if (n_args != 2)
        mp_raise_ValueError(MP_ERROR_TEXT("move takes src, dest"));
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_vfs_rename(sd_path_obj(mp_obj_str_get_str(args[0])),
                      sd_path_obj(mp_obj_str_get_str(args[1])));
        nlr_pop();
        return mp_const_none;
    }
    nlr_pop();
    mp_raise_OSError(MP_EIO);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_move_obj, 2, 2, sd_mp_move);

static const mp_rom_map_elem_t sd_mp_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sd_mp)},
    {MP_ROM_QSTR(MP_QSTR_fat32_file), MP_ROM_PTR(&mp_flipper_file_type)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&sd_mp_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&sd_mp_mount_obj)},
    {MP_ROM_QSTR(MP_QSTR_unmount), MP_ROM_PTR(&sd_mp_unmount_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_initialized), MP_ROM_PTR(&sd_mp_is_initialized_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_free_space), MP_ROM_PTR(&sd_mp_get_free_space_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_total_space), MP_ROM_PTR(&sd_mp_get_total_space_obj)},
    {MP_ROM_QSTR(MP_QSTR_exists), MP_ROM_PTR(&sd_mp_exists_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_file), MP_ROM_PTR(&sd_mp_is_file_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_directory), MP_ROM_PTR(&sd_mp_is_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_file_size), MP_ROM_PTR(&sd_mp_get_file_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_directory), MP_ROM_PTR(&sd_mp_create_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_file), MP_ROM_PTR(&sd_mp_create_file_obj)},
    {MP_ROM_QSTR(MP_QSTR_remove), MP_ROM_PTR(&sd_mp_remove_obj)},
    {MP_ROM_QSTR(MP_QSTR_rename), MP_ROM_PTR(&sd_mp_rename_obj)},
    {MP_ROM_QSTR(MP_QSTR_list_directory), MP_ROM_PTR(&sd_mp_list_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_directory), MP_ROM_PTR(&sd_mp_read_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_open), MP_ROM_PTR(&sd_mp_file_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_close), MP_ROM_PTR(&sd_mp_file_close_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_read), MP_ROM_PTR(&sd_mp_file_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_readinto), MP_ROM_PTR(&sd_mp_file_readinto_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_seek), MP_ROM_PTR(&sd_mp_file_seek_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_write), MP_ROM_PTR(&sd_mp_file_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_copy), MP_ROM_PTR(&sd_mp_file_copy_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_move), MP_ROM_PTR(&sd_mp_file_move_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&sd_mp_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_readinto), MP_ROM_PTR(&sd_mp_readinto_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&sd_mp_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_copy), MP_ROM_PTR(&sd_mp_copy_obj)},
    {MP_ROM_QSTR(MP_QSTR_move), MP_ROM_PTR(&sd_mp_move_obj)},
    {MP_ROM_QSTR(MP_QSTR_FlipperSDBlockDev), MP_ROM_PTR(&flipper_sd_blockdev_type)},
};
static MP_DEFINE_CONST_DICT(sd_mp_module_globals, sd_mp_module_globals_table);

const mp_obj_module_t sd_mp_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&sd_mp_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_sd_mp, sd_mp_user_cmodule);
