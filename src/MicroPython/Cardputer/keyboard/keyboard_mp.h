#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

    mp_obj_t cardputer_keyboard_init(void);
    mp_obj_t cardputer_keyboard_deinit(void);
    mp_obj_t cardputer_keyboard_set_key_available_callback(mp_obj_t callback);
    mp_obj_t cardputer_keyboard_set_background_poll(mp_obj_t enable_obj);
    mp_obj_t cardputer_keyboard_poll(void);
    mp_obj_t cardputer_keyboard_key_available(void);
    mp_obj_t cardputer_keyboard_get_key(void);
    mp_obj_t cardputer_keyboard_get_key_nonblocking(void);

#ifdef __cplusplus
}
#endif