#pragma once

#include "esp_err.h"

esp_err_t battery_init(void);
esp_err_t battery_read_voltage(float *voltage_v);
