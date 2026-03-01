#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "py/mperrno.h"
#include "fat32.h"

typedef struct
{
    mp_obj_base_t base;
    fat32_file_t file;
} mp_fat32_file_obj_t;

extern const mp_obj_type_t mp_fat32_file_type;

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

void mp_fat32_file_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t mp_fat32_file_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t mp_fat32_file_del(mp_obj_t self_in);
void mp_fat32_file_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

mp_obj_t sd_mp_init(void);
mp_obj_t sd_mp_create_file(mp_obj_t filepath_obj);
mp_obj_t sd_mp_create_directory(mp_obj_t directory_path_obj);
mp_obj_t sd_mp_exists(mp_obj_t path_obj);
mp_obj_t sd_mp_get_file_size(mp_obj_t filepath_obj);
mp_obj_t sd_mp_file_close(mp_obj_t file_obj);
mp_obj_t sd_mp_file_open(mp_obj_t filepath_obj);
mp_obj_t sd_mp_file_read(size_t n_args, const mp_obj_t *args);
mp_obj_t sd_mp_file_readinto(size_t n_args, const mp_obj_t *args);
mp_obj_t sd_mp_file_seek(size_t n_args, const mp_obj_t *args);
mp_obj_t sd_mp_file_write(size_t n_args, const mp_obj_t *args);
mp_obj_t sd_mp_get_free_space(void);
mp_obj_t sd_mp_get_total_space(void);
mp_obj_t sd_mp_is_initialized(void);
mp_obj_t sd_mp_is_directory(mp_obj_t path_obj);
mp_obj_t sd_mp_is_file(mp_obj_t path_obj);
mp_obj_t sd_mp_mount(void);
mp_obj_t sd_mp_read(size_t n_args, const mp_obj_t *args);
mp_obj_t sd_mp_read_directory(mp_obj_t dirpath_obj);
mp_obj_t sd_mp_readinto(mp_obj_t filepath_obj, mp_obj_t buffer_obj);
mp_obj_t sd_mp_remove(mp_obj_t filepath_obj);
mp_obj_t sd_mp_rename(size_t n_args, const mp_obj_t *args);
mp_obj_t sd_mp_write(size_t n_args, const mp_obj_t *args);
mp_obj_t sd_mp_unmount(void);