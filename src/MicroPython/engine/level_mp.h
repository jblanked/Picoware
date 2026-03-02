#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

typedef struct
{
    mp_obj_base_t base;
    char *name;
    mp_obj_t size;
    mp_obj_t entities;
    bool freed;
} level_mp_obj_t;

extern const mp_obj_type_t level_mp_type;

void level_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t level_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t level_mp_del(mp_obj_t self_in);
void level_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);