/*
 * Picoware SD Native C Extension for MicroPython
 * Copyright © 2025 JBlanked
 *
 */

#include "sd_mp.h"
#include "stdio.h"
#include <stdlib.h>
#include <string.h>

const mp_obj_type_t mp_fat32_file_type;

void mp_fat32_file_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    mp_fat32_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
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
    mp_fat32_file_obj_t *self = mp_obj_malloc_with_finaliser(mp_fat32_file_obj_t, &mp_fat32_file_type);
    self->base.type = &mp_fat32_file_type;
    // Initialize fat32_file_t structure
    memset(&self->file, 0, sizeof(fat32_file_t));
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t mp_fat32_file_del(mp_obj_t self_in)
{
    mp_fat32_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    fat32_close(&self->file);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mp_fat32_file_del_obj, mp_fat32_file_del);

// Attribute handler for fat32_file type
void mp_fat32_file_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    mp_fat32_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attribute
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
            // Store attribute
            mp_fat32_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
            self->file.position = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL; // indicate success
        }
    }
}

MP_DEFINE_CONST_OBJ_TYPE(
    mp_fat32_file_type,
    MP_QSTR_fat32_file, // name
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, mp_fat32_file_print,       // print function
    make_new, mp_fat32_file_make_new, // constructor
    attr, mp_fat32_file_attr          // attribute handler
);

// Function to initialize the SD card
mp_obj_t sd_mp_init(void)
{
    fat32_init();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_init_obj, sd_mp_init);

// Function to copy a file/directory to a new location
mp_obj_t sd_mp_copy(size_t n_args, const mp_obj_t *args)
{
    // Arguments: source_path, destination_path, bytes_per_chunk (optional)
    if (n_args < 2 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("copy requires 2 or 3 arguments: source_path, destination_path, [bytes_per_chunk]"));
    }
    const char *source_path = mp_obj_str_get_str(args[0]);
    const char *destination_path = mp_obj_str_get_str(args[1]);
    const size_t bytes_per_chunk = n_args == 3 ? mp_obj_get_int(args[2]) : 2048;
    fat32_file_t source_file;
    fat32_file_t destination_file;
    if (fat32_open(&source_file, source_path) != FAT32_OK)
    {
        PRINT("Failed to open source for copying.\n");
        mp_raise_OSError(MP_ENOENT);
    }
    if (fat32_open(&destination_file, destination_path) == FAT32_OK)
    {
        fat32_close(&source_file);
        fat32_close(&destination_file);
        PRINT("Destination already exists.\n");
        mp_raise_OSError(MP_EEXIST);
    }
    const bool is_directory = (source_file.attributes & FAT32_ATTR_DIRECTORY) != 0;
    if (!is_directory)
    {
        // Copy file
        uint8_t *buffer = (uint8_t *)m_malloc(bytes_per_chunk); // Allocate a buffer for copying
        size_t bytes_read, bytes_written;
        fat32_error_t err = fat32_create(&destination_file, destination_path);
        if (err != FAT32_OK)
        {
            fat32_close(&source_file);
            PRINT("Failed to create destination file: %s\n", fat32_error_string(err));
            mp_raise_OSError(MP_EIO);
        }
        if (fat32_open(&destination_file, destination_path) != FAT32_OK)
        {
            fat32_close(&source_file);
            PRINT("Failed to open destination file after creation.\n");
            mp_raise_OSError(MP_EIO);
        }
        while (fat32_read(&source_file, buffer, bytes_per_chunk, &bytes_read) == FAT32_OK && bytes_read > 0)
        {
            if (fat32_write(&destination_file, buffer, bytes_read, &bytes_written) != FAT32_OK || bytes_written != bytes_read)
            {
                fat32_close(&source_file);
                fat32_close(&destination_file);
                m_free(buffer);
                PRINT("Failed to write to destination file.\n");
                mp_raise_OSError(MP_EIO);
            }
        }
        m_free(buffer);
        fat32_close(&source_file);
        fat32_close(&destination_file);
    }
    else
    {
        // Copy directory
        fat32_error_t err = fat32_dir_create(&destination_file, destination_path);
        if (err != FAT32_OK)
        {
            fat32_close(&source_file);
            PRINT("Failed to create destination directory: %s\n", fat32_error_string(err));
            mp_raise_OSError(MP_EIO);
        }

        // Collect all directory entries before recursing
        fat32_entry_t entry;
        mp_obj_t entries = mp_obj_new_list(0, NULL);
        while (fat32_dir_read(&source_file, &entry) == FAT32_OK && entry.filename[0])
        {
            // Skip '.' and '..' entries to avoid infinite recursion
            if (strcmp(entry.filename, ".") == 0 || strcmp(entry.filename, "..") == 0)
            {
                continue;
            }
            mp_obj_t entry_tuple[2];
            entry_tuple[0] = mp_obj_new_str(entry.filename, strlen(entry.filename));
            entry_tuple[1] = mp_obj_new_int(entry.attr);
            mp_obj_list_append(entries, mp_obj_new_tuple(2, entry_tuple));
        }
        // Close directory handles before recursing
        fat32_close(&source_file);
        fat32_close(&destination_file);

        // Now process collected entries with no parent handles open
        size_t num_entries;
        mp_obj_t *entry_items;
        mp_obj_list_get(entries, &num_entries, &entry_items);
        char *source_entry_path = (char *)m_malloc(512);
        char *destination_entry_path = (char *)m_malloc(512);
        for (size_t i = 0; i < num_entries; i++)
        {
            mp_obj_t *tuple_items;
            size_t tuple_len;
            mp_obj_tuple_get(entry_items[i], &tuple_len, &tuple_items);
            const char *entry_name = mp_obj_str_get_str(tuple_items[0]);
            const int entry_attr = mp_obj_get_int(tuple_items[1]);
            snprintf(source_entry_path, 512, "%s/%s", source_path, entry_name);
            snprintf(destination_entry_path, 512, "%s/%s", destination_path, entry_name);
            mp_obj_t src_obj = mp_obj_new_str(source_entry_path, strlen(source_entry_path));
            mp_obj_t dst_obj = mp_obj_new_str(destination_entry_path, strlen(destination_entry_path));
            mp_obj_t chunk_obj = mp_obj_new_int(bytes_per_chunk);
            (void)entry_attr; // attr already filtered; recurse handles both files and dirs
            sd_mp_copy(3, (mp_obj_t[]){src_obj, dst_obj, chunk_obj});
        }
        m_free(source_entry_path);
        m_free(destination_entry_path);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_copy_obj, 2, 3, sd_mp_copy);

