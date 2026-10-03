#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

esp_err_t gc9309_init(void);
void gc9309_deinit(void);
bool gc9309_is_initialized(void);
bool gc9309_set_backlight(uint32_t brightness);
esp_err_t gc9309_draw_bitmap(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                             const uint16_t *pixels);
