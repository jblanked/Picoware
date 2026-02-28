#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

#if defined(PICOCALC)
#include "../../vector/vector_mp.h"
#else
#include "../../../vector/vector_mp.h"
#endif

typedef struct
{
    mp_obj_base_t base;
    mp_obj_t game;
    int fps;
    bool freed;
} engine_mp_obj_t;

extern const mp_obj_type_t engine_mp_type;

void engine_mp_del_reference(mp_obj_t mp_obj);
void engine_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t engine_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t engine_mp_del(mp_obj_t self_in);
void engine_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);