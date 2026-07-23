#include "battery_mp.h"
#include "battery.h"
#include "../board_config.h"
#include "log_mp.h"

#ifndef PRINT
#define PRINT(...) LOG_MESSAGE(__VA_ARGS__)
#endif

static bool g_battery_ready = false;

/* 3.3V = 0%, 4.2V = 100% */
static int flipper_battery_percent_from_mv(uint16_t mv)
{
    const uint16_t min_mv = 3300;
    const uint16_t max_mv = 4160;

    if (mv <= min_mv)
        return 0;
    if (mv >= max_mv)
        return 100;

    int pct = (int)(((int32_t)(mv - min_mv) * 100) / (max_mv - min_mv));
    return pct > 100 ? 100 : (pct < 0 ? 0 : pct);
}

mp_obj_t flipper_battery_mp_init(void)
{
    if (g_battery_ready)
        return mp_const_none;

    if (!flipper_battery_init())
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("flipper_battery_init failed"));
    }

    g_battery_ready = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_battery_mp_init_obj, flipper_battery_mp_init);

mp_obj_t flipper_battery_mp_deinit(void)
{
    if (!g_battery_ready)
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("battery not initialized"));

    flipper_battery_deinit();
    g_battery_ready = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_battery_mp_deinit_obj, flipper_battery_mp_deinit);

mp_obj_t flipper_battery_mp_get_voltage_mv(void)
{
    if (!g_battery_ready)
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("battery not initialized"));

    uint16_t mv = flipper_battery_read_mv();
    return mp_obj_new_int(mv);
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_battery_mp_get_voltage_mv_obj, flipper_battery_mp_get_voltage_mv);

mp_obj_t flipper_battery_mp_get_percentage(void)
{
    if (!g_battery_ready)
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("battery not initialized"));

    uint16_t mv = flipper_battery_read_mv();
    return mp_obj_new_int(flipper_battery_percent_from_mv(mv));
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_battery_mp_get_percentage_obj, flipper_battery_mp_get_percentage);

mp_obj_t flipper_battery_mp_shutdown(void)
{
    if (!g_battery_ready)
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("battery not initialized"));

    flipper_battery_shutdown();
    g_battery_ready = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_battery_mp_shutdown_obj, flipper_battery_mp_shutdown);

static const mp_rom_map_elem_t flipper_battery_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_flipper_battery)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&flipper_battery_mp_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&flipper_battery_mp_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_voltage_mv), MP_ROM_PTR(&flipper_battery_mp_get_voltage_mv_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_percentage), MP_ROM_PTR(&flipper_battery_mp_get_percentage_obj)},
    {MP_ROM_QSTR(MP_QSTR_shutdown), MP_ROM_PTR(&flipper_battery_mp_shutdown_obj)},
};
static MP_DEFINE_CONST_DICT(flipper_battery_module_globals,
                            flipper_battery_module_globals_table);

const mp_obj_module_t flipper_battery_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&flipper_battery_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_flipper_battery, flipper_battery_module);
