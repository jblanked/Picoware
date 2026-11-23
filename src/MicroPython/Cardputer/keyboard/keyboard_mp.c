#include "keyboard_mp.h"
#include "keyboard_input.h"

static mp_obj_t g_key_available_callback = mp_const_none;
static bool g_background_poll = false;

static void cardputer_keyboard_notify(void)
{
    if (g_key_available_callback != mp_const_none &&
        mp_obj_is_callable(g_key_available_callback))
    {
        mp_sched_schedule(g_key_available_callback, mp_const_none);
    }
}

mp_obj_t cardputer_keyboard_init(void)
{
    esp_err_t err = keyboard_input_init();
    if (err != ESP_OK)
    {
        mp_raise_msg_varg(&mp_type_RuntimeError,
                          MP_ERROR_TEXT("keyboard_init failed: %d"), err);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_keyboard_init_obj, cardputer_keyboard_init);

mp_obj_t cardputer_keyboard_deinit(void)
{
    keyboard_input_deinit();
    g_key_available_callback = mp_const_none;
    g_background_poll = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_keyboard_deinit_obj, cardputer_keyboard_deinit);

mp_obj_t cardputer_keyboard_set_key_available_callback(mp_obj_t callback)
{
    if (callback == mp_const_none || mp_obj_is_callable(callback))
    {
        g_key_available_callback = callback;
        keyboard_input_set_callback(callback == mp_const_none ? NULL : cardputer_keyboard_notify);
        return mp_const_none;
    }

    mp_raise_TypeError(MP_ERROR_TEXT("callback must be callable or None"));
}
static MP_DEFINE_CONST_FUN_OBJ_1(cardputer_keyboard_set_key_available_callback_obj,
                                 cardputer_keyboard_set_key_available_callback);

mp_obj_t cardputer_keyboard_set_background_poll(mp_obj_t enable_obj)
{
    g_background_poll = mp_obj_is_true(enable_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(cardputer_keyboard_set_background_poll_obj,
                                 cardputer_keyboard_set_background_poll);

mp_obj_t cardputer_keyboard_poll(void)
{
    keyboard_input_poll();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_keyboard_poll_obj, cardputer_keyboard_poll);

mp_obj_t cardputer_keyboard_is_pressed(void)
{
    return mp_obj_new_bool(keyboard_input_is_pressed());
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_keyboard_is_pressed_obj,
                                 cardputer_keyboard_is_pressed);

mp_obj_t cardputer_keyboard_key_available(void)
{
    if (g_background_poll)
    {
        keyboard_input_poll();
    }

    return mp_obj_new_bool(keyboard_input_key_available());
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_keyboard_key_available_obj,
                                 cardputer_keyboard_key_available);

mp_obj_t cardputer_keyboard_get_key(void)
{
    int key;
    while ((key = keyboard_input_read()) < 0)
    {
        MICROPY_EVENT_POLL_HOOK;
        mp_hal_delay_ms(5);
    }

    return mp_obj_new_int(key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_keyboard_get_key_obj, cardputer_keyboard_get_key);

mp_obj_t cardputer_keyboard_get_key_nonblocking(void)
{
    int key = keyboard_input_read();
    return key < 0 ? mp_const_none : mp_obj_new_int(key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(cardputer_keyboard_get_key_nonblocking_obj,
                                 cardputer_keyboard_get_key_nonblocking);

static const mp_rom_map_elem_t cardputer_keyboard_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_cardputer_keyboard)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&cardputer_keyboard_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&cardputer_keyboard_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_key_available_callback), MP_ROM_PTR(&cardputer_keyboard_set_key_available_callback_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_background_poll), MP_ROM_PTR(&cardputer_keyboard_set_background_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&cardputer_keyboard_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_pressed), MP_ROM_PTR(&cardputer_keyboard_is_pressed_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_available), MP_ROM_PTR(&cardputer_keyboard_key_available_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key), MP_ROM_PTR(&cardputer_keyboard_get_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key_nonblocking), MP_ROM_PTR(&cardputer_keyboard_get_key_nonblocking_obj)},
};
static MP_DEFINE_CONST_DICT(cardputer_keyboard_module_globals,
                            cardputer_keyboard_module_globals_table);

const mp_obj_module_t cardputer_keyboard_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&cardputer_keyboard_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_cardputer_keyboard, cardputer_keyboard_module);