// Function to create a file on the SD card
mp_obj_t sd_mp_create_file(mp_obj_t filepath_obj)
{
    const char *filePath = mp_obj_str_get_str(filepath_obj);
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        fat32_error_t err = fat32_create(&file, filePath);
        if (err != FAT32_OK)
        {
            PRINT("Failed to create file: %s\n", fat32_error_string(err));
            mp_raise_OSError(MP_EIO);
        }
    }
    fat32_close(&file);
    return mp_obj_new_bool(true);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_create_file_obj, sd_mp_create_file);

// Function to create a directory on the SD card
mp_obj_t sd_mp_create_directory(mp_obj_t directory_path_obj)
{
    const char *dirPath = mp_obj_str_get_str(directory_path_obj);
    fat32_file_t dir;
    if (fat32_open(&dir, dirPath) == FAT32_OK)
    {
        // Directory already exists, check if it's actually a directory
        if (dir.attributes & FAT32_ATTR_DIRECTORY)
        {
            fat32_close(&dir);
            return mp_const_true;
        }
        else
        {
            fat32_close(&dir);
            PRINT("Path exists but is not a directory.\n");
            mp_raise_OSError(MP_EEXIST);
        }
    }
    // Directory doesn't exist, try to create it
    fat32_error_t err = fat32_dir_create(&dir, dirPath);
    if (err != FAT32_OK)
    {
        PRINT("Failed to create directory: %s\n", fat32_error_string(err));
        fat32_close(&dir);
        mp_raise_OSError(MP_EIO);
    }
    fat32_close(&dir);
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_create_directory_obj, sd_mp_create_directory);

