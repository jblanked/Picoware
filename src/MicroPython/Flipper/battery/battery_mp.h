#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"

    mp_obj_t flipper_battery_mp_init(void);
    mp_obj_t flipper_battery_mp_get_voltage_mv(void);
    mp_obj_t flipper_battery_mp_get_percentage(void);

#ifdef __cplusplus
}
#endif
