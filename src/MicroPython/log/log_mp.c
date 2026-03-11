/*
 * Picoware Log Native C Extension for MicroPython
 * Copyright © 2026 JBlanked
 *
 */

#include "log_mp.h"
#include "log_config.h"
#include LOG_STORAGE_INCLUDE

const mp_obj_type_t log_mp_type;

void log_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    log_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Log(mode=");
    switch (self->mode)
    {
    case LOG_MODE_REPL:
        mp_print_str(print, "REPL");
        break;
    case LOG_MODE_STORAGE:
        mp_print_str(print, "Storage");
        break;
    case LOG_MODE_ALL:
        mp_print_str(print, "All");
        break;
    }
    if (self->file_path)
    {
        mp_print_str(print, ", file_path=");
        mp_print_str(print, self->file_path);
    }
    mp_print_str(print, ")");
}

mp_obj_t log_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // Arguments: mode (optional, default=LOG_MODE_REPL), file_path (optional, required if mode includes storage), reset (optional)
    mp_arg_check_num(n_args, n_kw, 0, 3, false);
    log_mp_obj_t *self = mp_obj_malloc_with_finaliser(log_mp_obj_t, &log_mp_type);
    self->base.type = &log_mp_type;
    self->mode = n_args > 0 ? (LogMode)mp_obj_get_int(args[0]) : LOG_MODE_REPL;
    if ((self->mode == LOG_MODE_STORAGE || self->mode == LOG_MODE_ALL) && n_args > 1)
    {
        self->file_path = mp_obj_str_get_str(args[1]);
        if (n_args > 2)
        {
            if (mp_obj_is_true(args[2])) // reset
            {
                log_mp_reset(self);
            }
        }
    }
    else
    {
        self->file_path = NULL;
    }
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t log_mp_del(mp_obj_t self_in)
{
    log_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->mode = LOG_MODE_REPL;
    self->file_path = NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(log_mp_del_obj, log_mp_del);

void log_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    log_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_mode)
        {
            destination[0] = mp_obj_new_int((int)self->mode);
        }
        else if (attribute == MP_QSTR_file_path)
        {
            destination[0] = self->file_path ? mp_obj_new_str(self->file_path, strlen(self->file_path)) : mp_const_none;
        }
        else if (attribute == MP_QSTR_logs)
        {
            mp_obj_t log_list = mp_obj_new_list(0, NULL);
            if (self->file_path == NULL)
            {
                destination[0] = log_list; // return empty list if no file path is set
            }
            else
            {
                const size_t file_size = LOG_FILE_SIZE(self->file_path);
                char *buffer = (char *)m_malloc(file_size + 1);
                size_t bytes_read = LOG_STORAGE_READ(self->file_path, buffer, file_size);
                buffer[bytes_read] = '\0'; // Null-terminate the buffer
                // return as a list of log entries split by newlines
                char *line = strtok(buffer, "\n");
                while (line)
                {
                    mp_obj_list_append(log_list, mp_obj_new_str(line, strlen(line)));
                    line = strtok(NULL, "\n");
                }
                m_free(buffer);
                destination[0] = log_list;
            }
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&log_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_mode)
        {
            self->mode = (LogMode)mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_file_path)
        {
            self->file_path = mp_obj_str_get_str(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t log_mp_log(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, message, log_type (optional, default=LOG_TYPE_INFO)
    if (n_args < 2 || n_args > 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("log requires 2 or 3 arguments: self, message, [log_type]"));
    }
    log_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    const char *message = mp_obj_str_get_str(args[1]);
    LogType log_type = n_args == 3 ? (LogType)mp_obj_get_int(args[2]) : LOG_TYPE_NONE;
    // Prepend log type to message
    const char *log_type_str;
    switch (log_type)
    {
    case LOG_TYPE_INFO:
        log_type_str = "[INFO] ";
        break;
    case LOG_TYPE_WARN:
        log_type_str = "[WARN] ";
        break;
    case LOG_TYPE_ERROR:
        log_type_str = "[ERROR] ";
        break;
    case LOG_TYPE_DEBUG:
        log_type_str = "[DEBUG] ";
        break;
    default:
        log_type_str = "";
        break;
    };
    char *full_message = (char *)m_malloc(strlen(log_type_str) + strlen(message) + 2); // +2 for newline and null terminator
    snprintf(full_message, strlen(log_type_str) + strlen(message) + 2, "%s%s\n", log_type_str, message);
    bool success = true;
    if (self->mode == LOG_MODE_REPL || self->mode == LOG_MODE_ALL)
    {
        PRINT(full_message);
    }
    if (self->mode == LOG_MODE_STORAGE || self->mode == LOG_MODE_ALL)
    {
        success = LOG_STORAGE_WRITE(self->file_path, full_message, strlen(full_message), false);
    }
    m_free(full_message);
    return success ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(log_mp_log_obj, 2, 3, log_mp_log);

mp_obj_t log_mp_reset(mp_obj_t self_in)
{
    log_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->file_path == NULL)
    {
        return mp_const_true;
    }
    return LOG_STORAGE_WRITE(self->file_path, "", 0, true) ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(log_mp_reset_obj, log_mp_reset);

static const mp_rom_map_elem_t log_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_log), MP_ROM_PTR(&log_mp_log_obj)},
    {MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&log_mp_reset_obj)},

    // constants
    {MP_ROM_QSTR(MP_QSTR_LOG_MODE_REPL), MP_ROM_INT(LOG_MODE_REPL)},
    {MP_ROM_QSTR(MP_QSTR_LOG_MODE_STORAGE), MP_ROM_INT(LOG_MODE_STORAGE)},
    {MP_ROM_QSTR(MP_QSTR_LOG_TYPE_NONE), MP_ROM_INT(LOG_TYPE_NONE)},
    {MP_ROM_QSTR(MP_QSTR_LOG_MODE_ALL), MP_ROM_INT(LOG_MODE_ALL)},
    {MP_ROM_QSTR(MP_QSTR_LOG_TYPE_INFO), MP_ROM_INT(LOG_TYPE_INFO)},
    {MP_ROM_QSTR(MP_QSTR_LOG_TYPE_WARN), MP_ROM_INT(LOG_TYPE_WARN)},
    {MP_ROM_QSTR(MP_QSTR_LOG_TYPE_ERROR), MP_ROM_INT(LOG_TYPE_ERROR)},
    {MP_ROM_QSTR(MP_QSTR_LOG_TYPE_DEBUG), MP_ROM_INT(LOG_TYPE_DEBUG)},
};
static MP_DEFINE_CONST_DICT(log_mp_locals_dict, log_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    log_mp_type,
    MP_QSTR_Log,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, log_mp_print,
    make_new, log_mp_make_new,
    attr, log_mp_attr,
    locals_dict, &log_mp_locals_dict);

static const mp_rom_map_elem_t log_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_log)},
    {MP_ROM_QSTR(MP_QSTR_Log), MP_ROM_PTR(&log_mp_type)},
};
static MP_DEFINE_CONST_DICT(log_module_globals, log_module_globals_table);

// Define module
const mp_obj_module_t log_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&log_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_log, log_user_cmodule);