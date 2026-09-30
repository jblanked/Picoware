#include "buttons_mp.h"
#include "keyboard.h"
#include "esp_err.h"

#define GPIO_BUTTONS_QUEUE_SIZE (16)

static mp_obj_t g_key_available_callback = mp_const_none;
static bool g_background_poll = false;
static bool g_buttons_ready = false;
static uint8_t g_key_queue[GPIO_BUTTONS_QUEUE_SIZE];
static uint8_t g_key_head = 0;
static uint8_t g_key_tail = 0;

static bool buttons_queue_empty(void)
{
    return g_key_head == g_key_tail;
}

static void buttons_queue_reset(void)
{
    g_key_head = 0;
    g_key_tail = 0;
}

static void buttons_queue_push(uint8_t key)
{
    uint8_t next = (uint8_t)((g_key_head + 1U) % buttons_QUEUE_SIZE);
    if (next == g_key_tail)
    {
        // Drop oldest entry when queue is full.
        g_key_tail = (uint8_t)((g_key_tail + 1U) % buttons_QUEUE_SIZE);
    }

    g_key_queue[g_key_head] = key;
    g_key_head = next;

    if (g_key_available_callback != mp_const_none &&
        mp_obj_is_callable(g_key_available_callback))
    {
        mp_sched_schedule(g_key_available_callback, mp_const_none);
    }
}

static bool buttons_queue_pop(uint8_t *key)
{
    if (key == NULL || buttons_queue_empty())
    {
        return false;
    }

    *key = g_key_queue[g_key_tail];
    g_key_tail = (uint8_t)((g_key_tail + 1U) % buttons_QUEUE_SIZE);
    return true;
}

static uint8_t buttons_event_to_key(const keyboard_event_t *event)
{
    if (event == NULL)
    {
        return 0;
    }

    if (event->ascii != 0)
    {
        // Keep PicoCalc-compatible Enter semantics.
        if (event->ascii == '\n')
        {
            return '\r';
        }
        return (uint8_t)event->ascii;
    }

    // Unknown keycode without ASCII translation.
    return 0;
}

static void buttons_poll_internal(void)
{
    if (!g_buttons_ready)
    {
        return;
    }

    for (size_t event_count = 0; event_count < 8; ++event_count)
    {
        keyboard_event_t event = {0};
        bool has_event = false;
        esp_err_t err = keyboard_read_event(&event, &has_event);
        if (err != ESP_OK || !has_event)
        {
            break;
        }

        if (!event.pressed)
        {
            continue;
        }
        uint8_t key = buttons_event_to_key(&event);
        if (key != 0)
        {
            buttons_queue_push(key);
        }
    }
}

mp_obj_t buttons_init(void)
{
    if (!g_buttons_ready)
    {
        esp_err_t err = keyboard_init();
        if (err != ESP_OK)
        {
            mp_raise_msg_varg(&mp_type_RuntimeError,
                              MP_ERROR_TEXT("keyboard_init failed: %d"), err);
        }
        g_buttons_ready = true;
        buttons_queue_reset();
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_init_obj, buttons_init);

mp_obj_t buttons_deinit(void)
{
    g_buttons_ready = false;
    buttons_queue_reset();
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

mp_obj_t buttons_set_background_poll(mp_obj_t enable_obj)
{
    g_background_poll = mp_obj_is_true(enable_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(buttons_set_background_poll_obj,
                                 buttons_set_background_poll);

mp_obj_t buttons_poll(void)
{
    buttons_poll_internal();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_poll_obj, buttons_poll);

mp_obj_t buttons_key_available(void)
{
    if (g_background_poll)
    {
        buttons_poll_internal();
    }

    return mp_obj_new_bool(!buttons_queue_empty());
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_key_available_obj,
                                 buttons_key_available);

mp_obj_t buttons_get_key(void)
{
    uint8_t key = 0;

    while (!buttons_queue_pop(&key))
    {
        buttons_poll_internal();
        MICROPY_EVENT_POLL_HOOK;
        mp_hal_delay_ms(5);
    }

    return mp_obj_new_int(key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_get_key_obj, buttons_get_key);

mp_obj_t buttons_get_key_nonblocking(void)
{
    uint8_t key = 0;

    buttons_poll_internal();
    if (!buttons_queue_pop(&key))
    {
        return mp_const_none;
    }

    return mp_obj_new_int(key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(buttons_get_key_nonblocking_obj,
                                 buttons_get_key_nonblocking);

static const mp_rom_map_elem_t buttons_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_buttons)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&buttons_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&buttons_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_key_available_callback), MP_ROM_PTR(&buttons_set_key_available_callback_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_background_poll), MP_ROM_PTR(&buttons_set_background_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&buttons_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_available), MP_ROM_PTR(&buttons_key_available_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key), MP_ROM_PTR(&buttons_get_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key_nonblocking), MP_ROM_PTR(&buttons_get_key_nonblocking_obj)},
};
static MP_DEFINE_CONST_DICT(buttons_module_globals,
                            buttons_module_globals_table);

const mp_obj_module_t buttons_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&buttons_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_buttons, buttons_module);
