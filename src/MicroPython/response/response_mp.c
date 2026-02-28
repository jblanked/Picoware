#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "stdio.h"
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

typedef struct
{
    mp_obj_base_t base;
    uint8_t *content;       // The content buffer
    size_t content_len;     // Length of content (for binary data)
    char *encoding;         // Encoding type (owned copy)
    mp_obj_dict_t *headers; // Headers dictionary
    char *reason;           // Reason phrase (owned copy)
    int status_code;        // HTTP status code
    char *text;             // Text representation of content (owned copy)
} response_mp_obj_t;

const mp_obj_type_t response_mp_type;

STATIC void response_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Response(");
    mp_print_str(print, "content=");
    if (self->content && self->content_len > 0)
    {
        mp_obj_print_helper(print, mp_obj_new_bytes(self->content, self->content_len), PRINT_REPR);
    }
    else
    {
        mp_print_str(print, "b''");
    }
    mp_print_str(print, ", encoding=");
    if (self->encoding)
    {
        mp_obj_print_helper(print, mp_obj_new_str(self->encoding, strlen(self->encoding)), PRINT_REPR);
    }
    else
    {
        mp_print_str(print, "'utf-8'");
    }
    mp_print_str(print, ", status_code=");
    mp_obj_print_helper(print, mp_obj_new_int(self->status_code), PRINT_REPR);
    mp_print_str(print, ", reason=");
    if (self->reason)
    {
        mp_obj_print_helper(print, mp_obj_new_str(self->reason, strlen(self->reason)), PRINT_REPR);
    }
    else
    {
        mp_print_str(print, "''");
    }
    mp_print_str(print, ", text=");
    if (self->text)
    {
        mp_obj_print_helper(print, mp_obj_new_str(self->text, strlen(self->text)), PRINT_REPR);
    }
    else
    {
        mp_print_str(print, "''");
    }
    mp_print_str(print, ", headers=");
    mp_obj_print_helper(print, MP_OBJ_FROM_PTR(self->headers), PRINT_REPR);
    mp_print_str(print, ")");
}

STATIC mp_obj_t response_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    (void)n_args;
    (void)n_kw;
    (void)args;
    (void)type;
    response_mp_obj_t *self = mp_obj_malloc_with_finaliser(response_mp_obj_t, &response_mp_type);
    self->base.type = &response_mp_type;
    self->content = NULL;
    self->content_len = 0;
    self->encoding = NULL;
    self->headers = mp_obj_new_dict(0);
    self->status_code = -1;
    self->reason = NULL;
    self->text = NULL;
    return MP_OBJ_FROM_PTR(self);
}

// Manual cleanup method
STATIC mp_obj_t response_mp_del(mp_obj_t self_in)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->content)
    {
        m_free(self->content);
        self->content = NULL;
    }
    if (self->encoding)
    {
        m_free(self->encoding);
        self->encoding = NULL;
    }
    if (self->reason)
    {
        m_free(self->reason);
        self->reason = NULL;
    }
    if (self->text)
    {
        m_free(self->text);
        self->text = NULL;
    }
    self->content_len = 0;
    if (self->headers)
    {
        m_del(mp_obj_dict_t, self->headers, 1);
        self->headers = NULL;
    }
    self->status_code = -1;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(response_mp_del_obj, response_mp_del);

STATIC void response_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_content)
        {
            if (self->content && self->content_len > 0)
            {
                destination[0] = mp_obj_new_bytes(self->content, self->content_len);
            }
            else
            {
                destination[0] = mp_obj_new_bytes((const byte *)"", 0);
            }
        }
        else if (attribute == MP_QSTR_encoding)
        {
            if (self->encoding)
            {
                destination[0] = mp_obj_new_str(self->encoding, strlen(self->encoding));
            }
            else
            {
                destination[0] = mp_obj_new_str("utf-8", 5);
            }
        }
        else if (attribute == MP_QSTR_headers)
        {
            destination[0] = MP_OBJ_FROM_PTR(self->headers);
        }
        else if (attribute == MP_QSTR_reason)
        {
            if (self->reason)
            {
                destination[0] = mp_obj_new_str(self->reason, strlen(self->reason));
            }
            else
            {
                destination[0] = mp_obj_new_str("", 0);
            }
        }
        else if (attribute == MP_QSTR_status_code)
        {
            destination[0] = mp_obj_new_int(self->status_code);
        }
        else if (attribute == MP_QSTR_text)
        {
            if (self->text)
            {
                destination[0] = mp_obj_new_str(self->text, strlen(self->text));
            }
            else
            {
                destination[0] = mp_obj_new_str("", 0);
            }
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&response_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_content)
        {
            mp_buffer_info_t bufinfo;
            mp_get_buffer_raise(destination[1], &bufinfo, MP_BUFFER_READ);
            if (self->content)
            {
                m_free(self->content);
            }
            self->content = m_malloc(bufinfo.len + 1);
            memcpy(self->content, bufinfo.buf, bufinfo.len);
            self->content[bufinfo.len] = '\0'; // Null-terminate for safety
            self->content_len = bufinfo.len;   // Store actual length for binary data
        }
        else if (attribute == MP_QSTR_encoding)
        {
            size_t len;
            const char *str_data = mp_obj_str_get_data(destination[1], &len);
            if (self->encoding)
            {
                m_free(self->encoding);
            }
            self->encoding = m_malloc(len + 1);
            memcpy(self->encoding, str_data, len);
            self->encoding[len] = '\0';
        }
        else if (attribute == MP_QSTR_headers)
        {
            self->headers = MP_OBJ_TO_PTR(destination[1]);
        }
        else if (attribute == MP_QSTR_status_code)
        {
            self->status_code = mp_obj_get_int(destination[1]);
        }
        else if (attribute == MP_QSTR_reason)
        {
            size_t len;
            const char *str_data = mp_obj_str_get_data(destination[1], &len);
            if (self->reason)
            {
                m_free(self->reason);
            }
            self->reason = m_malloc(len + 1);
            memcpy(self->reason, str_data, len);
            self->reason[len] = '\0';
        }
        else if (attribute == MP_QSTR_text)
        {
            size_t len;
            const char *str_data = mp_obj_str_get_data(destination[1], &len);
            if (self->text)
            {
                m_free(self->text);
            }
            self->text = m_malloc(len + 1);
            memcpy(self->text, str_data, len);
            self->text[len] = '\0';
        }
        // Mark destination[0] to indicate successful store
        destination[0] = MP_OBJ_NULL;
    }
}

MP_DEFINE_CONST_OBJ_TYPE(
    response_mp_type,
    MP_QSTR_Response, // Name of the type in Python
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, response_mp_print,       // Print function
    make_new, response_mp_make_new, // constructor
    attr, response_mp_attr          // attribute handler
);
// Define module globals
STATIC const mp_rom_map_elem_t response_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_response)},
    {MP_ROM_QSTR(MP_QSTR_Response), MP_ROM_PTR(&response_mp_type)},
};
STATIC MP_DEFINE_CONST_DICT(response_module_globals, response_module_globals_table);

// Define module
const mp_obj_module_t response_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&response_module_globals,
};
// Register the module to make it available in Python
MP_REGISTER_MODULE(MP_QSTR_response, response_user_cmodule);