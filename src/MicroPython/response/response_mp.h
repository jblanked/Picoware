#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

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
    bool freed;
} response_mp_obj_t;

extern const mp_obj_type_t response_mp_type;

void response_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t response_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t response_mp_del(mp_obj_t self_in);
void response_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
