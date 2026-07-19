/* Flipper Zero input bindings */

#include "input_mp.h"
#include "input.h"
#include "py/mphal.h"

#define FLIPPER_INPUT_QUEUE_SIZE 16

#define KEY_UP ((uint8_t)0xB5)
#define KEY_DOWN ((uint8_t)0xB6)
#define KEY_LEFT ((uint8_t)0xB4)
#define KEY_RIGHT ((uint8_t)0xB7)
#define KEY_ESC ((uint8_t)0xB1)

static bool g_input_ready = false;
static uint8_t g_key_queue[FLIPPER_INPUT_QUEUE_SIZE];
static uint8_t g_key_head = 0;
static uint8_t g_key_tail = 0;
static uint8_t g_prev_mask = 0; /* Edge detection state */

static bool flipper_input_queue_empty(void)
{
    return g_key_head == g_key_tail;
}

static void flipper_input_queue_reset(void)
{
    g_key_head = 0;
    g_key_tail = 0;
    g_prev_mask = 0;
}

static void flipper_input_queue_push(uint8_t key)
{
    uint8_t next = (uint8_t)((g_key_head + 1U) % FLIPPER_INPUT_QUEUE_SIZE);
    if (next == g_key_tail)
    {
        /* Drop oldest on overflow */
        g_key_tail = (uint8_t)((g_key_tail + 1U) % FLIPPER_INPUT_QUEUE_SIZE);
    }
    g_key_queue[g_key_head] = key;
    g_key_head = next;
}

static bool flipper_input_queue_pop(uint8_t *key)
{
    if (key == NULL || flipper_input_queue_empty())
    {
        return false;
    }
    *key = g_key_queue[g_key_tail];
    g_key_tail = (uint8_t)((g_key_tail + 1U) % FLIPPER_INPUT_QUEUE_SIZE);
    return true;
}

/* Button pin to key code */
static uint8_t flipper_pin_to_key(uint8_t pin)
{
    switch (pin)
    {
    case FLIPPER_INPUT_UP:
        return KEY_UP;
    case FLIPPER_INPUT_DOWN:
        return KEY_DOWN;
    case FLIPPER_INPUT_RIGHT:
        return KEY_RIGHT;
    case FLIPPER_INPUT_LEFT:
        return KEY_LEFT;
    case FLIPPER_INPUT_OK:
        return '\r'; /* OK button */
    case FLIPPER_INPUT_BACK:
        return KEY_ESC;
    default:
        return 0;
    }
}

/* Rising-edge poll */
static void flipper_input_poll_internal(void)
{
    if (!g_input_ready)
    {
        return;
    }

    uint8_t mask = input_read_all();

    /* Detect new presses */
    uint8_t new_presses = mask & ~g_prev_mask;
    g_prev_mask = mask;

    for (uint8_t i = 0; i < FLIPPER_INPUT_COUNT; i++)
    {
        if (new_presses & (1U << i))
        {
            uint8_t key = flipper_pin_to_key(i);
            if (key != 0)
            {
                flipper_input_queue_push(key);
            }
        }
    }
}

mp_obj_t flipper_input_init(void)
{
    if (!g_input_ready)
    {
        if (!input_init())
        {
            mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("input_init failed"));
        }
        g_input_ready = true;
        flipper_input_queue_reset();
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_input_init_obj, flipper_input_init);

mp_obj_t flipper_input_deinit(void)
{
    g_input_ready = false;
    flipper_input_queue_reset();
    input_deinit();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_input_deinit_obj, flipper_input_deinit);

mp_obj_t flipper_input_poll(void)
{
    flipper_input_poll_internal();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_input_poll_obj, flipper_input_poll);

mp_obj_t flipper_input_key_available(void)
{
    flipper_input_poll_internal();
    return mp_obj_new_bool(!flipper_input_queue_empty());
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_input_key_available_obj,
                                 flipper_input_key_available);

mp_obj_t flipper_input_get_key(void)
{
    uint8_t key = 0;

    while (!flipper_input_queue_pop(&key))
    {
        flipper_input_poll_internal();
        mp_hal_delay_ms(5);
    }

    return mp_obj_new_int(key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_input_get_key_obj, flipper_input_get_key);

mp_obj_t flipper_input_get_key_nonblocking(void)
{
    uint8_t key = 0;

    flipper_input_poll_internal();
    if (!flipper_input_queue_pop(&key))
    {
        return mp_const_none;
    }

    return mp_obj_new_int(key);
}
static MP_DEFINE_CONST_FUN_OBJ_0(flipper_input_get_key_nonblocking_obj,
                                 flipper_input_get_key_nonblocking);

static const mp_rom_map_elem_t flipper_input_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_flipper_input)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&flipper_input_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&flipper_input_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&flipper_input_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_available), MP_ROM_PTR(&flipper_input_key_available_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key), MP_ROM_PTR(&flipper_input_get_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_key_nonblocking), MP_ROM_PTR(&flipper_input_get_key_nonblocking_obj)},
};
static MP_DEFINE_CONST_DICT(flipper_input_module_globals,
                            flipper_input_module_globals_table);

const mp_obj_module_t flipper_input_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&flipper_input_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_flipper_input, flipper_input_module);