#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "../mjs/src/mjs_core.h"
#include "../mjs/src/mjs_array_public.h"
#include "../mjs/src/mjs_object_public.h"
#include "../mjs/src/mjs_string_public.h"
#include "../mjs/src/mjs_util_public.h"
#include "../mjs/src/mjs_primitive_public.h"
#include "../mjs/mjs.h"

/* Undef NORETURN to avoid conflict with MicroPython mpconfig.h */
#undef NORETURN

    typedef struct
    {
        const uint8_t *data;
        size_t length;
        uint8_t *owned_data;
    } mjs_input_buffer;

    char *mjs_copy_string_arg(struct mjs *mjs, uint8_t arg);
    mjs_val_t mjs_val_from_attr(struct mjs *mjs, mp_obj_t base, qstr attr);
    mjs_val_t mjs_val_from_mp_obj(struct mjs *mjs, mp_obj_t obj);
    mp_obj_t mjs_val_to_mp_obj(struct mjs *mjs, mjs_val_t val);
    uint16_t mjs_get_color(struct mjs *mjs, mjs_val_t value);
    float mjs_get_float(struct mjs *mjs, uint8_t arg);
    bool mjs_get_boolean(struct mjs *mjs, uint8_t arg);
    mjs_val_t mjs_mk_vector(struct mjs *mjs, float x, float y, float z);
    bool mjs_get_vector(struct mjs *mjs, uint8_t arg, float *x, float *y, float *z);
    void mjs_input_buffer_free(mjs_input_buffer *buffer);
    bool mjs_read_buffer(struct mjs *mjs, mjs_val_t value, size_t expected_length,
                         bool exact_length, const char *name, mjs_input_buffer *buffer);
    void mjs_slot_release(void *p);
    void mjs_slot_set(void *p);
    void mjs_slot_sweep(void);

#ifdef __cplusplus
}
#endif