#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

#if defined(PICOCALC)
#include "../../JPEGDEC/src/JPEGDEC.h"
#include "../../JPEGDEC/src/jpeg.inl"
#else
#include "../../../JPEGDEC/src/JPEGDEC.h"
#include "../../../JPEGDEC/src/jpeg.inl"
#endif

typedef struct
{
    mp_obj_base_t base;
    JPEGIMAGE *context;
    bool initialized;
} jpegdec_mp_obj_t;

void jpegdec_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the JPEG decoder object
mp_obj_t jpegdec_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the JPEG decoder object
mp_obj_t jpegdec_mp_del(mp_obj_t self_in);                                                                 // destructor for the JPEG decoder object
void jpegdec_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the JPEG decoder object (e.g., to access

mp_obj_t jpegdec_decode(mp_obj_t self_in, mp_obj_t data);
mp_obj_t jpegdec_decodex2(size_t n_args, const mp_obj_t *args);
mp_obj_t jpegdec_decode_core(size_t n_args, const mp_obj_t *args);
mp_obj_t jpegdec_decode_core_stat(mp_obj_t self_in);
mp_obj_t jpegdec_decode_core_wait(size_t n_args, const mp_obj_t *args);
mp_obj_t jpegdec_decode_opt(size_t n_args, const mp_obj_t *args);
mp_obj_t jpegdec_decode_split(size_t n_args, const mp_obj_t *args);
mp_obj_t jpegdec_decode_split_buffer(size_t n_args, const mp_obj_t *args);
mp_obj_t jpegdec_decode_split_wait(mp_obj_t self_in);
mp_obj_t jpegdec_getinfo(mp_obj_t self_in, mp_obj_t data);