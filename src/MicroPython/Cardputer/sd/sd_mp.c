#include "sd_mp.h"
#include "sdcard.h"
#include "extmod/vfs.h"

#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

const mp_obj_type_t mp_fat32_file_type;

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#define SD_MP_ROOT "/sdcard"
#define SD_MP_PATH_MAX (512)
#define SD_MP_COPY_CHUNK_DEFAULT (2048)

typedef struct
{
    mp_obj_base_t base;
    fat32_file_t file;
    FILE *handle;
    char path[SD_MP_PATH_MAX];
} mp_cardputer_file_obj_t;

static inline mp_cardputer_file_obj_t *sd_mp_file_from_obj(mp_obj_t self_in)
{
    return (mp_cardputer_file_obj_t *)MP_OBJ_TO_PTR(self_in);
}

static bool sd_mp_is_dot_entry(const char *name)
{
    return (strcmp(name, ".") == 0) || (strcmp(name, "..") == 0);
}

static bool sd_mp_ensure_mounted(void)
{
    return sdcard_is_mounted() || sdcard_mount() == ESP_OK;
}

static bool sd_mp_normalize_path(const char *input, char *output, size_t output_size)
{
    int written = 0;

    if (input == NULL || input[0] == '\0' || output == NULL || output_size == 0)
    {
        return false;
    }

    if (strncmp(input, SD_MP_ROOT, strlen(SD_MP_ROOT)) == 0)
    {
        written = snprintf(output, output_size, "%s", input);
    }
    else if (input[0] == '/')
    {
        written = snprintf(output, output_size, SD_MP_ROOT "%s", input);
    }
    else
    {
        written = snprintf(output, output_size, SD_MP_ROOT "/%s", input);
    }

    return written > 0 && (size_t)written < output_size;
}

