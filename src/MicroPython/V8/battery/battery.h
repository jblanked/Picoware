#pragma once

#include "esp_err.h"

esp_err_t battery_init(void);
esp_err_t battery_read_voltage(float *voltage_v);

// The MAX17048 tracks state of charge itself, so read it from the gauge.
esp_err_t battery_read_percentage(int *percentage);
