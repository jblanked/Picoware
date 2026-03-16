/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

    typedef enum
    {
        LOG_MODE_REPL,    // Log to REPL only
        LOG_MODE_STORAGE, // Log to storage only
        LOG_MODE_ALL      // Log to both REPL and storage
    } LogMode;

    typedef enum
    {
        LOG_TYPE_NONE = -1,
        LOG_TYPE_INFO = 0,
        LOG_TYPE_WARN = 1,
        LOG_TYPE_ERROR = 2,
        LOG_TYPE_DEBUG = 3
    } LogType;

    typedef struct
    {
        mp_obj_base_t base;
        LogMode mode;
        const char *file_path; // Optional file path for storage logging
    } log_mp_obj_t;

    extern const mp_obj_type_t log_mp_type;

    void log_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the Log object
    mp_obj_t log_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the Log object
    mp_obj_t log_mp_del(mp_obj_t self_in);                                                                 // destructor for the Log object
    void log_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the Log object

    mp_obj_t log_mp_log(size_t n_args, const mp_obj_t *args); // method to log a message with a specified type and mode
    mp_obj_t log_mp_reset(mp_obj_t self_in);                  // method to reset logs (erasing storage if applicable)

    mp_obj_t log_mp_set_mode(mp_obj_t self_in, mp_obj_t mode_obj);           // Method to set the logging mode (REPL, Storage, or All)
    mp_obj_t log_mp_set_file_path(mp_obj_t self_in, mp_obj_t file_path_obj); // Method to set the file path for storage logging

#ifdef __cplusplus
}
#endif