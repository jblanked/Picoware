#pragma once

#include "esp_err.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*keyboard_input_callback_t)(void);

esp_err_t keyboard_input_init(void);
void keyboard_input_deinit(void);
void keyboard_input_poll(void);
void keyboard_input_set_callback(keyboard_input_callback_t callback);
bool keyboard_input_is_pressed(void);
bool keyboard_input_key_available(void);
// Return a queued key byte, or -1 when no key is available.
int keyboard_input_read(void);

#ifdef __cplusplus
}
#endif
