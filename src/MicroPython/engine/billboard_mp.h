#pragma once
#include "image_mp.h"
#ifdef __cplusplus
extern "C" {
#endif
    typedef struct {
        mp_obj_base_t base;
        void *context;
        mp_obj_t images[64];
    } billboard_mp_obj_t;
    extern const mp_obj_type_t billboard_mp_type;
#ifdef __cplusplus
}
#endif
