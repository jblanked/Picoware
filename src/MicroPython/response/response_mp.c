#include "response_mp.h"

const mp_obj_type_t response_mp_type;

void response_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
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

mp_obj_t response_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
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
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t response_mp_del(mp_obj_t self_in)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }
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
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(response_mp_del_obj, response_mp_del);

void response_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        switch (attribute)
        {
        case MP_QSTR_content:
            destination[0] = self->content && self->content_len > 0 ? mp_obj_new_bytes(self->content, self->content_len) : mp_obj_new_bytes((const byte *)"", 0);
            break;
        case MP_QSTR_encoding:
            destination[0] = self->encoding ? mp_obj_new_str(self->encoding, strlen(self->encoding)) : mp_obj_new_str("utf-8", 5);
            break;
        case MP_QSTR_headers:
            destination[0] = MP_OBJ_FROM_PTR(self->headers);
            break;
        case MP_QSTR_reason:
            destination[0] = self->reason ? mp_obj_new_str(self->reason, strlen(self->reason)) : mp_obj_new_str("", 0);
            break;
        case MP_QSTR_status_code:
            destination[0] = mp_obj_new_int(self->status_code);
            break;
        case MP_QSTR_text:
            destination[0] = self->text ? mp_obj_new_str(self->text, strlen(self->text)) : mp_obj_new_str("", 0);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&response_mp_del_obj);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL; // not found here; fall through to locals_dict
            break;
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        switch (attribute)
        {
        case MP_QSTR_content:
            response_mp_set_content(self_in, destination[1]);
            break;
        case MP_QSTR_encoding:
            response_mp_set_encoding(self_in, destination[1]);
            break;
        case MP_QSTR_headers:
            response_mp_set_headers(self_in, destination[1]);
            break;
        case MP_QSTR_reason:
            response_mp_set_reason(self_in, destination[1]);
            break;
        case MP_QSTR_status_code:
            response_mp_set_status_code(self_in, destination[1]);
            break;
        case MP_QSTR_text:
            response_mp_set_text(self_in, destination[1]);
            break;
        default:
            return; // Fail
        };
        // Mark destination[0] to indicate successful store
        destination[0] = MP_OBJ_NULL;
    }
}

mp_obj_t response_mp_set_content(mp_obj_t self_in, mp_obj_t content_obj)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(content_obj, &bufinfo, MP_BUFFER_READ);
    if (self->content)
    {
        m_free(self->content);
    }
    self->content = m_malloc(bufinfo.len + 1);
    memcpy(self->content, bufinfo.buf, bufinfo.len);
    self->content[bufinfo.len] = '\0'; // Null-terminate for safety
    self->content_len = bufinfo.len;   // Store actual length for binary data
    return mp_obj_new_int(self->content_len);
}
static MP_DEFINE_CONST_FUN_OBJ_2(response_mp_set_content_obj, response_mp_set_content);

mp_obj_t response_mp_set_encoding(mp_obj_t self_in, mp_obj_t encoding_obj)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    size_t len;
    const char *str_data = mp_obj_str_get_data(encoding_obj, &len);
    if (self->encoding)
    {
        m_free(self->encoding);
    }
    self->encoding = m_malloc(len + 1);
    memcpy(self->encoding, str_data, len);
    self->encoding[len] = '\0';
    return mp_obj_new_int(len);
}
static MP_DEFINE_CONST_FUN_OBJ_2(response_mp_set_encoding_obj, response_mp_set_encoding);

mp_obj_t response_mp_set_headers(mp_obj_t self_in, mp_obj_t headers_obj)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!mp_obj_is_dict_or_ordereddict(headers_obj))
    {
        mp_raise_TypeError(MP_ERROR_TEXT("headers must be a dict"));
    }
    self->headers = MP_OBJ_TO_PTR(headers_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(response_mp_set_headers_obj, response_mp_set_headers);

mp_obj_t response_mp_set_reason(mp_obj_t self_in, mp_obj_t reason_obj)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    size_t len;
    const char *str_data = mp_obj_str_get_data(reason_obj, &len);
    if (self->reason)
    {
        m_free(self->reason);
    }
    self->reason = m_malloc(len + 1);
    memcpy(self->reason, str_data, len);
    self->reason[len] = '\0';
    return mp_obj_new_int(len);
}
static MP_DEFINE_CONST_FUN_OBJ_2(response_mp_set_reason_obj, response_mp_set_reason);

mp_obj_t response_mp_set_status_code(mp_obj_t self_in, mp_obj_t status_code_obj)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->status_code = mp_obj_get_int(status_code_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(response_mp_set_status_code_obj, response_mp_set_status_code);

mp_obj_t response_mp_set_text(mp_obj_t self_in, mp_obj_t text_obj)
{
    response_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    size_t len;
    const char *str_data = mp_obj_str_get_data(text_obj, &len);
    if (self->text)
    {
        m_free(self->text);
    }
    self->text = m_malloc(len + 1);
    memcpy(self->text, str_data, len);
    self->text[len] = '\0';
    return mp_obj_new_int(len);
}
static MP_DEFINE_CONST_FUN_OBJ_2(response_mp_set_text_obj, response_mp_set_text);

static const mp_rom_map_elem_t response_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_content), MP_ROM_PTR(&response_mp_set_content_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_encoding), MP_ROM_PTR(&response_mp_set_encoding_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_headers), MP_ROM_PTR(&response_mp_set_headers_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_reason), MP_ROM_PTR(&response_mp_set_reason_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_status_code), MP_ROM_PTR(&response_mp_set_status_code_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_text), MP_ROM_PTR(&response_mp_set_text_obj)},
};
static MP_DEFINE_CONST_DICT(response_mp_locals_dict, response_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    response_mp_type,
    MP_QSTR_Response, // Name of the type in Python
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, response_mp_print,             // Print function
    make_new, response_mp_make_new,       // constructor
    attr, response_mp_attr,               // attribute handler
    locals_dict, &response_mp_locals_dict // Local methods
);
// Define module globals
static const mp_rom_map_elem_t response_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_response)},
    {MP_ROM_QSTR(MP_QSTR_Response), MP_ROM_PTR(&response_mp_type)},
};
static MP_DEFINE_CONST_DICT(response_module_globals, response_module_globals_table);

// Define module
const mp_obj_module_t response_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&response_module_globals,
};
// Register the module to make it available in Python
MP_REGISTER_MODULE(MP_QSTR_response, response_user_cmodule);