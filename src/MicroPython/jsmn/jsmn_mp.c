#include "jsmn_mp.h"
#include "jsmn.h"

mp_obj_t jsmn_mp_get_value(mp_obj_t key_in, mp_obj_t json_str_in)
{
    const char *key = mp_obj_str_get_str(key_in);
    const char *json_str = mp_obj_str_get_str(json_str_in);
    char *value = get_json_value(key, json_str);
    if (value)
    {
        mp_obj_t result = mp_obj_new_str(value, strlen(value));
        m_free(value);
        return result;
    }
    mp_raise_ValueError(MP_ERROR_TEXT("Key not found in JSON"));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(jsmn_mp_get_value_obj, jsmn_mp_get_value);

mp_obj_t jsmn_mp_get_array_value(mp_obj_t key_in, mp_obj_t index_in, mp_obj_t json_str_in)
{
    const char *key = mp_obj_str_get_str(key_in);
    int index = mp_obj_get_int(index_in);
    const char *json_str = mp_obj_str_get_str(json_str_in);
    char *value = get_json_array_value(key, index, json_str);
    if (value)
    {
        mp_obj_t result = mp_obj_new_str(value, strlen(value));
        m_free(value);
        return result;
    }
    mp_raise_ValueError(MP_ERROR_TEXT("Key or index not found in JSON"));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(jsmn_mp_get_array_value_obj, jsmn_mp_get_array_value);

static const mp_rom_map_elem_t jsmn_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_jsmn)},
    {MP_ROM_QSTR(MP_QSTR_value), MP_ROM_PTR(&jsmn_mp_get_value_obj)}, // from jsmn import value
    {MP_ROM_QSTR(MP_QSTR_array_value), MP_ROM_PTR(&jsmn_mp_get_array_value_obj)}, // from jsmn import array_value
};
static MP_DEFINE_CONST_DICT(jsmn_module_globals, jsmn_module_globals_table);

// Define module
const mp_obj_module_t jsmn_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&jsmn_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_jsmn, jsmn_user_cmodule);