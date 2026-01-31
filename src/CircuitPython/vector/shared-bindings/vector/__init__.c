#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "stdio.h"
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "shared-module/vector/__init__.h"

#ifndef STATIC
#define STATIC static
#endif

typedef struct
{
    mp_obj_base_t base;
    float x;
    float y;
    bool integer;
} vector_mp_obj_t;

const mp_obj_type_t vector_mp_type;

STATIC void vector_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Vector(");
    mp_print_str(print, "x=");
    mp_obj_print_helper(print, mp_obj_new_int(self->integer ? (int)self->x : self->x), PRINT_REPR);
    mp_print_str(print, ", y=");
    mp_obj_print_helper(print, mp_obj_new_int(self->integer ? (int)self->y : self->y), PRINT_REPR);
    mp_print_str(print, ")");
}

STATIC mp_obj_t vector_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    vector_mp_obj_t *self = mp_obj_malloc_with_finaliser(vector_mp_obj_t, &vector_mp_type);
    self->base.type = &vector_mp_type;
    self->integer = n_args == 3 ? mp_obj_is_true(args[2]) : false;
    self->x = mp_obj_get_float(args[0]);
    self->y = mp_obj_get_float(args[1]);
    return MP_OBJ_FROM_PTR(self);
}

STATIC mp_obj_t vector_mp_del(mp_obj_t self_in)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->x = 0;
    self->y = 0;
    self->integer = false;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vector_mp_del_obj, vector_mp_del);

STATIC mp_obj_t vector_mp_x(mp_obj_t self_in)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return self->integer ? mp_obj_new_int((int)self->x) : mp_obj_new_float(self->x);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vector_mp_x_obj, vector_mp_x);

STATIC mp_obj_t vector_mp_y(mp_obj_t self_in)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return self->integer ? mp_obj_new_int((int)self->y) : mp_obj_new_float(self->y);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(vector_mp_y_obj, vector_mp_y);

STATIC void vector_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributea
        if (attribute == MP_QSTR_x)
        {
            destination[0] = vector_mp_x(self_in);
        }
        else if (attribute == MP_QSTR_y)
        {
            destination[0] = vector_mp_y(self_in);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&vector_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
        if (attribute == MP_QSTR_x)
        {
            self->x = self->integer ? (float)mp_obj_get_int(destination[1]) : mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y)
        {
            self->y = self->integer ? (float)mp_obj_get_int(destination[1]) : mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

// Define CLASS locals
STATIC const mp_rom_map_elem_t vector_class_locals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&vector_mp_del_obj)},
    {MP_ROM_QSTR(MP_QSTR_x), MP_ROM_PTR(&vector_mp_x_obj)},
    {MP_ROM_QSTR(MP_QSTR_y), MP_ROM_PTR(&vector_mp_y_obj)},
};
STATIC MP_DEFINE_CONST_DICT(vector_class_locals, vector_class_locals_table);

// Define MODULE globals
STATIC const mp_rom_map_elem_t vector_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_vector)},
    {MP_ROM_QSTR(MP_QSTR_Vector), MP_ROM_PTR(&vector_mp_type)},
};
STATIC MP_DEFINE_CONST_DICT(vector_module_globals, vector_module_globals_table);

MP_DEFINE_CONST_OBJ_TYPE(
    vector_mp_type,
    MP_QSTR_Vector,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, vector_mp_print,
    make_new, vector_mp_make_new,
    attr, vector_mp_attr,
    locals_dict, &vector_class_locals);

// Define module
const mp_obj_module_t vector_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&vector_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_vector, vector_user_cmodule);