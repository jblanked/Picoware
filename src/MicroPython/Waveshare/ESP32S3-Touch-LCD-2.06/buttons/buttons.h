#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

// Non-alphanumeric key values surfaced through keyboard_event_t.ascii.
#define KEY_BACKSPACE (0x08)
#define KEY_TAB (0x09)
#define KEY_ENTER (0x0A)

#define KEY_ESC (0xB1)
#define KEY_LEFT (0xB4)
#define KEY_UP (0xB5)
#define KEY_DOWN (0xB6)
#define KEY_RIGHT (0xB7)

#define KEY_ALT (0xA1)
#define KEY_OPT (0xA2)
#define KEY_FN (0xA4)
#define KEY_CTRL (0xA5)
#define KEY_CAPS (0xC1)

typedef struct
{
    bool pressed;
    uint8_t keycode;
    char ascii;
} keyboard_event_t;

esp_err_t buttons_init(void);
esp_err_t buttons_read_event(keyboard_event_t *out_event, bool *has_event);