static bool sd_mp_ensure_parent_dirs(const char *full_path)
{
    char path[SD_MP_PATH_MAX];
    const size_t root_len = strlen(SD_MP_ROOT);

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

static void sd_mp_refresh_file_metadata(mp_cardputer_file_obj_t *self)
{
    struct stat st = {0};

    if (self == NULL)
    {
        return;
    }

    if (stat(self->path, &st) == 0)
    {
        self->file.file_size = (uint32_t)((st.st_size >= 0) ? st.st_size : 0);
        self->file.attributes = S_ISDIR(st.st_mode) ? FAT32_ATTR_DIRECTORY : FAT32_ATTR_ARCHIVE;
    }

    if (self->handle != NULL)
    {
        const long pos = ftell(self->handle);
        if (pos >= 0)
        {
            self->file.position = (uint32_t)pos;
        }
    }
}

static void sd_mp_close_file_handle(mp_cardputer_file_obj_t *self)
{
    if (self == NULL)
    {
        return;
    }

    if (self->handle != NULL)
    {
        fclose(self->handle);
        self->handle = NULL;
    }

    self->file.is_open = false;
    self->file.last_entry_read = false;
}

static bool sd_mp_open_file_handle(mp_cardputer_file_obj_t *self, const char *mode, bool create_if_missing)
{
    if (self == NULL || mode == NULL || self->path[0] == '\0')
    {
        errno = EINVAL;
        return false;
    }

    if (self->handle != NULL)
    {
        return true;
    }

    self->handle = fopen(self->path, mode);
    if (self->handle == NULL && create_if_missing)
    {
        if (!sd_mp_ensure_parent_dirs(self->path))
        {
            errno = EIO;
            return false;
        }
        self->handle = fopen(self->path, "wb+");
    }

    if (self->handle == NULL)
    {
        return false;
    }

    self->file.is_open = true;
    self->file.last_entry_read = false;
    sd_mp_refresh_file_metadata(self);
    return true;
}

static bool sd_mp_remove_recursive_abs(const char *abs_path)
{
    struct stat st = {0};

    if (abs_path == NULL)
    {
        errno = EINVAL;
        return false;
    }

    if (stat(abs_path, &st) != 0)
    {
        return errno == ENOENT;
    }

    if (S_ISDIR(st.st_mode))
    {
        DIR *dir = opendir(abs_path);
        if (dir == NULL)
        {
            return false;
        }

        struct dirent *entry = NULL;
        while ((entry = readdir(dir)) != NULL)
        {
            char child[SD_MP_PATH_MAX];
            int written = 0;

            if (sd_mp_is_dot_entry(entry->d_name))
            {
                continue;
            }

            written = snprintf(child, sizeof(child), "%s/%s", abs_path, entry->d_name);
            if (written <= 0 || (size_t)written >= sizeof(child) || !sd_mp_remove_recursive_abs(child))
            {
                closedir(dir);
                return false;
            }
        }

        closedir(dir);
        return rmdir(abs_path) == 0;
    }

    return unlink(abs_path) == 0;
}

static bool sd_mp_copy_file_abs(const char *source_abs, const char *destination_abs, size_t bytes_per_chunk)
{
    FILE *source = NULL;
    FILE *destination = NULL;
    uint8_t *buffer = NULL;
    bool ok = false;
    size_t chunk = bytes_per_chunk == 0 ? SD_MP_COPY_CHUNK_DEFAULT : bytes_per_chunk;

    if (source_abs == NULL || destination_abs == NULL)
    {
        errno = EINVAL;
        return false;
    }

    source = fopen(source_abs, "rb");
    if (source == NULL)
    {
        goto cleanup;
    }

    if (!sd_mp_ensure_parent_dirs(destination_abs))
    {
        errno = EIO;
        goto cleanup;
    }

    destination = fopen(destination_abs, "wb");
    if (destination == NULL)
    {
        goto cleanup;
    }

    buffer = (uint8_t *)m_malloc(chunk);
    if (buffer == NULL)
    {
        errno = ENOMEM;
        goto cleanup;
    }

    ok = true;
    while (ok)
    {
        const size_t bytes_read = fread(buffer, 1, chunk, source);
        if (bytes_read == 0)
        {
            if (ferror(source))
            {
                ok = false;
            }
            break;
        }
        if (fwrite(buffer, 1, bytes_read, destination) != bytes_read)
        {
            ok = false;
            break;
        }
    }

cleanup:
    if (buffer != NULL)
    {
        m_free(buffer);
    }
    if (destination != NULL)
    {
        fclose(destination);
    }
    if (source != NULL)
    {
        fclose(source);
    }
    return ok;
}

static bool sd_mp_copy_recursive_abs(const char *source_abs, const char *destination_abs, size_t bytes_per_chunk)
{
    struct stat st = {0};

    if (source_abs == NULL || destination_abs == NULL)
    {
        errno = EINVAL;
        return false;
    }

    if (stat(source_abs, &st) != 0)
    {
        return false;
    }

    if (S_ISDIR(st.st_mode))
    {
        DIR *dir = NULL;
        struct dirent *entry = NULL;

        if (mkdir(destination_abs, 0775) != 0 && errno != EEXIST)
        {
            return false;
        }

        dir = opendir(source_abs);
        if (dir == NULL)
        {
            return false;
        }

        while ((entry = readdir(dir)) != NULL)
        {
            char source_child[SD_MP_PATH_MAX];
            char destination_child[SD_MP_PATH_MAX];
            int src_written = 0;
            int dst_written = 0;

            if (sd_mp_is_dot_entry(entry->d_name))
            {
                continue;
            }

            src_written = snprintf(source_child, sizeof(source_child), "%s/%s", source_abs, entry->d_name);
            dst_written = snprintf(destination_child, sizeof(destination_child), "%s/%s", destination_abs, entry->d_name);
            if (src_written <= 0 || dst_written <= 0 ||
                (size_t)src_written >= sizeof(source_child) ||
                (size_t)dst_written >= sizeof(destination_child) ||
                !sd_mp_copy_recursive_abs(source_child, destination_child, bytes_per_chunk))
            {
                closedir(dir);
                return false;
            }
        }

        closedir(dir);
        return true;
    }

    return sd_mp_copy_file_abs(source_abs, destination_abs, bytes_per_chunk);
}

static void sd_mp_stat_to_fat_datetime(const struct stat *st, uint16_t *fat_date, uint16_t *fat_time)
{
    struct tm tm_value = {0};
    int year = 0;

    if (fat_date == NULL || fat_time == NULL)
    {
        return;
    }

    *fat_date = 0;
    *fat_time = 0;
    if (st == NULL)
    {
        return;
    }

    localtime_r(&st->st_mtime, &tm_value);
    year = tm_value.tm_year + 1900;
    if (year < 1980 || year > 2107)
    {
        return;
    }

    *fat_date = (uint16_t)(((year - 1980) << 9) | ((tm_value.tm_mon + 1) << 5) | tm_value.tm_mday);
    *fat_time = (uint16_t)((tm_value.tm_hour << 11) | (tm_value.tm_min << 5) | (tm_value.tm_sec / 2));
}

void mp_fat32_file_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    mp_cardputer_file_obj_t *self = sd_mp_file_from_obj(self_in);

    mp_print_str(print, "fat32_file(");
    mp_print_str(print, "is_open=");
    mp_print_str(print, self->file.is_open ? "True" : "False");
    mp_print_str(print, ", last_entry_read=");
    mp_print_str(print, self->file.last_entry_read ? "True" : "False");
    mp_print_str(print, ", attributes=");
    mp_obj_print_helper(print, mp_obj_new_int(self->file.attributes), PRINT_REPR);
    mp_print_str(print, ", start_cluster=");
    mp_obj_print_helper(print, mp_obj_new_int(self->file.start_cluster), PRINT_REPR);
    mp_print_str(print, ", current_cluster=");
    mp_obj_print_helper(print, mp_obj_new_int(self->file.current_cluster), PRINT_REPR);
    mp_print_str(print, ", file_size=");
    mp_obj_print_helper(print, mp_obj_new_int(self->file.file_size), PRINT_REPR);
    mp_print_str(print, ", position=");
    mp_obj_print_helper(print, mp_obj_new_int(self->file.position), PRINT_REPR);
    mp_print_str(print, ", dir_entry_sector=");
    mp_obj_print_helper(print, mp_obj_new_int(self->file.dir_entry_sector), PRINT_REPR);
    mp_print_str(print, ", dir_entry_offset=");
    mp_obj_print_helper(print, mp_obj_new_int(self->file.dir_entry_offset), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t mp_fat32_file_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    (void)type;
    (void)n_args;
    (void)n_kw;
    (void)args;

    mp_cardputer_file_obj_t *self = mp_obj_malloc_with_finaliser(mp_cardputer_file_obj_t, &mp_fat32_file_type);
    self->base.type = &mp_fat32_file_type;
    memset(&self->file, 0, sizeof(self->file));
    self->handle = NULL;
    self->path[0] = '\0';
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t mp_fat32_file_del(mp_obj_t self_in)
{
    mp_cardputer_file_obj_t *self = sd_mp_file_from_obj(self_in);
    sd_mp_close_file_handle(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mp_fat32_file_del_obj, mp_fat32_file_del);

void mp_fat32_file_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    mp_cardputer_file_obj_t *self = sd_mp_file_from_obj(self_in);

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
            mp_int_t new_pos = mp_obj_get_int(destination[1]);
            if (new_pos < 0)
            {
                mp_raise_ValueError(MP_ERROR_TEXT("position must be >= 0"));
            }
            if (self->handle != NULL && fseek(self->handle, (long)new_pos, SEEK_SET) != 0)
            {
                mp_raise_OSError(errno == 0 ? MP_EIO : errno);
            }
            self->file.position = (uint32_t)new_pos;
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t mp_fat32_file_set_position(mp_obj_t self_in, mp_obj_t position_obj)
{
    mp_cardputer_file_obj_t *self = sd_mp_file_from_obj(self_in);
    mp_int_t position = mp_obj_get_int(position_obj);

    if (position < 0)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("position must be >= 0"));
    }

    if (!sd_mp_open_file_handle(self, "rb+", true) || fseek(self->handle, (long)position, SEEK_SET) != 0)
    {
        PRINT("Failed to seek in file.\n");
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    self->file.position = (uint32_t)position;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mp_fat32_file_set_position_obj, mp_fat32_file_set_position);

static const mp_rom_map_elem_t mp_fat32_file_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_position), MP_ROM_PTR(&mp_fat32_file_set_position_obj)},
};
static MP_DEFINE_CONST_DICT(mp_fat32_file_locals_dict, mp_fat32_file_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    mp_fat32_file_type,
    MP_QSTR_fat32_file,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, mp_fat32_file_print,
    make_new, mp_fat32_file_make_new,
    attr, mp_fat32_file_attr,
    locals_dict, &mp_fat32_file_locals_dict);