// Function to check if a file or directory exists
mp_obj_t sd_mp_exists(mp_obj_t path_obj)
{
    const char *path = mp_obj_str_get_str(path_obj);
    fat32_file_t file;
    if (fat32_open(&file, path) == FAT32_OK)
    {
        fat32_close(&file);
        return mp_const_true;
    }
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_exists_obj, sd_mp_exists);

// Function to copy a file object to a new location
mp_obj_t sd_mp_file_copy(size_t n_args, const mp_obj_t *args)
{
    // Arguments: mp_file_obj, destination_path, bytes_per_chunk (optional)
    if (n_args < 2 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("file_copy requires 2 arguments: mp_file_obj, destination_path, [bytes_per_chunk]"));
    }
    mp_fat32_file_obj_t *source_file_obj = MP_OBJ_TO_PTR(args[0]);
    fat32_file_t *source_file = &source_file_obj->file;
    const char *destination_path = mp_obj_str_get_str(args[1]);
    fat32_file_t destination_file;
    if (fat32_open(&destination_file, destination_path) == FAT32_OK)
    {
        PRINT("Destination already exists.\n");
        mp_raise_OSError(MP_EEXIST);
    }
    const size_t bytes_per_chunk = n_args == 3 ? mp_obj_get_int(args[2]) : 2048;
    uint8_t *buffer = (uint8_t *)m_malloc(bytes_per_chunk); // Allocate a buffer for copying
    size_t bytes_read, bytes_written;
    fat32_error_t err = fat32_create(&destination_file, destination_path);
    if (err != FAT32_OK)
    {
        PRINT("Failed to create destination file: %s\n", fat32_error_string(err));
        mp_raise_OSError(MP_EIO);
    }
    if (fat32_open(&destination_file, destination_path) != FAT32_OK)
    {
        PRINT("Failed to open destination file after creation.\n");
        mp_raise_OSError(MP_EIO);
    }
    while (fat32_read(source_file, buffer, bytes_per_chunk, &bytes_read) == FAT32_OK && bytes_read > 0)
    {
        if (fat32_write(&destination_file, buffer, bytes_read, &bytes_written) != FAT32_OK || bytes_written != bytes_read)
        {
            PRINT("Failed to write to destination file.\n");
            mp_raise_OSError(MP_EIO);
        }
    }
    m_free(buffer);
    fat32_close(&destination_file);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_copy_obj, 2, 3, sd_mp_file_copy);

// Function to move a file object to a new location
mp_obj_t sd_mp_file_move(size_t n_args, const mp_obj_t *args)
{
    // Arguments: source_file_obj, destination_path, bytes_per_chunk (optional)
    if (n_args < 2 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("file_move requires 2 arguments: source_file_obj, destination_path, [bytes_per_chunk]"));
    }
    mp_fat32_file_obj_t *source_file_obj = MP_OBJ_TO_PTR(args[0]);
    fat32_file_t *source_file = &source_file_obj->file;
    const char *destination_path = mp_obj_str_get_str(args[1]);
    fat32_file_t destination_file;
    if (fat32_open(&destination_file, destination_path) == FAT32_OK)
    {
        PRINT("Destination already exists.\n");
        mp_raise_OSError(MP_EEXIST);
    }
    const size_t bytes_per_chunk = n_args == 3 ? mp_obj_get_int(args[2]) : 2048;
    uint8_t *buffer = (uint8_t *)m_malloc(bytes_per_chunk); // Allocate a buffer for copying
    size_t bytes_read, bytes_written;
    fat32_error_t err = fat32_create(&destination_file, destination_path);
    if (err != FAT32_OK)
    {
        PRINT("Failed to create destination file: %s\n", fat32_error_string(err));
        mp_raise_OSError(MP_EIO);
    }
    if (fat32_open(&destination_file, destination_path) != FAT32_OK)
    {
        PRINT("Failed to open destination file after creation.\n");
        mp_raise_OSError(MP_EIO);
    }
    while (fat32_read(source_file, buffer, bytes_per_chunk, &bytes_read) == FAT32_OK && bytes_read > 0)
    {
        if (fat32_write(&destination_file, buffer, bytes_read, &bytes_written) != FAT32_OK || bytes_written != bytes_read)
        {
            PRINT("Failed to write to destination file.\n");
            mp_raise_OSError(MP_EIO);
        }
    }
    m_free(buffer);
    fat32_close(&destination_file);
    // we should delete here but just close for now
    fat32_close(source_file);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_move_obj, 2, 3, sd_mp_file_move);

