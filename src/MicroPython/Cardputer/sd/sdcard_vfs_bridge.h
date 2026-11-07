#pragma once
#include "esp_err.h"

esp_err_t sdcard_vfs_bridge_register(void);
esp_err_t sdcard_vfs_bridge_unregister(void);
// Discard previous-VM handles without dereferencing their freed objects.
void sdcard_vfs_bridge_reset(void);
