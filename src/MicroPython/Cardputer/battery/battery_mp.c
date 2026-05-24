#include "battery_mp.h"
#include "battery.h"
#include "esp_err.h"

static bool g_battery_ready = false;

static int cardputer_battery_percent_from_voltage(float voltage_v)
{
    const float min_v = 3.2f;
    const float max_v = 4.2f;

    if (voltage_v <= min_v)
    {
        return 0;
    }
    if (voltage_v >= max_v)
    {
        return 100;
    }

    float scaled = ((voltage_v - min_v) * 100.0f) / (max_v - min_v);
    return (int)(scaled + 0.5f);
}

static esp_err_t cardputer_battery_ensure_init(void)
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

mp_obj_t cardputer_battery_init(void)
{
    esp_err_t err = cardputer_battery_ensure_init();
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("battery_init failed: %d"), err);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_battery_init_obj, cardputer_battery_init);

mp_obj_t cardputer_battery_get_voltage(void)
{
    float voltage_v = 0.0f;
    esp_err_t err = cardputer_battery_ensure_init();
    if (err == ESP_OK)
    {
        err = battery_read_voltage(&voltage_v);
    }

    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("battery_read_voltage failed: %d"), err);
    }

    return mp_obj_new_float(voltage_v);
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_battery_get_voltage_obj,
                                 cardputer_battery_get_voltage);

mp_obj_t cardputer_battery_get_percentage(void)
{
    float voltage_v = 0.0f;
    esp_err_t err = cardputer_battery_ensure_init();
    if (err == ESP_OK)
    {
        err = battery_read_voltage(&voltage_v);
    }

    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("battery_read_voltage failed: %d"), err);
    }

    return mp_obj_new_int(cardputer_battery_percent_from_voltage(voltage_v));
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_battery_get_percentage_obj,
                                 cardputer_battery_get_percentage);

static const mp_rom_map_elem_t cardputer_battery_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_cardputer_battery)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&cardputer_battery_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_voltage), MP_ROM_PTR(&cardputer_battery_get_voltage_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_percentage), MP_ROM_PTR(&cardputer_battery_get_percentage_obj)},
};
static MP_DEFINE_CONST_DICT(cardputer_battery_module_globals,
                            cardputer_battery_module_globals_table);

const mp_obj_module_t cardputer_battery_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&cardputer_battery_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_cardputer_battery, cardputer_battery_module);