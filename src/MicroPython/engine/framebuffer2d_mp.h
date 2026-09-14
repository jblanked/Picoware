#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // FrameBuffer2D* in C++
        bool freed;
    } framebuffer2d_mp_obj_t;

    extern const mp_obj_type_t framebuffer2d_mp_type;

#ifdef __cplusplus
}
#endif
