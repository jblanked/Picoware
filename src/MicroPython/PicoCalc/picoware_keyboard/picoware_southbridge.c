/*
 * Picoware Southbridge Native C Extension for MicroPython
 * Direct exposure of southbridge.h methods
 * Copyright © 2025 JBlanked
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "southbridge.h"

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// init() - Initialize the southbridge
STATIC mp_obj_t picoware_southbridge_init(void)
{
    sb_init();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_init_obj, picoware_southbridge_init);

// available() - Check if southbridge is available
STATIC mp_obj_t picoware_southbridge_available(void)
{
    return mp_obj_new_bool(sb_available());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_available_obj, picoware_southbridge_available);

// read_keyboard() - Read keyboard value
STATIC mp_obj_t picoware_southbridge_read_keyboard(void)
{
    return MP_OBJ_NEW_SMALL_INT(sb_read_keyboard());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_read_keyboard_obj, picoware_southbridge_read_keyboard);

// read_keyboard_state() - Read keyboard state
STATIC mp_obj_t picoware_southbridge_read_keyboard_state(void)
{
    return MP_OBJ_NEW_SMALL_INT(sb_read_keyboard_state());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_read_keyboard_state_obj, picoware_southbridge_read_keyboard_state);

// read_battery() - Read battery level
STATIC mp_obj_t picoware_southbridge_read_battery(void)
{
    return MP_OBJ_NEW_SMALL_INT(sb_read_battery());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_read_battery_obj, picoware_southbridge_read_battery);

STATIC mp_obj_t picoware_southbridge_get_battery_percentage(void)
{
    int raw_level = sb_read_battery();
    int battery_level = raw_level & 0x7F; // Mask out the charging bit
    return MP_OBJ_NEW_SMALL_INT(battery_level);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_get_battery_percentage_obj, picoware_southbridge_get_battery_percentage);

STATIC mp_obj_t picoware_southbridge_is_battery_charging(void)
{
    int raw_level = sb_read_battery();
    bool charging = (raw_level & 0x80) != 0; // Check if charging
    return mp_obj_new_bool(charging);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_is_battery_charging_obj, picoware_southbridge_is_battery_charging);

// read_lcd_backlight() - Read LCD backlight brightness
STATIC mp_obj_t picoware_southbridge_read_lcd_backlight(void)
{
    return MP_OBJ_NEW_SMALL_INT(sb_read_lcd_backlight());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_read_lcd_backlight_obj, picoware_southbridge_read_lcd_backlight);

// write_lcd_backlight(brightness) - Set LCD backlight brightness
STATIC mp_obj_t picoware_southbridge_write_lcd_backlight(mp_obj_t brightness_obj)
{
    uint8_t brightness = mp_obj_get_int(brightness_obj);
    uint8_t result = sb_write_lcd_backlight(brightness);
    return MP_OBJ_NEW_SMALL_INT(result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_southbridge_write_lcd_backlight_obj, picoware_southbridge_write_lcd_backlight);

// read_keyboard_backlight() - Read keyboard backlight brightness
STATIC mp_obj_t picoware_southbridge_read_keyboard_backlight(void)
{
    return MP_OBJ_NEW_SMALL_INT(sb_read_keyboard_backlight());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_read_keyboard_backlight_obj, picoware_southbridge_read_keyboard_backlight);

// write_keyboard_backlight(brightness) - Set keyboard backlight brightness
STATIC mp_obj_t picoware_southbridge_write_keyboard_backlight(mp_obj_t brightness_obj)
{
    uint8_t brightness = mp_obj_get_int(brightness_obj);
    uint8_t result = sb_write_keyboard_backlight(brightness);
    return MP_OBJ_NEW_SMALL_INT(result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_southbridge_write_keyboard_backlight_obj, picoware_southbridge_write_keyboard_backlight);

// is_power_off_supported() - Check if power off is supported
STATIC mp_obj_t picoware_southbridge_is_power_off_supported(void)
{
    return mp_obj_new_bool(sb_is_power_off_supported());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_southbridge_is_power_off_supported_obj, picoware_southbridge_is_power_off_supported);

// write_power_off_delay(delay_seconds) - Set power off delay
STATIC mp_obj_t picoware_southbridge_write_power_off_delay(mp_obj_t delay_obj)
{
    uint8_t delay_seconds = mp_obj_get_int(delay_obj);
    return mp_obj_new_bool(sb_write_power_off_delay(delay_seconds));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_southbridge_write_power_off_delay_obj, picoware_southbridge_write_power_off_delay);

// reset(delay_seconds) - Reset the southbridge
STATIC mp_obj_t picoware_southbridge_reset(mp_obj_t delay_obj)
{
    uint8_t delay_seconds = mp_obj_get_int(delay_obj);
    return mp_obj_new_bool(sb_reset(delay_seconds));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_southbridge_reset_obj, picoware_southbridge_reset);

// Module globals
STATIC const mp_rom_map_elem_t picoware_southbridge_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_southbridge)},
    // Functions
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_southbridge_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_available), MP_ROM_PTR(&picoware_southbridge_available_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_keyboard), MP_ROM_PTR(&picoware_southbridge_read_keyboard_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_keyboard_state), MP_ROM_PTR(&picoware_southbridge_read_keyboard_state_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_battery), MP_ROM_PTR(&picoware_southbridge_read_battery_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_battery_percentage), MP_ROM_PTR(&picoware_southbridge_get_battery_percentage_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_battery_charging), MP_ROM_PTR(&picoware_southbridge_is_battery_charging_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_lcd_backlight), MP_ROM_PTR(&picoware_southbridge_read_lcd_backlight_obj)},
    {MP_ROM_QSTR(MP_QSTR_write_lcd_backlight), MP_ROM_PTR(&picoware_southbridge_write_lcd_backlight_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_keyboard_backlight), MP_ROM_PTR(&picoware_southbridge_read_keyboard_backlight_obj)},
    {MP_ROM_QSTR(MP_QSTR_write_keyboard_backlight), MP_ROM_PTR(&picoware_southbridge_write_keyboard_backlight_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_power_off_supported), MP_ROM_PTR(&picoware_southbridge_is_power_off_supported_obj)},
    {MP_ROM_QSTR(MP_QSTR_write_power_off_delay), MP_ROM_PTR(&picoware_southbridge_write_power_off_delay_obj)},
    {MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&picoware_southbridge_reset_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_southbridge_module_globals, picoware_southbridge_module_globals_table);

// Define the module
const mp_obj_module_t picoware_southbridge_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_southbridge_module_globals,
};

// Register the module
MP_REGISTER_MODULE(MP_QSTR_picoware_southbridge, picoware_southbridge_module);
