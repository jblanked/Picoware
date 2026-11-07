#pragma once

#include "keyboard.h"

esp_err_t keyboard_matrix_init(void);
esp_err_t keyboard_matrix_read(keyboard_event_t *event, bool *has_event);
