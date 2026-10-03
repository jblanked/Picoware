#include "esp_err.h"
#include "py/runtime.h"

esp_err_t watch_battery_init(void);
esp_err_t watch_battery_read_voltage(float *voltage_v);
void watch_battery_deinit(void);

static bool s_initialized;

static esp_err_t watch_battery_ensure_init(void)
{
    if (s_initialized)
    {
        return ESP_OK;
    }
    esp_err_t err = watch_battery_init();
    if (err == ESP_OK)
    {
        s_initialized = true;
    }
    return err;
}

static mp_obj_t watch_battery_init_mp(void)
{
    const esp_err_t err = watch_battery_ensure_init();
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError, MP_ERROR_TEXT("Battery init failed: %d"), err);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(watch_battery_init_obj, watch_battery_init_mp);

static mp_obj_t watch_battery_get_voltage(void)
{
    float voltage = 0.0f;
    esp_err_t err = watch_battery_ensure_init();
    if (err == ESP_OK)
    {
        err = watch_battery_read_voltage(&voltage);
    }
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("Battery voltage read failed: %d"), err);
    }
    return mp_obj_new_float(voltage);
}
static MP_DEFINE_CONST_FUN_OBJ_0(watch_battery_get_voltage_obj, watch_battery_get_voltage);

static mp_obj_t watch_battery_get_percentage(void)
{
    float voltage = 0.0f;
    esp_err_t err = watch_battery_ensure_init();
    if (err == ESP_OK)
    {
        err = watch_battery_read_voltage(&voltage);
    }
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("Battery voltage read failed: %d"), err);
    }

    const float min_voltage = 3.3f;
    const float max_voltage = 4.2f;
    if (voltage <= min_voltage)
    {
        return mp_obj_new_int(0);
    }
    if (voltage >= max_voltage)
    {
        return mp_obj_new_int(100);
    }
    return mp_obj_new_int((int)(((voltage - min_voltage) * 100.0f /
                                 (max_voltage - min_voltage)) + 0.5f));
}
static MP_DEFINE_CONST_FUN_OBJ_0(watch_battery_get_percentage_obj, watch_battery_get_percentage);

static mp_obj_t watch_battery_deinit_mp(void)
{
    watch_battery_deinit();
    s_initialized = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(watch_battery_deinit_obj, watch_battery_deinit_mp);

static const mp_rom_map_elem_t watch_battery_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_crowpanel_watch_battery)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&watch_battery_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&watch_battery_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_voltage), MP_ROM_PTR(&watch_battery_get_voltage_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_percentage), MP_ROM_PTR(&watch_battery_get_percentage_obj)},
};
static MP_DEFINE_CONST_DICT(watch_battery_globals, watch_battery_globals_table);

const mp_obj_module_t crowpanel_watch_battery_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&watch_battery_globals,
};

MP_REGISTER_MODULE(MP_QSTR_crowpanel_watch_battery, crowpanel_watch_battery_module);
