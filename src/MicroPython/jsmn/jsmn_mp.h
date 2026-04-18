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

    mp_obj_t jsmn_mp_get_value(mp_obj_t key_in, mp_obj_t json_str_in);             // (key: str, json_str: str) -> str
    mp_obj_t jsmn_mp_get_array_value(mp_obj_t key_in, mp_obj_t index_in, mp_obj_t json_str_in); // (key: str, index: int, json_str: str) -> str

#ifdef __cplusplus
}
#endif