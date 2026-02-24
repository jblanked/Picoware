#include "vector_mp.h"

const mp_obj_type_t vector_mp_type;

void vector_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
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

mp_obj_t vector_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    vector_mp_obj_t *self = mp_obj_malloc_with_finaliser(vector_mp_obj_t, &vector_mp_type);
    self->base.type = &vector_mp_type;
    self->integer = n_args == 3 ? mp_obj_is_true(args[2]) : false;
    self->x = mp_obj_get_float(args[0]);
    self->y = mp_obj_get_float(args[1]);
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t vector_mp_del(mp_obj_t self_in)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->x = 0;
    self->y = 0;
    self->integer = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(vector_mp_del_obj, vector_mp_del);

void vector_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_x)
        {
            destination[0] = self->integer ? mp_obj_new_int((int)self->x) : mp_obj_new_float(self->x);
        }
        else if (attribute == MP_QSTR_y)
        {
            destination[0] = self->integer ? mp_obj_new_int((int)self->y) : mp_obj_new_float(self->y);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&vector_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
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

static const mp_rom_map_elem_t vector_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_vector)},
    {MP_ROM_QSTR(MP_QSTR_Vector), MP_ROM_PTR(&vector_mp_type)},
};
static MP_DEFINE_CONST_DICT(vector_module_globals, vector_module_globals_table);

MP_DEFINE_CONST_OBJ_TYPE(
    vector_mp_type,
    MP_QSTR_Vector,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, vector_mp_print,
    make_new, vector_mp_make_new,
    attr, vector_mp_attr);

// Define module
const mp_obj_module_t vector_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&vector_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_vector, vector_user_cmodule);