// Function to get the file size
mp_obj_t sd_mp_get_file_size(mp_obj_t filepath_obj)
{
    const char *filePath = mp_obj_str_get_str(filepath_obj);
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        PRINT("Failed to open file for reading.\n");
        return mp_obj_new_int(0);
    }
    const uint32_t size = fat32_size(&file);
    fat32_close(&file);
    return mp_obj_new_int_from_uint(size);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_get_file_size_obj, sd_mp_get_file_size);

// Function to close a fat32_file_t object
mp_obj_t sd_mp_file_close(mp_obj_t file_obj)
{
    mp_fat32_file_obj_t *file = MP_OBJ_TO_PTR(file_obj);
    fat32_close(&file->file);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_file_close_obj, sd_mp_file_close);

// Function to open a file and return a fat32_file_t object
mp_obj_t sd_mp_file_open(mp_obj_t filepath_obj)
{
    const char *filePath = mp_obj_str_get_str(filepath_obj);
    mp_fat32_file_obj_t *file_obj = mp_fat32_file_make_new(&mp_fat32_file_type, 0, 0, NULL);
    if (fat32_open(&file_obj->file, filePath) != FAT32_OK)
    {
        if (fat32_create(&file_obj->file, filePath) != FAT32_OK)
        {
            PRINT("Failed to open and create file.\n");
            mp_raise_OSError(MP_EIO);
        }
    }
    return MP_OBJ_FROM_PTR(file_obj);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_file_open_obj, sd_mp_file_open);

// Function to read within a file object
mp_obj_t sd_mp_file_read(size_t n_args, const mp_obj_t *args)
{
    // Arguments: mp_file_obj, index (optional), count (optional)
    if (n_args < 1 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("read requires at least 1 argument: mp_file_obj, [index], [count]"));
    }
    uint32_t index = 0;
    uint32_t count = 0;
    if (n_args >= 2)
    {
        index = mp_obj_get_int(args[1]);
    }
    if (n_args == 3)
    {
        count = mp_obj_get_int(args[2]);
    }
    mp_fat32_file_obj_t *file_obj = MP_OBJ_TO_PTR(args[0]);
    fat32_file_t *file = &file_obj->file;
    if (index > 0 && file->position != index)
    {
        if (fat32_seek(file, index) != FAT32_OK)
        {
            PRINT("Failed to seek to index %lu.\n", index);
            mp_raise_OSError(MP_EIO);
        }
    }
    const uint32_t size_of_buffer = count != 0 ? count : fat32_size(file);
    uint8_t buffer[size_of_buffer];
    size_t bytes_read;
    if (fat32_read(file, buffer, size_of_buffer, &bytes_read) != FAT32_OK)
    {
        mp_raise_OSError(MP_EIO);
    }
    return mp_obj_new_bytes(buffer, bytes_read);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_read_obj, 1, 3, sd_mp_file_read);

mp_obj_t sd_mp_file_readinto(size_t n_args, const mp_obj_t *args)
{
    // Arguments: mp_file_obj, buffer
    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("readinto requires 2 arguments: mp_file_obj, buffer"));
    }
    mp_fat32_file_obj_t *file_obj = MP_OBJ_TO_PTR(args[0]);
    fat32_file_t *file = &file_obj->file;
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_WRITE);
    size_t bytes_read;
    if (fat32_read(file, bufinfo.buf, bufinfo.len, &bytes_read) != FAT32_OK)
    {
        mp_raise_OSError(MP_EIO);
    }
    return mp_obj_new_int(bytes_read);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_readinto_obj, 2, 2, sd_mp_file_readinto);

