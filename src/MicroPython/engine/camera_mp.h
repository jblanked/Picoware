#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

// Camera perspective types for 3D rendering
#define CAMERA_FIRST_PERSON 0 // Default - render from player's own position/view
#define CAMERA_THIRD_PERSON 1 // Render from external camera position

extern const mp_obj_type_t camera_mp_type;

void camera_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t camera_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t camera_mp_del(mp_obj_t self_in);
void camera_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);