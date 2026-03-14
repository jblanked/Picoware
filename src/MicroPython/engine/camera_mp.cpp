#include "camera_mp.h"
#include "engine/camera.hpp"

static inline Camera *camera_get_context(camera_mp_obj_t *self)
{
    return static_cast<Camera *>(self->context);
}

void camera_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Camera *ctx = camera_get_context(self);
    mp_print_str(print, "Camera(");
    mp_print_str(print, "position=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->position.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->position.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->position.z), PRINT_REPR);
    mp_print_str(print, "), direction=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->direction.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->direction.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->direction.z), PRINT_REPR);
    mp_print_str(print, "), plane=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->plane.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->plane.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->plane.z), PRINT_REPR);
    mp_print_str(print, "), height=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->height), PRINT_REPR);
    mp_print_str(print, "), distance=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->distance), PRINT_REPR);
    mp_print_str(print, ", perspective=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->perspective), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t camera_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // position, direction, plane are Vector objects; height, distance are floats; perspective is an int
    mp_arg_check_num(n_args, n_kw, 0, 6, true);
    //
    camera_mp_obj_t *self = mp_obj_malloc_with_finaliser(camera_mp_obj_t, &camera_mp_type);
    self->base.type = &camera_mp_type;
    //
    self->context = new Camera();
    Camera *ctx = camera_get_context(self);

    if (n_args > 0)
    {
        mp_obj_t native_vec = mp_obj_cast_to_native_base(args[0], MP_OBJ_FROM_PTR(&vector_mp_type));
        if (native_vec == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for position"));
        vector_mp_obj_t *position = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
        ctx->position.x = position->x;
        ctx->position.y = position->y;
        ctx->position.z = position->z;
        ctx->position.integer = position->integer;
    }
    if (n_args > 1)
    {
        mp_obj_t native_vec = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&vector_mp_type));
        if (native_vec == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for direction"));
        vector_mp_obj_t *direction = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
        ctx->direction.x = direction->x;
        ctx->direction.y = direction->y;
        ctx->direction.z = direction->z;
        ctx->direction.integer = direction->integer;
    }
    if (n_args > 2)
    {
        mp_obj_t native_vec = mp_obj_cast_to_native_base(args[2], MP_OBJ_FROM_PTR(&vector_mp_type));
        if (native_vec == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for plane"));
        vector_mp_obj_t *plane = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
        ctx->plane.x = plane->x;
        ctx->plane.y = plane->y;
        ctx->plane.z = plane->z;
        ctx->plane.integer = plane->integer;
    }
    if (n_args > 3)
    {
        ctx->height = mp_obj_get_float(args[3]);
    }
    if (n_args > 4)
    {
        ctx->distance = mp_obj_get_float(args[4]);
    }
    if (n_args > 5)
    {
        ctx->perspective = static_cast<CameraPerspective>(mp_obj_get_int(args[5]));
    }
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t camera_mp_del(mp_obj_t self_in)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Camera *ctx = camera_get_context(self);
    delete ctx;
    self->context = nullptr;
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(camera_mp_del_obj, camera_mp_del);

void camera_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    Camera *ctx = camera_get_context(self);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes — return new Vector MicroPython objects from Camera fields
        if (attribute == MP_QSTR_position)
        {
            destination[0] = vector_mp_init(ctx->position.x, ctx->position.y, ctx->position.z, ctx->position.integer);
        }
        else if (attribute == MP_QSTR_direction)
        {
            destination[0] = vector_mp_init(ctx->direction.x, ctx->direction.y, ctx->direction.z, ctx->direction.integer);
        }
        else if (attribute == MP_QSTR_plane)
        {
            destination[0] = vector_mp_init(ctx->plane.x, ctx->plane.y, ctx->plane.z, ctx->plane.integer);
        }
        else if (attribute == MP_QSTR_height)
        {
            destination[0] = mp_obj_new_float(ctx->height);
        }
        else if (attribute == MP_QSTR_distance)
        {
            destination[0] = mp_obj_new_float(ctx->distance);
        }
        else if (attribute == MP_QSTR_perspective)
        {
            destination[0] = mp_obj_new_int(ctx->perspective);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&camera_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_position)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->position.x = vec->x;
            ctx->position.y = vec->y;
            ctx->position.z = vec->z;
            ctx->position.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_direction)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->direction.x = vec->x;
            ctx->direction.y = vec->y;
            ctx->direction.z = vec->z;
            ctx->direction.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_plane)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->plane.x = vec->x;
            ctx->plane.y = vec->y;
            ctx->plane.z = vec->z;
            ctx->plane.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_height)
        {
            ctx->height = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_distance)
        {
            ctx->distance = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_perspective)
        {
            ctx->perspective = static_cast<CameraPerspective>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
    }
}

static const mp_rom_map_elem_t camera_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_CAMERA_FIRST_PERSON), MP_ROM_INT(CAMERA_FIRST_PERSON)},
    {MP_ROM_QSTR(MP_QSTR_CAMERA_THIRD_PERSON), MP_ROM_INT(CAMERA_THIRD_PERSON)},
};
static MP_DEFINE_CONST_DICT(camera_mp_locals_dict, camera_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t camera_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Camera,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)camera_mp_make_new,
            (const void *)camera_mp_print,
            (const void *)camera_mp_attr,
            (const void *)&camera_mp_locals_dict,
        },
    };
}