// Function to seek within a file object
mp_obj_t sd_mp_file_seek(size_t n_args, const mp_obj_t *args)
{
    // Arguments: mp_file_obj,position
    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("seek requires 2 arguments: mp_file_obj,position"));
    }
    // Arguments: mp_file_obj, position
    mp_fat32_file_obj_t *file_obj = MP_OBJ_TO_PTR(args[0]);
    fat32_file_t *file = &file_obj->file;
    uint32_t position = mp_obj_get_int(args[1]);
    if (fat32_seek(file, position) != FAT32_OK)
    {
        PRINT("Failed to seek in file.\n");
        mp_raise_OSError(MP_EIO);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_seek_obj, 2, 2, sd_mp_file_seek);

// Function to write to a file object
mp_obj_t sd_mp_file_write(size_t n_args, const mp_obj_t *args)
{
    // Arguments: mp_file_obj, data
    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("write requires 2 arguments: mp_file_obj, data"));
    }
    mp_fat32_file_obj_t *file_obj = MP_OBJ_TO_PTR(args[0]);
    fat32_file_t *file = &file_obj->file;
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_READ);
    size_t bytes_written;
    if (fat32_write(file, bufinfo.buf, bufinfo.len, &bytes_written) != FAT32_OK || bytes_written != bufinfo.len)
    {
        PRINT("Failed to write to file.\n");
        mp_raise_OSError(MP_EIO);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_file_write_obj, 2, 2, sd_mp_file_write);

// Function to get the free space of the SD card
mp_obj_t sd_mp_get_free_space(void)
{
    uint64_t free_space = 0;
    if (fat32_get_free_space(&free_space) != FAT32_OK)
    {
        PRINT("Failed to get free space.\n");
        return mp_obj_new_int(0);
    }
    return mp_obj_new_int_from_ull(free_space);
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_get_free_space_obj, sd_mp_get_free_space);

// Function to get the total space of the SD card
mp_obj_t sd_mp_get_total_space(void)
{
    uint64_t total_space = 0;
    if (fat32_get_total_space(&total_space) != FAT32_OK)
    {
        PRINT("Failed to get total space.\n");
        return mp_obj_new_int(0);
    }
    return mp_obj_new_int_from_ull(total_space);
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_get_total_space_obj, sd_mp_get_total_space);

// Function to check if SD card is initialized
mp_obj_t sd_mp_is_initialized(void)
{
    return mp_obj_new_bool(fat32_is_ready());
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_is_initialized_obj, sd_mp_is_initialized);

// Function to check if path is a directory
mp_obj_t sd_mp_is_directory(mp_obj_t path_obj)
{
    const char *dirPath = mp_obj_str_get_str(path_obj);
    fat32_file_t dir;
    if (fat32_open(&dir, dirPath) == FAT32_OK)
    {
        // Directory already exists, check if it's actually a directory
        mp_obj_t result = (dir.attributes & FAT32_ATTR_DIRECTORY) ? mp_const_true : mp_const_false;
        fat32_close(&dir);
        return result;
    }
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_is_directory_obj, sd_mp_is_directory);

// Function to check if path is a file
mp_obj_t sd_mp_is_file(mp_obj_t path_obj)
{
    const char *path = mp_obj_str_get_str(path_obj);
    fat32_file_t file;
    if (fat32_open(&file, path) == FAT32_OK)
    {
        // File exists, check if it's actually a file
        mp_obj_t result = (file.attributes & FAT32_ATTR_DIRECTORY) ? mp_const_false : mp_const_true;
        fat32_close(&file);
        return result;
    }
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_is_file_obj, sd_mp_is_file);

// Function to mount the SD card
mp_obj_t sd_mp_mount(void)
{
    if (fat32_is_mounted())
    {
        return mp_const_true;
    }
    fat32_error_t err = fat32_mount();
    if (err != FAT32_OK)
    {
        PRINT("Failed to mount SD card: %s\n", fat32_error_string(err));
        mp_raise_OSError(MP_EIO);
    }
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_mount_obj, sd_mp_mount);

