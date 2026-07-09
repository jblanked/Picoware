#pragma once
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

char *mjs_copy_string_arg(struct mjs *mjs, uint8_t arg);
mjs_val_t mjs_val_from_attr(struct mjs *mjs, mp_obj_t base, qstr attr);
mjs_val_t mjs_val_from_mp_obj(struct mjs *mjs, mp_obj_t obj);
mp_obj_t mjs_val_to_mp_obj(struct mjs *mjs, mjs_val_t val);