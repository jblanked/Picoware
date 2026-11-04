#pragma once

#include "esp_err.h"

esp_err_t battery_init(void);
esp_err_t battery_read_voltage(float *voltage_v);

// The AXP2101 fuel gauge tracks state of charge itself, so read it from the PMU.
// Both reads return ESP_ERR_NOT_FOUND while no cell is fitted.
esp_err_t battery_read_percentage(int *percentage);