// Function to move a file/directory to a new location
mp_obj_t sd_mp_move(size_t n_args, const mp_obj_t *args)
{
    // Arguments: source_path, destination_path
    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("move requires 2 arguments: source_path, destination_path"));
    }
    const char *source_path = mp_obj_str_get_str(args[0]);
    const char *destination_path = mp_obj_str_get_str(args[1]);
    fat32_file_t source_file;
    if (fat32_open(&source_file, source_path) != FAT32_OK)
    {
        PRINT("Failed to open source for moving.\n");
        mp_raise_OSError(MP_ENOENT);
    }
    if (fat32_open(&source_file, destination_path) == FAT32_OK)
    {
        fat32_close(&source_file);
        PRINT("Destination already exists.\n");
        mp_raise_OSError(MP_EEXIST);
    }
    const bool is_directory = (source_file.attributes & FAT32_ATTR_DIRECTORY) != 0;
    if (!is_directory)
    {
        // Move file
        if (fat32_rename(source_path, destination_path) != FAT32_OK)
        {
            fat32_close(&source_file);
            PRINT("Failed to move file.\n");
            mp_raise_OSError(MP_EIO);
        }
    }
    else
    {
        // Move directory
        fat32_error_t err = fat32_dir_create(&source_file, destination_path);
        if (err != FAT32_OK)
        {
            fat32_close(&source_file);
            PRINT("Failed to create destination directory: %s\n", fat32_error_string(err));
            mp_raise_OSError(MP_EIO);
        }

        // Loop through all directory entries
        fat32_entry_t entry;
        char source_entry_path[512];
        char destination_entry_path[512];
        while (fat32_dir_read(&source_file, &entry) == FAT32_OK && entry.filename[0])
        {
            // Skip '.' and '..' entries to avoid infinite recursion
            if (strcmp(entry.filename, ".") == 0 || strcmp(entry.filename, "..") == 0)
            {
                continue;
            }
            snprintf(source_entry_path, sizeof(source_entry_path), "%s/%s", source_path, entry.filename);
            snprintf(destination_entry_path, sizeof(destination_entry_path), "%s/%s", destination_path, entry.filename);
            if (entry.attr & FAT32_ATTR_DIRECTORY)
            {
                // Recursively move subdirectory
                mp_obj_t src_obj = mp_obj_new_str(source_entry_path, strlen(source_entry_path));
                mp_obj_t dst_obj = mp_obj_new_str(destination_entry_path, strlen(destination_entry_path));
                sd_mp_move(2, (mp_obj_t[]){src_obj, dst_obj});
            }
            else
            {
                // Move file
                mp_obj_t src_obj = mp_obj_new_str(source_entry_path, strlen(source_entry_path));
                mp_obj_t dst_obj = mp_obj_new_str(destination_entry_path, strlen(destination_entry_path));
                sd_mp_move(2, (mp_obj_t[]){src_obj, dst_obj});
            }
            // Clear entry paths for next iteration
            source_entry_path[0] = '\0';
            destination_entry_path[0] = '\0';
        }
    }
    fat32_close(&source_file);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_move_obj, 2, 2, sd_mp_move);

// Function to read a file
mp_obj_t sd_mp_read(size_t n_args, const mp_obj_t *args)
{
    // Arguments: File path, index (optional), count (optional)
    if (n_args < 1 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("read requires at least 1 argument: file_path, [index], [count]"));
    }
    uint32_t index = 0;
    uint32_t count = 0;
    if (n_args == 2)
    {
        index = mp_obj_get_int(args[1]);
    }
    if (n_args == 3)
    {
        count = mp_obj_get_int(args[2]);
    }
    const char *filePath = mp_obj_str_get_str(args[0]);
    fat32_file_t file;
    fat32_error_t err = fat32_open(&file, filePath);
    if (err != FAT32_OK)
    {
        mp_raise_OSError(MP_ENOENT);
    }
    if (index > 0)
    {
        if (fat32_seek(&file, index) != FAT32_OK)
        {
            fat32_close(&file);
            PRINT("Failed to seek to index %lu.\n", index);
            mp_raise_OSError(MP_EIO);
        }
    }
    const uint32_t size_of_buffer = count != 0 ? count : fat32_size(&file);
    uint8_t buffer[size_of_buffer];
    size_t bytes_read;
    const bool status = fat32_read(&file, buffer, size_of_buffer, &bytes_read) == FAT32_OK;
    fat32_close(&file);
    buffer[bytes_read] = '\0'; // Null-terminate the buffer
    mp_obj_t result = status ? mp_obj_new_bytes(buffer, bytes_read) : mp_const_none;
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_read_obj, 1, 3, sd_mp_read);

