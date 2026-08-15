/*
 * Shared I2C bus for the Marauder V8.
 *
 * The FT6336 and the MAX17048 share these pins, so the bus is refcounted and
 * only torn down once the last user releases it.
 */

#pragma once

#include "driver/i2c_master.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C"
{
#endif

    // Returns the shared bus handle, creating it on first call.
    esp_err_t v8_i2c_bus_acquire(i2c_master_bus_handle_t *out_bus);

    // Drops one reference; deletes the bus when the count reaches zero.
    void v8_i2c_bus_release(void);

    // Adds a device to the shared bus at the given 7-bit address.
    esp_err_t v8_i2c_add_device(uint16_t address, i2c_master_dev_handle_t *out_dev);

#ifdef __cplusplus
}
#endif
