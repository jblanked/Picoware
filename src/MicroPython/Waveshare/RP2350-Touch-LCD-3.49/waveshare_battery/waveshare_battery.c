/*
 * Waveshare Battery Native C Extension for MicroPython
 *
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "battery.h"
#include <stdlib.h>
#include <string.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// Function to get the battery percentage
STATIC mp_obj_t waveshare_battery_get_percentage(void)
{
    uint8_t percentage = battery_get_percentage();
    return mp_obj_new_int(percentage);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_battery_get_percentage_obj, waveshare_battery_get_percentage);

// Function to get the battery voltage
STATIC mp_obj_t waveshare_battery_get_voltage(void)
{
    float voltage = battery_get_voltage();
    return mp_obj_new_float(voltage);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_battery_get_voltage_obj, waveshare_battery_get_voltage);

// Function to initialize the battery monitoring
STATIC mp_obj_t waveshare_battery_init(void)
{
    battery_init();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_battery_init_obj, waveshare_battery_init);

// Function to read raw battery ADC value
STATIC mp_obj_t waveshare_battery_read(void)
{
    uint16_t adc_value = battery_read();
    return mp_obj_new_int(adc_value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(waveshare_battery_read_obj, waveshare_battery_read);

// Define all functions in the module
STATIC const mp_rom_map_elem_t waveshare_battery_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_waveshare_battery)},
    {MP_ROM_QSTR(MP_QSTR_get_percentage), MP_ROM_PTR(&waveshare_battery_get_percentage_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_voltage), MP_ROM_PTR(&waveshare_battery_get_voltage_obj)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&waveshare_battery_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&waveshare_battery_read_obj)},
};

STATIC MP_DEFINE_CONST_DICT(waveshare_battery_module_globals, waveshare_battery_module_globals_table);

// module definition
const mp_obj_module_t waveshare_battery_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&waveshare_battery_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_waveshare_battery, waveshare_battery_user_cmodule);