mp_obj_t sd_mp_read_directory(mp_obj_t dirpath_obj)
{
    const char *dirPath = mp_obj_str_get_str(dirpath_obj);
    fat32_file_t dir;
    fat32_error_t err = fat32_open(&dir, dirPath);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open directory for reading: %s\n", fat32_error_string(err));
        mp_raise_OSError(MP_ENOENT);
    }
    mp_obj_t list = mp_obj_new_list(0, NULL);
    fat32_entry_t entry;

    // Loop through all directory entries
    while (fat32_dir_read(&dir, &entry) == FAT32_OK && entry.filename[0])
    {
        mp_obj_t entry_dict = mp_obj_new_dict(5);
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_filename), mp_obj_new_str(entry.filename, strlen(entry.filename)));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_size), mp_obj_new_int_from_uint(entry.size));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_date), mp_obj_new_int(entry.date));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_time), mp_obj_new_int(entry.time));
        mp_obj_dict_store(entry_dict, MP_OBJ_NEW_QSTR(MP_QSTR_attributes), mp_obj_new_int(entry.attr));
        mp_obj_list_append(list, entry_dict);
    }

    fat32_close(&dir);
    return list;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_read_directory_obj, sd_mp_read_directory);

mp_obj_t sd_mp_readinto(mp_obj_t filepath_obj, mp_obj_t buffer_obj)
{
    const char *filePath = mp_obj_str_get_str(filepath_obj);
    fat32_file_t file;
    fat32_error_t err = fat32_open(&file, filePath);
    if (err != FAT32_OK)
    {
        PRINT("Failed to open file for reading: %s\n", fat32_error_string(err));
        mp_raise_OSError(MP_ENOENT);
    }
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(buffer_obj, &bufinfo, MP_BUFFER_WRITE);
    size_t bytes_read;
    const bool status = fat32_read(&file, bufinfo.buf, bufinfo.len, &bytes_read) == FAT32_OK;
    fat32_close(&file);
    return status ? mp_obj_new_int(bytes_read) : mp_obj_new_int(0);
}
static MP_DEFINE_CONST_FUN_OBJ_2(sd_mp_readinto_obj, sd_mp_readinto);

// Function to remove a file or directory
mp_obj_t sd_mp_remove(mp_obj_t filepath_obj)
{
    const char *filePath = mp_obj_str_get_str(filepath_obj);
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        return mp_const_true;
    }
    if ((file.attributes & FAT32_ATTR_DIRECTORY) != 0)
    {
        // Remove directory recursively
        fat32_entry_t entry;
        char *entry_path = (char *)m_malloc(512);
        while (fat32_dir_read(&file, &entry) == FAT32_OK && entry.filename[0])
        {
            // Skip '.' and '..' entries to avoid infinite recursion
            if (strcmp(entry.filename, ".") == 0 || strcmp(entry.filename, "..") == 0)
            {
                continue;
            }
            snprintf(entry_path, 512, "%s/%s", filePath, entry.filename);
            mp_obj_t entry_obj = mp_obj_new_str(entry_path, strlen(entry_path));
            sd_mp_remove(entry_obj); // Recursively remove entry
            entry_path[0] = '\0';    // Clear entry path for next iteration
        }
        m_free(entry_path);
    }
    fat32_close(&file);
    return mp_obj_new_bool(fat32_delete(filePath) == FAT32_OK);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sd_mp_remove_obj, sd_mp_remove);

