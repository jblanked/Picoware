#include "keyboard_input.h"
#include "keyboard.h"
#include "esp_timer.h"
#include <stddef.h>
#include <stdint.h>

#define CARDPUTER_KEYBOARD_QUEUE_SIZE (32)
#define CARDPUTER_KEY_REPEAT_DELAY_MS 500
#define CARDPUTER_KEY_REPEAT_INTERVAL_MS 100

static keyboard_input_callback_t g_key_available_callback;
static bool g_keyboard_ready = false;
static uint8_t g_key_queue[CARDPUTER_KEYBOARD_QUEUE_SIZE];
static uint8_t g_key_head = 0;
static uint8_t g_key_tail = 0;
static uint8_t g_repeat_keys[128];
static uint8_t g_repeat_keycode = 0;
static uint32_t g_repeat_at = 0;

static bool cardputer_keyboard_queue_empty(void)
{
    return g_key_head == g_key_tail;
}

static void cardputer_keyboard_queue_reset(void)
{
    g_key_head = 0;
    g_key_tail = 0;
    for (size_t keycode = 0; keycode < sizeof(g_repeat_keys); ++keycode)
    {
        g_repeat_keys[keycode] = 0;
    }
    g_repeat_keycode = 0;
    g_repeat_at = 0;
}

static void cardputer_keyboard_queue_push(uint8_t key)
{
    uint8_t next = (uint8_t)((g_key_head + 1U) % CARDPUTER_KEYBOARD_QUEUE_SIZE);
    if (next == g_key_tail)
    {
        // Drop oldest entry when queue is full.
        g_key_tail = (uint8_t)((g_key_tail + 1U) % CARDPUTER_KEYBOARD_QUEUE_SIZE);
    }

    g_key_queue[g_key_head] = key;
    g_key_head = next;

    if (g_key_available_callback != NULL)
    {
        g_key_available_callback();
    }
}

static bool cardputer_keyboard_queue_pop(uint8_t *key)
{
    if (key == NULL || cardputer_keyboard_queue_empty())
    {
        return false;
    }

    *key = g_key_queue[g_key_tail];
    g_key_tail = (uint8_t)((g_key_tail + 1U) % CARDPUTER_KEYBOARD_QUEUE_SIZE);
    return true;
}

static uint8_t cardputer_keyboard_event_to_key(const keyboard_event_t *event)
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

static void cardputer_keyboard_release_repeat_key(uint8_t keycode)
{
    g_repeat_keys[keycode] = 0;
    if (keycode != g_repeat_keycode)
    {
        return;
    }

    g_repeat_keycode = 0;
    for (uint8_t candidate = 1; candidate < sizeof(g_repeat_keys); ++candidate)
    {
        if (g_repeat_keys[candidate] != 0)
        {
            g_repeat_keycode = candidate;
            g_repeat_at = (uint32_t)(esp_timer_get_time() / 1000) +
                          CARDPUTER_KEY_REPEAT_DELAY_MS;
        }
    }
}

static void cardputer_keyboard_repeat_held_key(void)
{
    if (g_repeat_keycode == 0 || g_repeat_keys[g_repeat_keycode] == 0)
    {
        return;
    }

    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);
    if ((int32_t)(now - g_repeat_at) >= 0)
    {
        cardputer_keyboard_queue_push(g_repeat_keys[g_repeat_keycode]);
        g_repeat_at = now + CARDPUTER_KEY_REPEAT_INTERVAL_MS;
    }
}

void keyboard_input_poll(void)
{
    if (!g_keyboard_ready)
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
            cardputer_keyboard_release_repeat_key(event.keycode);
            continue;
        }
        uint8_t key = cardputer_keyboard_event_to_key(&event);
        if (key != 0)
        {
            cardputer_keyboard_queue_push(key);
            g_repeat_keycode = event.keycode;
            g_repeat_keys[event.keycode] = key;
            g_repeat_at = (uint32_t)(esp_timer_get_time() / 1000) +
                          CARDPUTER_KEY_REPEAT_DELAY_MS;
        }
    }

    cardputer_keyboard_repeat_held_key();
}

esp_err_t keyboard_input_init(void)
{
    if (!g_keyboard_ready)
    {
        esp_err_t err = keyboard_init();
        if (err != ESP_OK)
        {
            return err;
        }
        cardputer_keyboard_queue_reset();
        g_keyboard_ready = true;
    }
    return ESP_OK;
}

void keyboard_input_deinit(void)
{
    g_keyboard_ready = false;
    cardputer_keyboard_queue_reset();
    g_key_available_callback = NULL;
}

void keyboard_input_set_callback(keyboard_input_callback_t callback)
{
    g_key_available_callback = callback;
}

bool keyboard_input_is_pressed(void)
{
    keyboard_input_poll();
    return g_keyboard_ready && keyboard_is_pressed();
}

bool keyboard_input_key_available(void)
{
    return g_keyboard_ready && !cardputer_keyboard_queue_empty();
}

int keyboard_input_read(void)
{
    uint8_t key = 0;
    keyboard_input_poll();
    return cardputer_keyboard_queue_pop(&key) ? key : -1;
}
