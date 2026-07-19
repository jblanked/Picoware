#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"

    mp_obj_t flipper_input_init(void);
    mp_obj_t flipper_input_deinit(void);
    mp_obj_t flipper_input_poll(void);
    mp_obj_t flipper_input_key_available(void);
    mp_obj_t flipper_input_get_key(void);
    mp_obj_t flipper_input_get_key_nonblocking(void);

#ifdef __cplusplus
}
#endif
