#include "buttons_mp.h"
#include "buttons.h"
#include "esp_err.h"
#include <stdint.h>

static mp_obj_t g_key_available_callback = mp_const_none;
static bool g_buttons_ready = false;

mp_obj_t buttons_init(void)
{
    if (!g_buttons_ready)
    {
        esp_err_t err = gpio_buttons_init();
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(&mp_type_RuntimeError,
                              MP_ERROR_TEXT("buttons_init failed: %d"), err);
        }
        g_buttons_ready = true;
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_init_obj, buttons_init);

mp_obj_t buttons_deinit(void)
{
    g_buttons_ready = false;
    g_key_available_callback = mp_const_none;
    g_background_poll = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_deinit_obj, buttons_deinit);

mp_obj_t buttons_set_key_available_callback(mp_obj_t callback)
{
    if (callback == mp_const_none || mp_obj_is_callable(callback))
    {
        g_key_available_callback = callback;
        return mp_const_none;
    }

    mp_raise_TypeError(MP_ERROR_TEXT("callback must be callable or None"));
}
static MP_DEFINE_CONST_FUN_OBJ_1(buttons_set_key_available_callback_obj,
                                 buttons_set_key_available_callback);

mp_obj_t buttons_key_available(void)
{
    bool has_key = false;

    esp_err_t err = gpio_buttons_key_available(&has_key);
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("buttons_key_avaliable failed: %d"), err);
    }

    return mp_obj_new_bool(has_key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_key_available_obj,
                                 buttons_key_available);

mp_obj_t buttons_get_key(void)
{
    uint8_t key = 0;
    bool has_key = false;
    esp_err_t err = gpio_buttons_read_key(&key, &has_key);
    if (err != ESP_OK || !has_key)
    {
        return mp_const_none;
    }

    return mp_obj_new_int(key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_get_key_obj, buttons_get_key);

static const mp_rom_map_elem_t buttons_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_gpio_buttons)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&buttons_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&buttons_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_key_available_callback), MP_ROM_PTR(&buttons_set_key_available_callback_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_available), MP_ROM_PTR(&buttons_key_available_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key), MP_ROM_PTR(&buttons_get_key_obj)},
};
static MP_DEFINE_CONST_DICT(buttons_module_globals,
                            buttons_module_globals_table);

const mp_obj_module_t gpio_buttons_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&buttons_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_gpio_buttons, gpio_buttons_module);
