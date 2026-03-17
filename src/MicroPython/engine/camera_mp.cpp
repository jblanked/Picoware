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
        self->position_obj = args[0];
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
        self->direction_obj = args[1];
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
        self->plane_obj = args[2];
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
    if (ctx)
        delete ctx;
    self->context = nullptr;
    self->freed = true;
    self->position_obj = MP_OBJ_NULL;
    self->direction_obj = MP_OBJ_NULL;
    self->plane_obj = MP_OBJ_NULL;
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
    if (destination[0] == MP_OBJ_NULL)
    {
        Camera *ctx = camera_get_context(self);
        // Load attributes
        switch (attribute)
        {
        case MP_QSTR_position:
            destination[0] = self->position_obj;
            break;
        case MP_QSTR_direction:
            destination[0] = self->direction_obj;
            break;
        case MP_QSTR_plane:
            destination[0] = self->plane_obj;
            break;
        case MP_QSTR_height:
            destination[0] = mp_obj_new_float(ctx->height);
            break;
        case MP_QSTR_distance:
            destination[0] = mp_obj_new_float(ctx->distance);
            break;
        case MP_QSTR_perspective:
            destination[0] = mp_obj_new_int(ctx->perspective);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&camera_mp_del_obj);
            break;
        default:
            return; // Fail
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        switch (attribute)
        {
        case MP_QSTR_position:
            camera_mp_set_position(self_in, destination[1]);
            break;
        case MP_QSTR_direction:
            camera_mp_set_direction(self_in, destination[1]);
            break;
        case MP_QSTR_plane:
            camera_mp_set_plane(self_in, destination[1]);
            break;
        case MP_QSTR_height:
            camera_mp_set_height(self_in, destination[1]);
            break;
        case MP_QSTR_distance:
            camera_mp_set_distance(self_in, destination[1]);
            break;
        case MP_QSTR_perspective:
            camera_mp_set_perspective(self_in, destination[1]);
            break;
        default:
            return; // Fail
        };
        destination[0] = MP_OBJ_NULL;
    }
}

mp_obj_t camera_mp_set_position(mp_obj_t self_in, mp_obj_t position_obj)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Camera *ctx = camera_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(position_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->position.x = vec->x;
    ctx->position.y = vec->y;
    ctx->position.z = vec->z;
    ctx->position.integer = vec->integer;
    self->position_obj = position_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(camera_mp_set_position_obj, camera_mp_set_position);

mp_obj_t camera_mp_set_direction(mp_obj_t self_in, mp_obj_t direction_obj)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Camera *ctx = camera_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(direction_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->direction.x = vec->x;
    ctx->direction.y = vec->y;
    ctx->direction.z = vec->z;
    ctx->direction.integer = vec->integer;
    self->direction_obj = direction_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(camera_mp_set_direction_obj, camera_mp_set_direction);

mp_obj_t camera_mp_set_plane(mp_obj_t self_in, mp_obj_t plane_obj)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Camera *ctx = camera_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(plane_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->plane.x = vec->x;
    ctx->plane.y = vec->y;
    ctx->plane.z = vec->z;
    ctx->plane.integer = vec->integer;
    self->plane_obj = plane_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(camera_mp_set_plane_obj, camera_mp_set_plane);

mp_obj_t camera_mp_set_height(mp_obj_t self_in, mp_obj_t height_obj)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Camera *ctx = camera_get_context(self);
    ctx->height = mp_obj_get_float(height_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(camera_mp_set_height_obj, camera_mp_set_height);

mp_obj_t camera_mp_set_distance(mp_obj_t self_in, mp_obj_t distance_obj)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Camera *ctx = camera_get_context(self);
    ctx->distance = mp_obj_get_float(distance_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(camera_mp_set_distance_obj, camera_mp_set_distance);

mp_obj_t camera_mp_set_perspective(mp_obj_t self_in, mp_obj_t perspective_obj)
{
    camera_mp_obj_t *self = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Camera *ctx = camera_get_context(self);
    ctx->perspective = static_cast<CameraPerspective>(mp_obj_get_int(perspective_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(camera_mp_set_perspective_obj, camera_mp_set_perspective);

static const mp_rom_map_elem_t camera_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_position), MP_ROM_PTR(&camera_mp_set_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_direction), MP_ROM_PTR(&camera_mp_set_direction_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_plane), MP_ROM_PTR(&camera_mp_set_plane_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_height), MP_ROM_PTR(&camera_mp_set_height_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_distance), MP_ROM_PTR(&camera_mp_set_distance_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_perspective), MP_ROM_PTR(&camera_mp_set_perspective_obj)},
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