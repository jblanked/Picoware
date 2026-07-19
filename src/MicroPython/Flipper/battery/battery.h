#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C"
{
#endif

    bool flipper_battery_init(void);
    void flipper_battery_deinit(void);
    uint16_t flipper_battery_read_mv(void);

#ifdef __cplusplus
}
#endif
