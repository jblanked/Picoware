#include "../../../input/input.h"
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

static TouchVector last_touch_point = {0, 0};

// Function to get the touch point
STATIC mp_obj_t waveshare_touch_get_touch_point(void)
{
    mp_obj_t tuple[2];
    tuple[0] = mp_obj_new_int(last_touch_point.x);
    tuple[1] = mp_obj_new_int(last_touch_point.y);
    last_touch_point = touch_get_point();
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_get_touch_point_obj, waveshare_touch_get_touch_point);

// Function to initialize the touch
STATIC mp_obj_t waveshare_touch_init(void)
{
    touch_init();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_init_obj, waveshare_touch_init);

// Function to read touch data
STATIC mp_obj_t waveshare_touch_read_data(void)
{
    touch_read_data(true);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_read_data_obj, waveshare_touch_read_data);

// Function to reset the touch
STATIC mp_obj_t waveshare_touch_reset(void)
{
    touch_reset();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_reset_obj, waveshare_touch_reset);

// Function to reset the touch state
STATIC mp_obj_t waveshare_touch_reset_state(void)
{
    last_touch_point.x = 0;
    last_touch_point.y = 0;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_touch_reset_state_obj, waveshare_touch_reset_state);

// Define all functions in the module
STATIC const mp_rom_map_elem_t waveshare_touch_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_waveshare_touch)},
    {MP_ROM_QSTR(MP_QSTR_get_touch_point), MP_ROM_PTR(&waveshare_touch_get_touch_point_obj)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&waveshare_touch_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_data), MP_ROM_PTR(&waveshare_touch_read_data_obj)},
    {MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&waveshare_touch_reset_obj)},
    {MP_ROM_QSTR(MP_QSTR_reset_state), MP_ROM_PTR(&waveshare_touch_reset_state_obj)},
};

STATIC MP_DEFINE_CONST_DICT(waveshare_touch_module_globals, waveshare_touch_module_globals_table);

// Define module
const mp_obj_module_t waveshare_touch_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&waveshare_touch_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_waveshare_touch, waveshare_touch_user_cmodule);

static bool touch_input_pressed = false;

static int touch_input_map_point(uint16_t x, uint16_t y)
{
    const uint16_t width = 466;
    const uint16_t height = 466;

    if (x <= (width * 15 / 100) &&
        y <= (height * 12 / 100))
    {
        return 5;
    }
    if (width * 85 / 100 <= x &&
        height * 30 / 100 <= y &&
        y <= height * 70 / 100)
    {
        return 2;
    }
    if (x <= width * 15 / 100 &&
        height * 30 / 100 <= y &&
        y <= height * 70 / 100)
    {
        return 3;
    }
    if (width * 20 / 100 <= x &&
        x <= width * 80 / 100 &&
        y <= height * 20 / 100)
    {
        return 0;
    }
    if (width * 20 / 100 <= x &&
        x <= width * 80 / 100 &&
        y >= height * 80 / 100)
    {
        return 1;
    }
    if (width * 40 / 100 <= x &&
        x <= width * 60 / 100 &&
        height * 40 / 100 <= y &&
        y <= height * 60 / 100)
    {
        return 4;
    }
    return -1;
}

bool touch_input_init(void)
{
    touch_input_pressed = false;
    touch_init();
    return true;
}

void touch_input_deinit(void)
{
    touch_input_pressed = false;
    touch_reset_state();
    touch_reset();
}

int touch_input_read(void)
{
    TouchVector point = touch_get_point();
    input_set_touch(point.x, point.y, 0, point.x != 0 || point.y != 0);
    if (point.x == 0 && point.y == 0)
    {
        touch_input_pressed = false;
        return -1;
    }

    if (touch_input_pressed)
    {
        return -1;
    }
    touch_input_pressed = true;
    return touch_input_map_point(point.x, point.y);
}
