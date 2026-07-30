/*
 * Picoware Keys Native C Extension for MicroPython
 * Module name: picoware_keyboard
 *Copyright © 2025 JBlanked
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "keyboard.h"

// GC-scanned root for callback
MP_REGISTER_ROOT_POINTER(mp_obj_t picoware_keyboard_callback);

// ISR callback wrapper
static void c_key_available_callback(void)
{
    mp_obj_t cb = MP_STATE_VM(picoware_keyboard_callback);
    if (cb != NULL && cb != mp_const_none && mp_obj_is_callable(cb))
    {
        mp_sched_schedule(cb, mp_const_none);
    }
}

static mp_obj_t picoware_keyboard_init(void)
{
    keyboard_init();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_init_obj, picoware_keyboard_init);

static mp_obj_t picoware_keyboard_set_key_available_callback(mp_obj_t callback)
{
    if (callback == mp_const_none || mp_obj_is_callable(callback))
    {
        MP_STATE_VM(picoware_keyboard_callback) = callback;

        if (callback != mp_const_none)
        {
            keyboard_set_key_available_callback(c_key_available_callback);
        }
        else
        {
            keyboard_set_key_available_callback(NULL);
        }
        return mp_const_none;
    }
    else
    {
        mp_raise_TypeError(MP_ERROR_TEXT("callback must be callable or None"));
    }
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_keyboard_set_key_available_callback_obj, picoware_keyboard_set_key_available_callback);

static mp_obj_t picoware_keyboard_set_background_poll(mp_obj_t enable_obj)
{
    bool enable = mp_obj_is_true(enable_obj);
    keyboard_set_background_poll(enable);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_keyboard_set_background_poll_obj, picoware_keyboard_set_background_poll);

static mp_obj_t picoware_keyboard_poll(void)
{
    keyboard_poll();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_poll_obj, picoware_keyboard_poll);

static mp_obj_t picoware_keyboard_key_available(void)
{
    return mp_obj_new_bool(keyboard_key_available());
}
static MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_key_available_obj, picoware_keyboard_key_available);

static mp_obj_t picoware_keyboard_get_key(void)
{
    char key = keyboard_get_key();
    return mp_obj_new_int((unsigned char)key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_get_key_obj, picoware_keyboard_get_key);

static mp_obj_t picoware_keyboard_get_key_nonblocking(void)
{
    if (keyboard_key_available())
    {
        char key = keyboard_get_key();
        return mp_obj_new_int((unsigned char)key);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_get_key_nonblocking_obj, picoware_keyboard_get_key_nonblocking);

static const mp_rom_map_elem_t picoware_keyboard_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_keyboard)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_keyboard_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_key_available_callback), MP_ROM_PTR(&picoware_keyboard_set_key_available_callback_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_background_poll), MP_ROM_PTR(&picoware_keyboard_set_background_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&picoware_keyboard_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_available), MP_ROM_PTR(&picoware_keyboard_key_available_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key), MP_ROM_PTR(&picoware_keyboard_get_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key_nonblocking), MP_ROM_PTR(&picoware_keyboard_get_key_nonblocking_obj)},
};
static MP_DEFINE_CONST_DICT(picoware_keyboard_module_globals, picoware_keyboard_module_globals_table);

const mp_obj_module_t picoware_keyboard_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_keyboard_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_picoware_keyboard, picoware_keyboard_module);
