#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

esp_err_t gpio_buttons_init(void);
esp_err_t gpio_buttons_deinit(void);
esp_err_t gpio_buttons_key_available(bool *has_key);
esp_err_t gpio_buttons_read_key(uint8_t *key, bool *has_key);
