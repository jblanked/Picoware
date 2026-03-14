#include "triangle3d_mp.h"
#include "engine/triangle3d.hpp"

static inline Triangle3D *triangle3d_get_context(triangle3d_mp_obj_t *self)
{
    return static_cast<Triangle3D *>(self->context);
}

void triangle3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    triangle3d_mp_obj_t *self = static_cast<triangle3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Triangle3D *ctx = triangle3d_get_context(self);
    mp_print_str(print, "Triangle3D(");
    mp_print_str(print, "v1=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->x1), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->y1), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->z1), PRINT_REPR);
    mp_print_str(print, "), v2=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->x2), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->y2), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->z2), PRINT_REPR);
    mp_print_str(print, "), v3=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->x3), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->y3), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->z3), PRINT_REPR);
    mp_print_str(print, "), visible=");
    mp_obj_print_helper(print, ctx->visible ? mp_const_true : mp_const_false, PRINT_REPR);
    mp_print_str(print, ", distance=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->distance), PRINT_REPR);
    mp_print_str(print, ", color=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->color), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t triangle3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 10, false);
    triangle3d_mp_obj_t *self = mp_obj_malloc_with_finaliser(triangle3d_mp_obj_t, &triangle3d_mp_type);
    self->base.type = &triangle3d_mp_type;
    self->context = new Triangle3D();
    Triangle3D *ctx = triangle3d_get_context(self);
    ctx->x1 = n_args > 0 ? mp_obj_get_float(args[0]) : 0.0f;
    ctx->y1 = n_args > 1 ? mp_obj_get_float(args[1]) : 0.0f;
    ctx->z1 = n_args > 2 ? mp_obj_get_float(args[2]) : 0.0f;
    ctx->x2 = n_args > 3 ? mp_obj_get_float(args[3]) : 0.0f;
    ctx->y2 = n_args > 4 ? mp_obj_get_float(args[4]) : 0.0f;
    ctx->z2 = n_args > 5 ? mp_obj_get_float(args[5]) : 0.0f;
    ctx->x3 = n_args > 6 ? mp_obj_get_float(args[6]) : 0.0f;
    ctx->y3 = n_args > 7 ? mp_obj_get_float(args[7]) : 0.0f;
    ctx->z3 = n_args > 8 ? mp_obj_get_float(args[8]) : 0.0f;
    ctx->color = n_args > 9 ? static_cast<uint16_t>(mp_obj_get_int(args[9])) : 0x0000;
    ctx->visible = true;
    ctx->distance = 0.0f;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t triangle3d_mp_del(mp_obj_t self_in)
{
    triangle3d_mp_obj_t *self = static_cast<triangle3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Triangle3D *ctx = triangle3d_get_context(self);
    delete ctx;
    self->context = nullptr;
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(triangle3d_mp_del_obj, triangle3d_mp_del);

void triangle3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    triangle3d_mp_obj_t *self = static_cast<triangle3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        Triangle3D *ctx = triangle3d_get_context(self);
        if (attribute == MP_QSTR_x1)
        {
            destination[0] = mp_obj_new_float(ctx->x1);
        }
        else if (attribute == MP_QSTR_y1)
        {
            destination[0] = mp_obj_new_float(ctx->y1);
        }
        else if (attribute == MP_QSTR_z1)
        {
            destination[0] = mp_obj_new_float(ctx->z1);
        }
        else if (attribute == MP_QSTR_x2)
        {
            destination[0] = mp_obj_new_float(ctx->x2);
        }
        else if (attribute == MP_QSTR_y2)
        {
            destination[0] = mp_obj_new_float(ctx->y2);
        }
        else if (attribute == MP_QSTR_z2)
        {
            destination[0] = mp_obj_new_float(ctx->z2);
        }
        else if (attribute == MP_QSTR_x3)
        {
            destination[0] = mp_obj_new_float(ctx->x3);
        }
        else if (attribute == MP_QSTR_y3)
        {
            destination[0] = mp_obj_new_float(ctx->y3);
        }
        else if (attribute == MP_QSTR_z3)
        {
            destination[0] = mp_obj_new_float(ctx->z3);
        }
        else if (attribute == MP_QSTR_visible)
        {
            destination[0] = ctx->visible ? mp_const_true : mp_const_false;
        }
        else if (attribute == MP_QSTR_distance)
        {
            destination[0] = mp_obj_new_float(ctx->distance);
        }
        else if (attribute == MP_QSTR_color)
        {
            destination[0] = mp_obj_new_int(ctx->color);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&triangle3d_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        Triangle3D *ctx = triangle3d_get_context(self);
        if (attribute == MP_QSTR_x1)
        {
            ctx->x1 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y1)
        {
            ctx->y1 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_z1)
        {
            ctx->z1 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_x2)
        {
            ctx->x2 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y2)
        {
            ctx->y2 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_z2)
        {
            ctx->z2 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_x3)
        {
            ctx->x3 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y3)
        {
            ctx->y3 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_z3)
        {
            ctx->z3 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_visible)
        {
            ctx->visible = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_distance)
        {
            ctx->distance = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_color)
        {
            ctx->color = static_cast<uint16_t>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t triangle3d_mp_center(mp_obj_t self_in)
{
    triangle3d_mp_obj_t *self = static_cast<triangle3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Triangle3D *ctx = triangle3d_get_context(self);
    Vector is_center = ctx->getCenter();
    // return a new vector with the center coordinates
    return vector_mp_init(is_center.x, is_center.y, is_center.z, false);
}
static MP_DEFINE_CONST_FUN_OBJ_1(triangle3d_mp_center_obj, triangle3d_mp_center);

mp_obj_t triangle3d_mp_is_facing_camera(mp_obj_t self_in, mp_obj_t camera_pos_vector)
{
    triangle3d_mp_obj_t *self = static_cast<triangle3d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Triangle3D *ctx = triangle3d_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(camera_pos_vector, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    return mp_obj_new_bool(ctx->isFacingCamera(Vector(vec->x, vec->y, vec->z, vec->integer)));
}
static MP_DEFINE_CONST_FUN_OBJ_2(triangle3d_mp_is_facing_camera_obj, triangle3d_mp_is_facing_camera);

static const mp_rom_map_elem_t triangle3d_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_center), MP_ROM_PTR(&triangle3d_mp_center_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_facing_camera), MP_ROM_PTR(&triangle3d_mp_is_facing_camera_obj)},
};
static MP_DEFINE_CONST_DICT(triangle3d_mp_locals_dict, triangle3d_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t triangle3d_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Triangle3D,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)triangle3d_mp_make_new,
            (const void *)triangle3d_mp_print,
            (const void *)triangle3d_mp_attr,
            (const void *)&triangle3d_mp_locals_dict,
        },
    };
}