mp_obj_t sd_mp_init(void)
{
    if (!sd_mp_ensure_mounted())
    {
        PRINT("Failed to initialize SD card.\n");
        mp_raise_OSError(MP_EIO);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_init_obj, sd_mp_init);

mp_obj_t sd_mp_copy(size_t n_args, const mp_obj_t *args)
{
    char source_path[SD_MP_PATH_MAX];
    char destination_path[SD_MP_PATH_MAX];
    struct stat destination_stat = {0};
    size_t bytes_per_chunk = SD_MP_COPY_CHUNK_DEFAULT;

    if (n_args < 2 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("copy requires 2 or 3 arguments: source_path, destination_path, [bytes_per_chunk]"));
    }

    if (!sd_mp_normalize_path(mp_obj_str_get_str(args[0]), source_path, sizeof(source_path)) ||
        !sd_mp_normalize_path(mp_obj_str_get_str(args[1]), destination_path, sizeof(destination_path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (n_args == 3)
    {
        mp_int_t value = mp_obj_get_int(args[2]);
        if (value <= 0)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("bytes_per_chunk must be > 0"));
        }
        bytes_per_chunk = (size_t)value;
    }

    if (!sd_mp_ensure_mounted())
    {
        mp_raise_OSError(MP_EIO);
    }

    if (stat(destination_path, &destination_stat) == 0)
    {
        mp_raise_OSError(MP_EEXIST);
    }

    if (!sd_mp_copy_recursive_abs(source_path, destination_path, bytes_per_chunk))
    {
        PRINT("Failed to copy path.\n");
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_copy_obj, 2, 3, sd_mp_copy);

mp_obj_t sd_mp_create_file(mp_obj_t filepath_obj)
{
    char path[SD_MP_PATH_MAX];
    FILE *file = NULL;

    if (!sd_mp_normalize_path(mp_obj_str_get_str(filepath_obj), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (!sd_mp_ensure_mounted())
    {
        mp_raise_OSError(MP_EIO);
    }

    if (!sd_mp_ensure_parent_dirs(path))
    {
        mp_raise_OSError(MP_EIO);
    }

    file = fopen(path, "ab");
    if (file == NULL)
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    fclose(file);
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_create_file_obj, sd_mp_create_file);

mp_obj_t sd_mp_create_directory(mp_obj_t directory_path_obj)
{
    char path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (!sd_mp_normalize_path(mp_obj_str_get_str(directory_path_obj), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (!sd_mp_ensure_mounted())
    {
        mp_raise_OSError(MP_EIO);
    }

    if (stat(path, &st) == 0)
    {
        if (S_ISDIR(st.st_mode))
        {
            return mp_const_true;
        }
        mp_raise_OSError(MP_EEXIST);
    }

    if (!sd_mp_ensure_parent_dirs(path))
    {
        mp_raise_OSError(MP_EIO);
    }

    if (mkdir(path, 0775) != 0 && errno != EEXIST)
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_create_directory_obj, sd_mp_create_directory);

mp_obj_t sd_mp_exists(mp_obj_t path_obj)
{
    char path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (!sd_mp_normalize_path(mp_obj_str_get_str(path_obj), path, sizeof(path)))
    {
        return mp_const_false;
    }

    return (stat(path, &st) == 0) ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_exists_obj, sd_mp_exists);

mp_obj_t sd_mp_get_file_size(mp_obj_t filepath_obj)
{
    char path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (!sd_mp_normalize_path(mp_obj_str_get_str(filepath_obj), path, sizeof(path)))
    {
        return mp_obj_new_int(0);
    }

    if (stat(path, &st) != 0 || S_ISDIR(st.st_mode))
    {
        return mp_obj_new_int(0);
    }

    return mp_obj_new_int_from_uint((uint32_t)((st.st_size >= 0) ? st.st_size : 0));
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_get_file_size_obj, sd_mp_get_file_size);

mp_obj_t sd_mp_file_close(mp_obj_t file_obj)
{
    mp_cardputer_file_obj_t *file = sd_mp_file_from_obj(file_obj);
    sd_mp_close_file_handle(file);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_file_close_obj, sd_mp_file_close);

mp_obj_t sd_mp_file_copy(size_t n_args, const mp_obj_t *args)
{
    mp_cardputer_file_obj_t *source = NULL;
    char destination_path[SD_MP_PATH_MAX];
    struct stat st = {0};
    size_t bytes_per_chunk = SD_MP_COPY_CHUNK_DEFAULT;

    if (n_args < 2 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("file_copy requires 2 arguments: mp_file_obj, destination_path, [bytes_per_chunk]"));
    }

    source = sd_mp_file_from_obj(args[0]);
    if (source->path[0] == '\0')
    {
        mp_raise_OSError(MP_ENOENT);
    }

    if (!sd_mp_normalize_path(mp_obj_str_get_str(args[1]), destination_path, sizeof(destination_path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (n_args == 3)
    {
        mp_int_t value = mp_obj_get_int(args[2]);
        if (value <= 0)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("bytes_per_chunk must be > 0"));
        }
        bytes_per_chunk = (size_t)value;
    }

    if (stat(source->path, &st) != 0)
    {
        mp_raise_OSError(MP_ENOENT);
    }
    if (stat(destination_path, &st) == 0)
    {
        mp_raise_OSError(MP_EEXIST);
    }

    if (!sd_mp_copy_recursive_abs(source->path, destination_path, bytes_per_chunk))
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_copy_obj, 2, 3, sd_mp_file_copy);

mp_obj_t sd_mp_file_move(size_t n_args, const mp_obj_t *args)
{
    mp_cardputer_file_obj_t *source = NULL;
    char destination_path[SD_MP_PATH_MAX];
    struct stat st = {0};
    size_t bytes_per_chunk = SD_MP_COPY_CHUNK_DEFAULT;

    if (n_args < 2 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("file_move requires 2 arguments: source_file_obj, destination_path, [bytes_per_chunk]"));
    }

    source = sd_mp_file_from_obj(args[0]);
    if (source->path[0] == '\0')
    {
        mp_raise_OSError(MP_ENOENT);
    }

    if (!sd_mp_normalize_path(mp_obj_str_get_str(args[1]), destination_path, sizeof(destination_path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (n_args == 3)
    {
        mp_int_t value = mp_obj_get_int(args[2]);
        if (value <= 0)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("bytes_per_chunk must be > 0"));
        }
        bytes_per_chunk = (size_t)value;
    }

    if (stat(source->path, &st) != 0)
    {
        mp_raise_OSError(MP_ENOENT);
    }
    if (stat(destination_path, &st) == 0)
    {
        mp_raise_OSError(MP_EEXIST);
    }

    if (!sd_mp_ensure_parent_dirs(destination_path))
    {
        mp_raise_OSError(MP_EIO);
    }

    if (rename(source->path, destination_path) != 0)
    {
        if (errno != EXDEV ||
            !sd_mp_copy_recursive_abs(source->path, destination_path, bytes_per_chunk) ||
            !sd_mp_remove_recursive_abs(source->path))
        {
            mp_raise_OSError(errno == 0 ? MP_EIO : errno);
        }
    }

    sd_mp_close_file_handle(source);
    snprintf(source->path, sizeof(source->path), "%s", destination_path);
    source->file.is_open = false;
    source->file.position = 0;
    source->file.last_entry_read = false;
    sd_mp_refresh_file_metadata(source);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_move_obj, 2, 3, sd_mp_file_move);

mp_obj_t sd_mp_file_open(mp_obj_t filepath_obj)
{
    char path[SD_MP_PATH_MAX];
    mp_cardputer_file_obj_t *file_obj = NULL;

    if (!sd_mp_normalize_path(mp_obj_str_get_str(filepath_obj), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (!sd_mp_ensure_mounted())
    {
        mp_raise_OSError(MP_EIO);
    }

    file_obj = (mp_cardputer_file_obj_t *)MP_OBJ_TO_PTR(mp_fat32_file_make_new(&mp_fat32_file_type, 0, 0, NULL));
    snprintf(file_obj->path, sizeof(file_obj->path), "%s", path);

    if (!sd_mp_open_file_handle(file_obj, "rb+", true))
    {
        PRINT("Failed to open and create file.\n");
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    return MP_OBJ_FROM_PTR(file_obj);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_file_open_obj, sd_mp_file_open);

mp_obj_t sd_mp_file_read(size_t n_args, const mp_obj_t *args)
{
    mp_cardputer_file_obj_t *file_obj = NULL;
    mp_int_t index = 0;
    mp_int_t count = 0;
    size_t to_read = 0;
    uint8_t *buffer = NULL;
    size_t bytes_read = 0;

    if (n_args < 1 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("read requires at least 1 argument: mp_file_obj, [index], [count]"));
    }

    file_obj = sd_mp_file_from_obj(args[0]);
    if (file_obj->path[0] == '\0')
    {
        mp_raise_OSError(MP_ENOENT);
    }

    if (!sd_mp_open_file_handle(file_obj, "rb+", false))
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    if (n_args >= 2)
    {
        index = mp_obj_get_int(args[1]);
        if (index < 0)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("index must be >= 0"));
        }
    }
    if (n_args == 3)
    {
        count = mp_obj_get_int(args[2]);
        if (count < 0)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("count must be >= 0"));
        }
    }

    if (fseek(file_obj->handle, (long)index, SEEK_SET) != 0)
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    if (count == 0)
    {
        const long current = ftell(file_obj->handle);
        long end = -1;

        if (current < 0 || fseek(file_obj->handle, 0, SEEK_END) != 0)
        {
            mp_raise_OSError(errno == 0 ? MP_EIO : errno);
        }
        end = ftell(file_obj->handle);
        if (end < current || fseek(file_obj->handle, current, SEEK_SET) != 0)
        {
            mp_raise_OSError(errno == 0 ? MP_EIO : errno);
        }
        to_read = (size_t)(end - current);
    }
    else
    {
        to_read = (size_t)count;
    }

    if (to_read == 0)
    {
        file_obj->file.position = (uint32_t)index;
        return mp_obj_new_bytes((const byte *)"", 0);
    }

    buffer = (uint8_t *)m_malloc(to_read);
    if (buffer == NULL)
    {
        mp_raise_OSError(MP_ENOMEM);
    }

    bytes_read = fread(buffer, 1, to_read, file_obj->handle);
    if (ferror(file_obj->handle))
    {
        m_free(buffer);
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    file_obj->file.position = (uint32_t)ftell(file_obj->handle);
    mp_obj_t result = mp_obj_new_bytes(buffer, bytes_read);
    m_free(buffer);
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_read_obj, 1, 3, sd_mp_file_read);

mp_obj_t sd_mp_file_readinto(size_t n_args, const mp_obj_t *args)
{
    mp_cardputer_file_obj_t *file_obj = NULL;
    mp_buffer_info_t bufinfo;
    size_t bytes_read = 0;

    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("readinto requires 2 arguments: mp_file_obj, buffer"));
    }

    file_obj = sd_mp_file_from_obj(args[0]);
    if (!sd_mp_open_file_handle(file_obj, "rb+", false))
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_WRITE);
    bytes_read = fread(bufinfo.buf, 1, bufinfo.len, file_obj->handle);
    if (ferror(file_obj->handle))
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    file_obj->file.position = (uint32_t)ftell(file_obj->handle);
    return mp_obj_new_int(bytes_read);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_readinto_obj, 2, 2, sd_mp_file_readinto);

mp_obj_t sd_mp_file_seek(size_t n_args, const mp_obj_t *args)
{
    mp_cardputer_file_obj_t *file_obj = NULL;
    mp_int_t position = 0;

    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("seek requires 2 arguments: mp_file_obj,position"));
    }

    file_obj = sd_mp_file_from_obj(args[0]);
    position = mp_obj_get_int(args[1]);
    if (position < 0)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("position must be >= 0"));
    }

    if (!sd_mp_open_file_handle(file_obj, "rb+", true) || fseek(file_obj->handle, (long)position, SEEK_SET) != 0)
    {
        PRINT("Failed to seek in file.\n");
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    file_obj->file.position = (uint32_t)position;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_seek_obj, 2, 2, sd_mp_file_seek);

