#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"

    bool poom_input_mp_init(void);
    void poom_input_mp_deinit(void);
    int poom_input_mp_read(void);

    mp_obj_t poom_input_init(void);
    mp_obj_t poom_input_deinit(void);
    mp_obj_t poom_input_poll(void);
    mp_obj_t poom_input_key_available(void);
    mp_obj_t poom_input_get_key(void);
    mp_obj_t poom_input_get_key_nonblocking(void);

#ifdef __cplusplus
}
#endif
