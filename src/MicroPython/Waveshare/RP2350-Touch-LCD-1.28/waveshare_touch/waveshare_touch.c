/*
 * Waveshare Touch Native C Extension for MicroPython
 *
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "touch.h"
#include <stdlib.h>
#include <string.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// Function to get the touch gesture
STATIC mp_obj_t waveshare_touch_get_gesture(void)
{
    uint8_t gesture = touch_get_gesture();
    return mp_obj_new_int(gesture);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_get_gesture_obj, waveshare_touch_get_gesture);

// Function to get the touch point
STATIC mp_obj_t waveshare_touch_get_touch_point(void)
{
    TouchVector point = touch_get_point();
    mp_obj_t tuple[2];
    tuple[0] = mp_obj_new_int(point.x);
    tuple[1] = mp_obj_new_int(point.y);
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_get_touch_point_obj, waveshare_touch_get_touch_point);

// Function to initialize the touch
STATIC mp_obj_t waveshare_touch_init(size_t n_args, const mp_obj_t *args)
{
    // Arguments: mode
    if (n_args != 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("init requires 1 argument: mode"));
    }
    uint8_t mode = mp_obj_get_int(args[0]);
    bool result = touch_init(mode);
    return mp_obj_new_bool(result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(waveshare_touch_init_obj, 1, 1, waveshare_touch_init);

// Function to reset the touch
STATIC mp_obj_t waveshare_touch_reset(void)
{
    touch_reset();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_reset_obj, waveshare_touch_reset);

// Define all functions in the module
STATIC const mp_rom_map_elem_t waveshare_touch_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_waveshare_touch)},
    {MP_ROM_QSTR(MP_QSTR_get_gesture), MP_ROM_PTR(&waveshare_touch_get_gesture_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_touch_point), MP_ROM_PTR(&waveshare_touch_get_touch_point_obj)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&waveshare_touch_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&waveshare_touch_reset_obj)},

    // Touch mode constants
    {MP_ROM_QSTR(MP_QSTR_TOUCH_POINT_MODE), MP_ROM_INT(TOUCH_POINT_MODE)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_MODE), MP_ROM_INT(TOUCH_GESTURE_MODE)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_ALL_MODE), MP_ROM_INT(TOUCH_ALL_MODE)},

    // Touch gesture constants
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_NONE), MP_ROM_INT(TOUCH_GESTURE_NONE)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_UP), MP_ROM_INT(TOUCH_GESTURE_UP)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_DOWN), MP_ROM_INT(TOUCH_GESTURE_DOWN)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_LEFT), MP_ROM_INT(TOUCH_GESTURE_LEFT)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_RIGHT), MP_ROM_INT(TOUCH_GESTURE_RIGHT)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_CLICK), MP_ROM_INT(TOUCH_GESTURE_CLICK)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_DOUBLE_CLICK), MP_ROM_INT(TOUCH_GESTURE_DOUBLE_CLICK)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_GESTURE_LONG_PRESS), MP_ROM_INT(TOUCH_GESTURE_LONG_PRESS)},
};

STATIC MP_DEFINE_CONST_DICT(waveshare_touch_module_globals, waveshare_touch_module_globals_table);

// Define module
const mp_obj_module_t waveshare_touch_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&waveshare_touch_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_waveshare_touch, waveshare_touch_user_cmodule);
