#include "vector_mp.h"
#include <math.h>

const mp_obj_type_t vector_mp_type;

mp_obj_t vector_mp_init(float x, float y, float z, bool integer)
{
    vector_mp_obj_t *vector_obj = mp_obj_malloc_with_finaliser(vector_mp_obj_t, &vector_mp_type);
    vector_obj->base.type = &vector_mp_type;
    vector_obj->x = x;
    vector_obj->y = y;
    vector_obj->z = z;
    vector_obj->integer = integer;
    return MP_OBJ_FROM_PTR(vector_obj);
}

void vector_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Vector(");
    mp_print_str(print, "x=");
    mp_obj_print_helper(print, self->integer ? mp_obj_new_int((int)self->x) : mp_obj_new_float(self->x), PRINT_REPR);
    mp_print_str(print, ", y=");
    mp_obj_print_helper(print, self->integer ? mp_obj_new_int((int)self->y) : mp_obj_new_float(self->y), PRINT_REPR);
    mp_print_str(print, ", z=");
    mp_obj_print_helper(print, self->integer ? mp_obj_new_int((int)self->z) : mp_obj_new_float(self->z), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t vector_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 4, false);
    vector_mp_obj_t *self = mp_obj_malloc_with_finaliser(vector_mp_obj_t, &vector_mp_type);
    self->base.type = &vector_mp_type;
    self->x = n_args > 0 ? mp_obj_get_float(args[0]) : 0.0f;
    self->y = n_args > 1 ? mp_obj_get_float(args[1]) : 0.0f;
    self->z = n_args > 2 ? mp_obj_get_float(args[2]) : 0.0f;
    self->integer = n_args > 3 ? mp_obj_is_true(args[3]) : false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t vector_mp_del(mp_obj_t self_in)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->x = 0;
    self->y = 0;
    self->z = 0;
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
        else if (attribute == MP_QSTR_z)
        {
            destination[0] = self->integer ? mp_obj_new_int((int)self->z) : mp_obj_new_float(self->z);
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
            self->x = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y)
        {
            self->y = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_z)
        {
            self->z = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t vector_mp_rotate_y(mp_obj_t self_in, mp_obj_t angle_in)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    float angle = mp_obj_get_float(angle_in);
    float cos_angle = cosf(angle);
    float sin_angle = sinf(angle);

    // return a new vector with the rotated coordinates
    return vector_mp_init(self->x * cos_angle - self->z * sin_angle, self->y, self->x * sin_angle + self->z * cos_angle, self->integer);
}
static MP_DEFINE_CONST_FUN_OBJ_2(vector_mp_rotate_y_obj, vector_mp_rotate_y);

mp_obj_t vector_mp_translate(size_t n_args, const mp_obj_t *args)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    float dx = mp_obj_get_float(args[1]);
    float dy = mp_obj_get_float(args[2]);
    float dz = mp_obj_get_float(args[3]);

    // return a new vector with the translated coordinates
    return vector_mp_init(self->x + dx, self->y + dy, self->z + dz, self->integer);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vector_mp_translate_obj, 4, 4, vector_mp_translate);

mp_obj_t vector_mp_scale(size_t n_args, const mp_obj_t *args)
{
    vector_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    float sx = mp_obj_get_float(args[1]);
    float sy = mp_obj_get_float(args[2]);
    float sz = mp_obj_get_float(args[3]);

    // return a new vector with the scaled coordinates
    return vector_mp_init(self->x * sx, self->y * sy, self->z * sz, self->integer);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vector_mp_scale_obj, 4, 4, vector_mp_scale);

static const mp_rom_map_elem_t vector_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_rotate_y), MP_ROM_PTR(&vector_mp_rotate_y_obj)},
    {MP_ROM_QSTR(MP_QSTR_translate), MP_ROM_PTR(&vector_mp_translate_obj)},
    {MP_ROM_QSTR(MP_QSTR_scale), MP_ROM_PTR(&vector_mp_scale_obj)},
};
static MP_DEFINE_CONST_DICT(vector_mp_locals_dict, vector_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    vector_mp_type,
    MP_QSTR_Vector,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, vector_mp_print,
    make_new, vector_mp_make_new,
    attr, vector_mp_attr,
    locals_dict, &vector_mp_locals_dict);

static const mp_rom_map_elem_t vector_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_vector)},
    {MP_ROM_QSTR(MP_QSTR_Vector), MP_ROM_PTR(&vector_mp_type)},
};
static MP_DEFINE_CONST_DICT(vector_module_globals, vector_module_globals_table);

// Define module
const mp_obj_module_t vector_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&vector_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_vector, vector_user_cmodule);