/*
 * Picoware Keys Native C Extension for MicroPython
 * Module name: picoware_keyboard
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "keyboard.h"

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// Global variable to store the Python callback
// Note: The callback object is kept alive by being referenced from the Input class instance in Python.
STATIC mp_obj_t g_key_available_callback = mp_const_none;

// C callback that will be registered with keyboard.h
STATIC void c_key_available_callback(void)
{
    if (g_key_available_callback != mp_const_none && mp_obj_is_callable(g_key_available_callback))
    {
        // Schedule the Python callback to run on the main thread
        // mp_sched_schedule will call the function with one argument (mp_const_none)
        // The Python callback should accept an optional argument for this
        mp_sched_schedule(g_key_available_callback, mp_const_none);
    }
}

// init() - Initialize the keyboard
STATIC mp_obj_t picoware_keyboard_init(void)
{
    keyboard_init();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_init_obj, picoware_keyboard_init);

// set_key_available_callback(callback) - Set callback for when key is available
STATIC mp_obj_t picoware_keyboard_set_key_available_callback(mp_obj_t callback)
{
    if (callback == mp_const_none || mp_obj_is_callable(callback))
    {
        // Store the callback - it will be protected from GC via module globals
        g_key_available_callback = callback;

        if (callback != mp_const_none)
        {
            // Register our C callback wrapper with the keyboard driver
            keyboard_set_key_available_callback(c_key_available_callback);
        }
        else
        {
            // Unregister callback
            keyboard_set_key_available_callback(NULL);
        }
        return mp_const_none;
    }
    else
    {
        mp_raise_TypeError(MP_ERROR_TEXT("callback must be callable or None"));
    }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_keyboard_set_key_available_callback_obj, picoware_keyboard_set_key_available_callback);

// set_background_poll(enable) - Enable/disable background polling
STATIC mp_obj_t picoware_keyboard_set_background_poll(mp_obj_t enable_obj)
{
    bool enable = mp_obj_is_true(enable_obj);
    keyboard_set_background_poll(enable);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_keyboard_set_background_poll_obj, picoware_keyboard_set_background_poll);

// poll() - Poll the keyboard
STATIC mp_obj_t picoware_keyboard_poll(void)
{
    keyboard_poll();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_poll_obj, picoware_keyboard_poll);

// key_available() - Check if a key is available
STATIC mp_obj_t picoware_keyboard_key_available(void)
{
    return mp_obj_new_bool(keyboard_key_available());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_key_available_obj, picoware_keyboard_key_available);

// get_key() - Get a key (blocking) - returns the key code as an integer
STATIC mp_obj_t picoware_keyboard_get_key(void)
{
    char key = keyboard_get_key();
    // Return as integer (unsigned) to properly handle special keys (> 127)
    return mp_obj_new_int((unsigned char)key);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_get_key_obj, picoware_keyboard_get_key);

// get_key_nonblocking() - Get a key without blocking, returns None if no key available
STATIC mp_obj_t picoware_keyboard_get_key_nonblocking(void)
{
    if (keyboard_key_available())
    {
        char key = keyboard_get_key();
        // Return as integer (unsigned) to properly handle special keys (> 127)
        return mp_obj_new_int((unsigned char)key);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_keyboard_get_key_nonblocking_obj, picoware_keyboard_get_key_nonblocking);

// Module globals
STATIC const mp_rom_map_elem_t picoware_keyboard_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_keyboard)},
    // Functions
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_keyboard_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_key_available_callback), MP_ROM_PTR(&picoware_keyboard_set_key_available_callback_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_background_poll), MP_ROM_PTR(&picoware_keyboard_set_background_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&picoware_keyboard_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_available), MP_ROM_PTR(&picoware_keyboard_key_available_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key), MP_ROM_PTR(&picoware_keyboard_get_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key_nonblocking), MP_ROM_PTR(&picoware_keyboard_get_key_nonblocking_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_keyboard_module_globals, picoware_keyboard_module_globals_table);

// Define the module
const mp_obj_module_t picoware_keyboard_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_keyboard_module_globals,
};

// Register the module
MP_REGISTER_MODULE(MP_QSTR_picoware_keyboard, picoware_keyboard_module);
