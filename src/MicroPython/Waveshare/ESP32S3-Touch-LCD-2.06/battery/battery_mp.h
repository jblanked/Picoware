#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

    mp_obj_t cardputer_battery_init(void);
    mp_obj_t cardputer_battery_get_voltage(void);
    mp_obj_t cardputer_battery_get_percentage(void);

#ifdef __cplusplus
}
#endif