mp_obj_t sd_mp_file_write(size_t n_args, const mp_obj_t *args)
{
    mp_cardputer_file_obj_t *file_obj = NULL;
    mp_buffer_info_t bufinfo;
    size_t bytes_written = 0;

    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("write requires 2 arguments: mp_file_obj, data"));
    }

    file_obj = sd_mp_file_from_obj(args[0]);
    if (!sd_mp_open_file_handle(file_obj, "rb+", true))
    {
        PRINT("Failed to open file for writing.\n");
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_READ);
    bytes_written = fwrite(bufinfo.buf, 1, bufinfo.len, file_obj->handle);
    if (bytes_written != bufinfo.len)
    {
        PRINT("Failed to write to file.\n");
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    fflush(file_obj->handle);
    sd_mp_refresh_file_metadata(file_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_write_obj, 2, 2, sd_mp_file_write);

static bool sd_mp_get_space_info(uint64_t *total_bytes, uint64_t *free_bytes)
{
    mp_obj_t statvfs = mp_const_none;
    mp_obj_t *items = NULL;
    size_t items_len = 0;
    nlr_buf_t nlr;

    if (nlr_push(&nlr) != 0)
    {
        return false;
    }

    statvfs = mp_vfs_statvfs(mp_obj_new_str(SD_MP_ROOT, strlen(SD_MP_ROOT)));
    mp_obj_get_array(statvfs, &items_len, &items);
    if (items_len < 4)
    {
        nlr_pop();
        return false;
    }

    if (total_bytes != NULL)
    {
        *total_bytes = (uint64_t)mp_obj_get_int(items[0]) * (uint64_t)mp_obj_get_int(items[2]);
    }
    if (free_bytes != NULL)
    {
        *free_bytes = (uint64_t)mp_obj_get_int(items[0]) * (uint64_t)mp_obj_get_int(items[3]);
    }

    nlr_pop();
    return true;
}

mp_obj_t sd_mp_get_free_space(void)
{
    uint64_t free_bytes = 0;

    if (!sd_mp_ensure_mounted())
    {
        PRINT("Failed to get free space.\n");
        return mp_obj_new_int(0);
    }

    if (!sd_mp_get_space_info(NULL, &free_bytes))
    {
        PRINT("Failed to get free space.\n");
        return mp_obj_new_int(0);
    }

    return mp_obj_new_int_from_ull((uint64_t)free_bytes);
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_get_free_space_obj, sd_mp_get_free_space);

mp_obj_t sd_mp_get_total_space(void)
{
    uint64_t total_bytes = 0;

    if (!sd_mp_ensure_mounted())
    {
        PRINT("Failed to get total space.\n");
        return mp_obj_new_int(0);
    }

    if (!sd_mp_get_space_info(&total_bytes, NULL))
    {
        PRINT("Failed to get total space.\n");
        return mp_obj_new_int(0);
    }

    return mp_obj_new_int_from_ull((uint64_t)total_bytes);
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_get_total_space_obj, sd_mp_get_total_space);

mp_obj_t sd_mp_is_initialized(void)
{
    return mp_obj_new_bool(sdcard_is_mounted());
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_is_initialized_obj, sd_mp_is_initialized);

mp_obj_t sd_mp_is_directory(mp_obj_t path_obj)
{
    char path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (!sd_mp_normalize_path(mp_obj_str_get_str(path_obj), path, sizeof(path)))
    {
        return mp_const_false;
    }

    if (stat(path, &st) != 0)
    {
        return mp_const_false;
    }

    return S_ISDIR(st.st_mode) ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_is_directory_obj, sd_mp_is_directory);

mp_obj_t sd_mp_is_file(mp_obj_t path_obj)
{
    char path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (!sd_mp_normalize_path(mp_obj_str_get_str(path_obj), path, sizeof(path)))
    {
        return mp_const_false;
    }

    if (stat(path, &st) != 0)
    {
        return mp_const_false;
    }

    return S_ISREG(st.st_mode) ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_is_file_obj, sd_mp_is_file);

mp_obj_t sd_mp_list_directory(mp_obj_t dirpath_obj)
{
    char path[SD_MP_PATH_MAX];
    DIR *dir = NULL;
    struct dirent *entry = NULL;
    mp_obj_t list = mp_obj_new_list(0, NULL);

    if (!sd_mp_normalize_path(mp_obj_str_get_str(dirpath_obj), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    dir = opendir(path);
    if (dir == NULL)
    {
        PRINT("Failed to open directory for listing.\n");
        mp_raise_OSError(MP_ENOENT);
    }

    while ((entry = readdir(dir)) != NULL)
    {
        if (sd_mp_is_dot_entry(entry->d_name))
        {
            continue;
        }
        mp_obj_list_append(list, mp_obj_new_str(entry->d_name, strlen(entry->d_name)));
    }

    closedir(dir);
    return list;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_list_directory_obj, sd_mp_list_directory);

mp_obj_t sd_mp_mount(void)
{
    if (!sd_mp_ensure_mounted())
    {
        PRINT("Failed to mount SD card.\n");
        mp_raise_OSError(MP_EIO);
    }
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_mount_obj, sd_mp_mount);

mp_obj_t sd_mp_move(size_t n_args, const mp_obj_t *args)
{
    char source_path[SD_MP_PATH_MAX];
    char destination_path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("move requires 2 arguments: source_path, destination_path"));
    }

    if (!sd_mp_normalize_path(mp_obj_str_get_str(args[0]), source_path, sizeof(source_path)) ||
        !sd_mp_normalize_path(mp_obj_str_get_str(args[1]), destination_path, sizeof(destination_path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (stat(source_path, &st) != 0)
    {
        PRINT("Failed to open source for moving.\n");
        mp_raise_OSError(MP_ENOENT);
    }
    if (stat(destination_path, &st) == 0)
    {
        mp_raise_OSError(MP_EEXIST);
    }

    if (!sd_mp_ensure_parent_dirs(destination_path))
    {
        mp_raise_OSError(MP_EIO);
    }

    if (rename(source_path, destination_path) != 0)
    {
        if (errno != EXDEV ||
            !sd_mp_copy_recursive_abs(source_path, destination_path, SD_MP_COPY_CHUNK_DEFAULT) ||
            !sd_mp_remove_recursive_abs(source_path))
        {
            PRINT("Failed to move path.\n");
            mp_raise_OSError(errno == 0 ? MP_EIO : errno);
        }
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_move_obj, 2, 2, sd_mp_move);

mp_obj_t sd_mp_read(size_t n_args, const mp_obj_t *args)
{
    char path[SD_MP_PATH_MAX];
    FILE *file = NULL;
    mp_int_t index = 0;
    mp_int_t count = 0;
    size_t to_read = 0;
    uint8_t *buffer = NULL;
    size_t bytes_read = 0;
    bool read_error = false;

    if (n_args < 1 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("read requires at least 1 argument: file_path, [index], [count]"));
    }

    if (!sd_mp_normalize_path(mp_obj_str_get_str(args[0]), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (n_args >= 2)
    {
        index = mp_obj_get_int(args[1]);
        if (index < 0)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("index must be >= 0"));
        }
    }
    if (n_args == 3)
    {
        count = mp_obj_get_int(args[2]);
        if (count < 0)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("count must be >= 0"));
        }
    }

    file = fopen(path, "rb");
    if (file == NULL)
    {
        mp_raise_OSError(MP_ENOENT);
    }

    if (fseek(file, (long)index, SEEK_SET) != 0)
    {
        fclose(file);
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    if (count == 0)
    {
        const long current = ftell(file);
        long end = -1;
        if (current < 0 || fseek(file, 0, SEEK_END) != 0)
        {
            fclose(file);
            mp_raise_OSError(errno == 0 ? MP_EIO : errno);
        }
        end = ftell(file);
        if (end < current || fseek(file, current, SEEK_SET) != 0)
        {
            fclose(file);
            mp_raise_OSError(errno == 0 ? MP_EIO : errno);
        }
        to_read = (size_t)(end - current);
    }
    else
    {
        to_read = (size_t)count;
    }

    if (to_read == 0)
    {
        fclose(file);
        return mp_obj_new_bytes((const byte *)"", 0);
    }

    buffer = (uint8_t *)m_malloc(to_read);
    if (buffer == NULL)
    {
        fclose(file);
        mp_raise_OSError(MP_ENOMEM);
    }

    bytes_read = fread(buffer, 1, to_read, file);
    read_error = ferror(file) != 0;
    fclose(file);

    if (read_error)
    {
        m_free(buffer);
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    mp_obj_t result = mp_obj_new_bytes(buffer, bytes_read);
    m_free(buffer);
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_read_obj, 1, 3, sd_mp_read);

mp_obj_t sd_mp_read_directory(mp_obj_t dirpath_obj)
{
    char path[SD_MP_PATH_MAX];
    DIR *dir = NULL;
    struct dirent *entry = NULL;
    mp_obj_t list = mp_obj_new_list(0, NULL);

    if (!sd_mp_normalize_path(mp_obj_str_get_str(dirpath_obj), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    dir = opendir(path);
    if (dir == NULL)
    {
        PRINT("Failed to open directory for reading.\n");
        mp_raise_OSError(MP_ENOENT);
    }

    while ((entry = readdir(dir)) != NULL)
    {
        char entry_path[SD_MP_PATH_MAX];
        struct stat st = {0};
        uint16_t fat_date = 0;
        uint16_t fat_time = 0;
        int written = 0;
        mp_obj_t entry_dict = mp_obj_new_dict(6);

        if (sd_mp_is_dot_entry(entry->d_name))
        {
            continue;
        }

        written = snprintf(entry_path, sizeof(entry_path), "%s/%s", path, entry->d_name);
        if (written <= 0 || (size_t)written >= sizeof(entry_path) || stat(entry_path, &st) != 0)
        {
            continue;
        }

        sd_mp_stat_to_fat_datetime(&st, &fat_date, &fat_time);
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_filename), mp_obj_new_str(entry->d_name, strlen(entry->d_name)));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_size), mp_obj_new_int_from_uint((uint32_t)(S_ISDIR(st.st_mode) ? 0 : st.st_size)));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_date), mp_obj_new_int(fat_date));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_time), mp_obj_new_int(fat_time));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_attributes), mp_obj_new_int(S_ISDIR(st.st_mode) ? FAT32_ATTR_DIRECTORY : FAT32_ATTR_ARCHIVE));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_is_directory), mp_obj_new_bool(S_ISDIR(st.st_mode)));
        mp_obj_list_append(list, entry_dict);
    }

    closedir(dir);
    return list;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_read_directory_obj, sd_mp_read_directory);

