#include "battery_mp.h"
#include "battery.h"
#include "esp_err.h"

// With no cell fitted the board runs from USB, so report a full battery the way
// the mains-powered boards do instead of raising on every status-bar poll.
#define NO_CELL_VOLTAGE_V 4.2f
#define NO_CELL_PERCENTAGE 100

static bool g_battery_ready = false;

static esp_err_t ws_c5_35_battery_ensure_init(void)
{
    if (g_battery_ready)
    {
        return ESP_OK;
    }

    esp_err_t err = battery_init();
    if (err == ESP_OK)
    {
        g_battery_ready = true;
    }
    return err;
}

mp_obj_t ws_c5_35_battery_init(void)
{
    esp_err_t err = ws_c5_35_battery_ensure_init();
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("battery_init failed: %d"), err);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(ws_c5_35_battery_init_obj, ws_c5_35_battery_init);

mp_obj_t ws_c5_35_battery_get_voltage(void)
{
    float voltage_v = 0.0f;
    esp_err_t err = ws_c5_35_battery_ensure_init();
    if (err == ESP_OK)
    {
        err = battery_read_voltage(&voltage_v);
    }
    if (err == ESP_ERR_NOT_FOUND)
    {
        return mp_obj_new_float(NO_CELL_VOLTAGE_V);
    }

    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("battery_read_voltage failed: %d"), err);
    }
    const int millivolts = (int)(voltage_v * 1000);
    return mp_obj_new_int(millivolts);
}
static MP_DEFINE_CONST_FUN_OBJ_0(ws_c5_35_battery_get_voltage_obj, ws_c5_35_battery_get_voltage);

mp_obj_t ws_c5_35_battery_get_percentage(void)
{
    int percentage = 0;
    esp_err_t err = ws_c5_35_battery_ensure_init();
    if (err == ESP_OK)
    {
        err = battery_read_percentage(&percentage);
    }
    if (err == ESP_ERR_NOT_FOUND)
    {
        return mp_obj_new_int(NO_CELL_PERCENTAGE);
    }

    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("battery_read_percentage failed: %d"), err);
    }

    return mp_obj_new_int(percentage);
}
static MP_DEFINE_CONST_FUN_OBJ_0(ws_c5_35_battery_get_percentage_obj,
                                 ws_c5_35_battery_get_percentage);

static const mp_rom_map_elem_t ws_c5_35_battery_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ws_c5_35_battery)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&ws_c5_35_battery_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_voltage), MP_ROM_PTR(&ws_c5_35_battery_get_voltage_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_percentage), MP_ROM_PTR(&ws_c5_35_battery_get_percentage_obj)},
};
static MP_DEFINE_CONST_DICT(ws_c5_35_battery_module_globals,
                            ws_c5_35_battery_module_globals_table);

const mp_obj_module_t ws_c5_35_battery_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&ws_c5_35_battery_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_ws_c5_35_battery, ws_c5_35_battery_module);
