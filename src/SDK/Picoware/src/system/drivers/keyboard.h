/*
Author: Blair Leduc
License: MIT License
Source: https://github.com/BlairLeduc/picocalc-text-starter
*/

#pragma once

#include "pico/stdlib.h"

// Keyboard key definitions
#define KEY_MOD_ALT (0xA1)
#define KEY_MOD_SHL (0xA2)
#define KEY_MOD_SHR (0xA3)
#define KEY_MOD_SYM (0xA4)
#define KEY_MOD_CTRL (0xA5)

#define KEY_STATE_IDLE (0)
#define KEY_STATE_PRESSED (1)
#define KEY_STATE_HOLD (2)
#define KEY_STATE_RELEASED (3)

#define KEY_BACKSPACE (0x08)
#define KEY_TAB (0x09)
#define KEY_ENTER (0x0A)
#define KEY_RETURN (0x0D)
#define KEY_SPACE (0x20)

#define KEY_ESC (0xB1)
#define KEY_UP (0xB5)
#define KEY_DOWN (0xB6)
#define KEY_LEFT (0xB4)
#define KEY_RIGHT (0xB7)

#define KEY_BREAK (0xD0)
#define KEY_INSERT (0xD1)
#define KEY_HOME (0xD2)
#define KEY_DEL (0xD4)
#define KEY_END (0xD5)
#define KEY_PAGE_UP (0xD6)
#define KEY_PAGE_DOWN (0xD7)

#define KEY_CAPS_LOCK (0xC1)

#define KEY_F1 (0x81)
#define KEY_F2 (0x82)
#define KEY_F3 (0x83)
#define KEY_F4 (0x84)
#define KEY_F5 (0x85)
#define KEY_F6 (0x86)
#define KEY_F7 (0x87)
#define KEY_F8 (0x88)
#define KEY_F9 (0x89)
#define KEY_F10 (0x90)

#define KEY_POWER (0x91)

// Keyboard defaults
#define KBD_BUFFER_SIZE (32)
#define KEYBOARD_POLL_MS (100) // poll keyboard every 100 ms

#ifdef __cplusplus
extern "C"
{
#endif

    // Callback function type for when a key becomes available
    typedef void (*keyboard_key_available_callback_t)(void);

    // Global user interrupt flag
    extern volatile bool user_interrupt;

    // Keyboard Function prototypes
    void keyboard_init(void);
    void keyboard_set_key_available_callback(keyboard_key_available_callback_t callback);
    void keyboard_set_background_poll(bool enable);
    void keyboard_poll(void);
    bool keyboard_key_available(void);
    char keyboard_get_key(void);

#ifdef __cplusplus
}
#endif