mp_obj_t sd_mp_readinto(mp_obj_t filepath_obj, mp_obj_t buffer_obj)
{
    char path[SD_MP_PATH_MAX];
    FILE *file = NULL;
    mp_buffer_info_t bufinfo;
    size_t bytes_read = 0;

    if (!sd_mp_normalize_path(mp_obj_str_get_str(filepath_obj), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    file = fopen(path, "rb");
    if (file == NULL)
    {
        PRINT("Failed to open file for reading.\n");
        mp_raise_OSError(MP_ENOENT);
    }

    mp_get_buffer_raise(buffer_obj, &bufinfo, MP_BUFFER_WRITE);
    bytes_read = fread(bufinfo.buf, 1, bufinfo.len, file);
    fclose(file);
    return mp_obj_new_int(bytes_read);
}
static MP_DEFINE_CONST_FUN_OBJ_2(sd_mp_readinto_obj, sd_mp_readinto);

mp_obj_t sd_mp_remove(mp_obj_t filepath_obj)
{
    char path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (!sd_mp_normalize_path(mp_obj_str_get_str(filepath_obj), path, sizeof(path)))
    {
        return mp_const_true;
    }

    if (stat(path, &st) != 0)
    {
        return mp_const_true;
    }

    return mp_obj_new_bool(sd_mp_remove_recursive_abs(path));
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_remove_obj, sd_mp_remove);

mp_obj_t sd_mp_rename(size_t n_args, const mp_obj_t *args)
{
    char old_path[SD_MP_PATH_MAX];
    char new_path[SD_MP_PATH_MAX];
    struct stat st = {0};

    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("rename requires 2 arguments: old_path, new_path"));
    }

    if (!sd_mp_normalize_path(mp_obj_str_get_str(args[0]), old_path, sizeof(old_path)) ||
        !sd_mp_normalize_path(mp_obj_str_get_str(args[1]), new_path, sizeof(new_path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    if (stat(old_path, &st) != 0)
    {
        PRINT("Failed to open file for renaming.\n");
        mp_raise_OSError(MP_ENOENT);
    }

    if (!sd_mp_ensure_parent_dirs(new_path))
    {
        mp_raise_OSError(MP_EIO);
    }

    return mp_obj_new_bool(rename(old_path, new_path) == 0);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_rename_obj, 2, 2, sd_mp_rename);

mp_obj_t sd_mp_write(size_t n_args, const mp_obj_t *args)
{
    char path[SD_MP_PATH_MAX];
    FILE *file = NULL;
    bool overwrite = false;
    mp_buffer_info_t bufinfo;
    size_t bytes_written = 0;

    if (n_args != 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("write requires 3 arguments: file_path, data, overwrite"));
    }

    if (!sd_mp_normalize_path(mp_obj_str_get_str(args[0]), path, sizeof(path)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid path"));
    }

    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_READ);
    overwrite = mp_obj_is_true(args[2]);

    if (!sd_mp_ensure_parent_dirs(path))
    {
        mp_raise_OSError(MP_EIO);
    }

    file = fopen(path, overwrite ? "wb" : "ab");
    if (file == NULL)
    {
        mp_raise_OSError(errno == 0 ? MP_EIO : errno);
    }

    bytes_written = fwrite(bufinfo.buf, 1, bufinfo.len, file);
    fclose(file);
    return mp_obj_new_bool(bytes_written == bufinfo.len);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_write_obj, 3, 3, sd_mp_write);

mp_obj_t sd_mp_unmount(void)
{
    if (!sdcard_is_mounted())
    {
        return mp_const_none;
    }

    sdcard_unmount();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_unmount_obj, sd_mp_unmount);

static const mp_rom_map_elem_t sd_mp_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sd_mp)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&sd_mp_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_copy), MP_ROM_PTR(&sd_mp_copy_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_file), MP_ROM_PTR(&sd_mp_create_file_obj)},
    {MP_ROM_QSTR(MP_QSTR_create_directory), MP_ROM_PTR(&sd_mp_create_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_exists), MP_ROM_PTR(&sd_mp_exists_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_close), MP_ROM_PTR(&sd_mp_file_close_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_copy), MP_ROM_PTR(&sd_mp_file_copy_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_move), MP_ROM_PTR(&sd_mp_file_move_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_open), MP_ROM_PTR(&sd_mp_file_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_read), MP_ROM_PTR(&sd_mp_file_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_readinto), MP_ROM_PTR(&sd_mp_file_readinto_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_seek), MP_ROM_PTR(&sd_mp_file_seek_obj)},
    {MP_ROM_QSTR(MP_QSTR_file_write), MP_ROM_PTR(&sd_mp_file_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_file_size), MP_ROM_PTR(&sd_mp_get_file_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_free_space), MP_ROM_PTR(&sd_mp_get_free_space_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_total_space), MP_ROM_PTR(&sd_mp_get_total_space_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_directory), MP_ROM_PTR(&sd_mp_is_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_initialized), MP_ROM_PTR(&sd_mp_is_initialized_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_file), MP_ROM_PTR(&sd_mp_is_file_obj)},
    {MP_ROM_QSTR(MP_QSTR_list_directory), MP_ROM_PTR(&sd_mp_list_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&sd_mp_mount_obj)},
    {MP_ROM_QSTR(MP_QSTR_move), MP_ROM_PTR(&sd_mp_move_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&sd_mp_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_readinto), MP_ROM_PTR(&sd_mp_readinto_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_directory), MP_ROM_PTR(&sd_mp_read_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_remove), MP_ROM_PTR(&sd_mp_remove_obj)},
    {MP_ROM_QSTR(MP_QSTR_rename), MP_ROM_PTR(&sd_mp_rename_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&sd_mp_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_unmount), MP_ROM_PTR(&sd_mp_unmount_obj)},

    {MP_ROM_QSTR(MP_QSTR_fat32_file), MP_ROM_PTR(&mp_fat32_file_type)},
    {MP_ROM_QSTR(MP_QSTR_FAT32_OK), MP_ROM_INT(FAT32_OK)},
};
static MP_DEFINE_CONST_DICT(sd_mp_module_globals, sd_mp_module_globals_table);

const mp_obj_module_t sd_mp_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&sd_mp_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_sd_mp, sd_mp_user_cmodule);