// Function to rename a file
mp_obj_t sd_mp_rename(size_t n_args, const mp_obj_t *args)
{
    // Arguments: old_path, new_path
    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("rename requires 2 arguments: old_path, new_path"));
    }
    const char *oldPath = mp_obj_str_get_str(args[0]);
    const char *newPath = mp_obj_str_get_str(args[1]);
    fat32_file_t file;
    if (fat32_open(&file, oldPath) != FAT32_OK)
    {
        PRINT("Failed to open file for renaming.\n");
        mp_raise_OSError(MP_ENOENT);
    }
    const bool status = fat32_rename(oldPath, newPath) == FAT32_OK;
    fat32_close(&file);
    return mp_obj_new_bool(status);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_rename_obj, 2, 2, sd_mp_rename);

// Function to write to a file
mp_obj_t sd_mp_write(size_t n_args, const mp_obj_t *args)
{
    // Arguments: file_path, data, overwrite
    if (n_args != 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("write requires 3 arguments: file_path, data, overwrite"));
    }
    const char *filePath = mp_obj_str_get_str(args[0]);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[1], &bufinfo, MP_BUFFER_READ);
    const bool overwrite = mp_obj_is_true(args[2]);
    fat32_file_t file;
    if (fat32_open(&file, filePath) != FAT32_OK)
    {
        if (fat32_create(&file, filePath) != FAT32_OK)
        {
            PRINT("Failed to open and create file.\n");
            mp_raise_OSError(MP_EIO);
        }
    }
    else
    {
        if (overwrite)
        {
            if (fat32_delete(filePath) != FAT32_OK)
            {
                PRINT("Failed to delete existing file.\n");
                mp_raise_OSError(MP_EIO);
            }
            if (fat32_create(&file, filePath) != FAT32_OK)
            {
                PRINT("Failed to create new file.\n");
                mp_raise_OSError(MP_EIO);
            }
            if (fat32_open(&file, filePath) != FAT32_OK)
            {
                PRINT("Failed to open new file.\n");
                mp_raise_OSError(MP_ENOENT);
            }
        }
    }
    size_t bytes_written;
    const bool status = fat32_write(&file, bufinfo.buf, bufinfo.len, &bytes_written) == FAT32_OK;
    fat32_close(&file);
    return mp_obj_new_bool(status && bytes_written == bufinfo.len);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sd_mp_write_obj, 3, 3, sd_mp_write);

// Function to unmount the SD card
mp_obj_t sd_mp_unmount(void)
{
    if (!fat32_is_mounted())
    {
        return mp_const_none;
    }
    fat32_unmount();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(sd_mp_unmount_obj, sd_mp_unmount);

// Define module globals
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
    {MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&sd_mp_mount_obj)},
    {MP_ROM_QSTR(MP_QSTR_move), MP_ROM_PTR(&sd_mp_move_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&sd_mp_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_readinto), MP_ROM_PTR(&sd_mp_readinto_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_directory), MP_ROM_PTR(&sd_mp_read_directory_obj)},
    {MP_ROM_QSTR(MP_QSTR_remove), MP_ROM_PTR(&sd_mp_remove_obj)},
    {MP_ROM_QSTR(MP_QSTR_rename), MP_ROM_PTR(&sd_mp_rename_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&sd_mp_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_unmount), MP_ROM_PTR(&sd_mp_unmount_obj)},

    // Expose fat32_file type
    {MP_ROM_QSTR(MP_QSTR_fat32_file), MP_ROM_PTR(&mp_fat32_file_type)},

    // constants
    {MP_ROM_QSTR(MP_QSTR_FAT32_OK), MP_ROM_INT(FAT32_OK)},
};
static MP_DEFINE_CONST_DICT(sd_mp_module_globals, sd_mp_module_globals_table);

// Define module
const mp_obj_module_t sd_mp_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&sd_mp_module_globals,
};

// Register the module to make it available in Python
MP_REGISTER_MODULE(MP_QSTR_sd_mp, sd_mp_user_cmodule);