#include "camera_mp.h"
#include "engine_mp.h"

typedef struct
{
    mp_obj_base_t base;
    vector_mp_obj_t position;
    vector_mp_obj_t direction;
    vector_mp_obj_t plane;
    float height;
} camera_mp_obj_t;

const mp_obj_type_t camera_mp_type;

void camera_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    camera_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Camera(");
    mp_print_str(print, "position=(");
    mp_obj_print_helper(print, mp_obj_new_float(self->position.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->position.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->position.z), PRINT_REPR);
    mp_print_str(print, "), direction=(");
    mp_obj_print_helper(print, mp_obj_new_float(self->direction.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->direction.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->direction.z), PRINT_REPR);
    mp_print_str(print, "), plane=(");
    mp_obj_print_helper(print, mp_obj_new_float(self->plane.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->plane.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->plane.z), PRINT_REPR);
    mp_print_str(print, "), height=");
    mp_obj_print_helper(print, mp_obj_new_float(self->height), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t camera_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // position, direction, plane are Vector objects; height is a float
    mp_arg_check_num(n_args, n_kw, 0, 4, true);
    //
    camera_mp_obj_t *self = mp_obj_malloc_with_finaliser(camera_mp_obj_t, &camera_mp_type);
    self->base.type = &camera_mp_type;
    //
    self->position.base.type = &vector_mp_type;
    self->position.x = 0.0f;
    self->position.y = 0.0f;
    self->position.z = 0.0f;
    self->position.integer = false;
    self->direction.base.type = &vector_mp_type;
    self->direction.x = 1.0f;
    self->direction.y = 0.0f;
    self->direction.z = 0.0f;
    self->direction.integer = true;
    self->plane.base.type = &vector_mp_type;
    self->plane.x = 0.0f;
    self->plane.y = 0.66f;
    self->plane.z = 0.0f;
    self->plane.integer = false;
    self->height = 1.6f;
    //
    if (n_args > 0)
    {
        vector_mp_obj_t *position = MP_OBJ_TO_PTR(args[0]);
        self->position.x = position->x;
        self->position.y = position->y;
        self->position.z = position->z;
        self->position.integer = position->integer;
    }
    //
    if (n_args > 1)
    {
        vector_mp_obj_t *direction = MP_OBJ_TO_PTR(args[1]);
        self->direction.x = direction->x;
        self->direction.y = direction->y;
        self->direction.z = direction->z;
        self->direction.integer = direction->integer;
    }
    //
    if (n_args > 2)
    {
        vector_mp_obj_t *plane = MP_OBJ_TO_PTR(args[2]);
        self->plane.x = plane->x;
        self->plane.y = plane->y;
        self->plane.z = plane->z;
        self->plane.integer = plane->integer;
    }
    //
    if (n_args > 3)
    {
        self->height = mp_obj_get_float(args[3]);
    }
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t camera_mp_del(mp_obj_t self_in)
{
    camera_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->position.x = 0.0f;
    self->position.y = 0.0f;
    self->position.z = 0.0f;
    self->position.integer = true;
    self->direction.x = 1.0f;
    self->direction.y = 0.0f;
    self->direction.z = 0.0f;
    self->direction.integer = true;
    self->plane.x = 0.0f;
    self->plane.y = 0.66f;
    self->plane.z = 0.0f;
    self->plane.integer = false;
    self->height = 1.6f;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(camera_mp_del_obj, camera_mp_del);

void camera_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    camera_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_position)
        {
            destination[0] = MP_OBJ_FROM_PTR(&self->position);
        }
        else if (attribute == MP_QSTR_direction)
        {
            destination[0] = MP_OBJ_FROM_PTR(&self->direction);
        }
        else if (attribute == MP_QSTR_plane)
        {
            destination[0] = MP_OBJ_FROM_PTR(&self->plane);
        }
        else if (attribute == MP_QSTR_height)
        {
            destination[0] = mp_obj_new_float(self->height);
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
            vector_mp_obj_t *vec = MP_OBJ_TO_PTR(destination[1]);
            self->position.x = vec->x;
            self->position.y = vec->y;
            self->position.z = vec->z;
            self->position.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_direction)
        {
            vector_mp_obj_t *vec = MP_OBJ_TO_PTR(destination[1]);
            self->direction.x = vec->x;
            self->direction.y = vec->y;
            self->direction.z = vec->z;
            self->direction.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_plane)
        {
            vector_mp_obj_t *vec = MP_OBJ_TO_PTR(destination[1]);
            self->plane.x = vec->x;
            self->plane.y = vec->y;
            self->plane.z = vec->z;
            self->plane.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_height)
        {
            self->height = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

MP_DEFINE_CONST_OBJ_TYPE(
    camera_mp_type,
    MP_QSTR_Camera,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, camera_mp_print,
    make_new, camera_mp_make_new,
    attr, camera_mp_attr);