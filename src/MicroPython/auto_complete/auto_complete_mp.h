#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "auto_complete.h"

typedef struct
{
    mp_obj_base_t base;
    AutoComplete context;
    bool freed;
} auto_complete_mp_obj_t;

extern const mp_obj_type_t auto_complete_mp_type;

void auto_complete_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t auto_complete_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t auto_complete_mp_del(mp_obj_t self_in);
void auto_complete_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
mp_obj_t auto_complete_mp_add_word(mp_obj_t self_in, mp_obj_t word_obj);
mp_obj_t auto_complete_mp_remove_suggestions(mp_obj_t self_in);
mp_obj_t auto_complete_mp_remove_words(mp_obj_t self_in);
mp_obj_t auto_complete_mp_search(mp_obj_t self_in, mp_obj_t prefix_obj);
#if defined(STORAGE_INCLUDE) && defined(STORAGE_READ)
mp_obj_t auto_complete_mp_add_dictionary(mp_obj_t self_in, mp_obj_t filename_obj);
#endif
