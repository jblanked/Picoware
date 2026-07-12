#pragma once

#include "esp_err.h"
#include <stdbool.h>

esp_err_t sdcard_mount(void);
void sdcard_unmount(void);
bool sdcard_is_mounted(void);
