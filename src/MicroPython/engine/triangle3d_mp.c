#include "triangle3d_mp.h"
#include "engine_mp.h"

const mp_obj_type_t triangle3d_mp_type;

void triangle3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    triangle3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Triangle3D(");
    mp_print_str(print, "v1=(");
    mp_obj_print_helper(print, mp_obj_new_float(self->x1), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->y1), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->z1), PRINT_REPR);
    mp_print_str(print, "), v2=(");
    mp_obj_print_helper(print, mp_obj_new_float(self->x2), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->y2), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->z2), PRINT_REPR);
    mp_print_str(print, "), v3=(");
    mp_obj_print_helper(print, mp_obj_new_float(self->x3), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->y3), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(self->z3), PRINT_REPR);
    mp_print_str(print, "), visible=");
    mp_obj_print_helper(print, self->visible ? MP_OBJ_NEW_SMALL_INT(1) : MP_OBJ_NEW_SMALL_INT(0), PRINT_REPR);
    mp_print_str(print, ", distance=");
    mp_obj_print_helper(print, mp_obj_new_float(self->distance), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t triangle3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 9, false);
    triangle3d_mp_obj_t *self = mp_obj_malloc_with_finaliser(triangle3d_mp_obj_t, &triangle3d_mp_type);
    self->base.type = &triangle3d_mp_type;
    self->x1 = n_args > 0 ? mp_obj_get_float(args[0]) : 0.0f;
    self->y1 = n_args > 1 ? mp_obj_get_float(args[1]) : 0.0f;
    self->z1 = n_args > 2 ? mp_obj_get_float(args[2]) : 0.0f;
    self->x2 = n_args > 3 ? mp_obj_get_float(args[3]) : 0.0f;
    self->y2 = n_args > 4 ? mp_obj_get_float(args[4]) : 0.0f;
    self->z2 = n_args > 5 ? mp_obj_get_float(args[5]) : 0.0f;
    self->x3 = n_args > 6 ? mp_obj_get_float(args[6]) : 0.0f;
    self->y3 = n_args > 7 ? mp_obj_get_float(args[7]) : 0.0f;
    self->z3 = n_args > 8 ? mp_obj_get_float(args[8]) : 0.0f;
    self->visible = true;
    self->distance = 0.0f;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t triangle3d_mp_del(mp_obj_t self_in)
{
    triangle3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->x1 = 0.0f;
    self->y1 = 0.0f;
    self->z1 = 0.0f;
    self->x2 = 0.0f;
    self->y2 = 0.0f;
    self->z2 = 0.0f;
    self->x3 = 0.0f;
    self->y3 = 0.0f;
    self->z3 = 0.0f;
    self->visible = false;
    self->distance = 0.0f;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(triangle3d_mp_del_obj, triangle3d_mp_del);

void triangle3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    triangle3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_x1)
        {
            destination[0] = mp_obj_new_float(self->x1);
        }
        else if (attribute == MP_QSTR_y1)
        {
            destination[0] = mp_obj_new_float(self->y1);
        }
        else if (attribute == MP_QSTR_z1)
        {
            destination[0] = mp_obj_new_float(self->z1);
        }
        else if (attribute == MP_QSTR_x2)
        {
            destination[0] = mp_obj_new_float(self->x2);
        }
        else if (attribute == MP_QSTR_y2)
        {
            destination[0] = mp_obj_new_float(self->y2);
        }
        else if (attribute == MP_QSTR_z2)
        {
            destination[0] = mp_obj_new_float(self->z2);
        }
        else if (attribute == MP_QSTR_x3)
        {
            destination[0] = mp_obj_new_float(self->x3);
        }
        else if (attribute == MP_QSTR_y3)
        {
            destination[0] = mp_obj_new_float(self->y3);
        }
        else if (attribute == MP_QSTR_z3)
        {
            destination[0] = mp_obj_new_float(self->z3);
        }
        else if (attribute == MP_QSTR_visible)
        {
            destination[0] = self->visible ? mp_const_true : mp_const_false;
        }
        else if (attribute == MP_QSTR_distance)
        {
            destination[0] = mp_obj_new_float(self->distance);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&triangle3d_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_x1)
        {
            self->x1 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y1)
        {
            self->y1 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_z1)
        {
            self->z1 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_x2)
        {
            self->x2 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y2)
        {
            self->y2 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_z2)
        {
            self->z2 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_x3)
        {
            self->x3 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y3)
        {
            self->y3 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_z3)
        {
            self->z3 = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_visible)
        {
            self->visible = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_distance)
        {
            self->distance = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t triangle3d_mp_center(mp_obj_t self_in)
{
    triangle3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    // return a new vector with the center coordinates
    vector_mp_obj_t *result = mp_obj_malloc_with_finaliser(vector_mp_obj_t, &vector_mp_type);
    result->base.type = &vector_mp_type;
    result->integer = false;
    result->x = (self->x1 + self->x2 + self->x3) / 3.0f;
    result->y = (self->y1 + self->y2 + self->y3) / 3.0f;
    result->z = (self->z1 + self->z2 + self->z3) / 3.0f;
    return MP_OBJ_FROM_PTR(result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(triangle3d_mp_center_obj, triangle3d_mp_center);

mp_obj_t triangle3d_mp_vertices(mp_obj_t self_in)
{
    triangle3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t vertices_list[3];
    for (int i = 0; i < 3; i++)
    {
        vector_mp_obj_t *vertex = mp_obj_malloc_with_finaliser(vector_mp_obj_t, &vector_mp_type);
        vertex->base.type = &vector_mp_type;
        vertex->integer = false;
        if (i == 0)
        {
            vertex->x = self->x1;
            vertex->y = self->y1;
            vertex->z = self->z1;
        }
        else if (i == 1)
        {
            vertex->x = self->x2;
            vertex->y = self->y2;
            vertex->z = self->z2;
        }
        else if (i == 2)
        {
            vertex->x = self->x3;
            vertex->y = self->y3;
            vertex->z = self->z3;
        }
        vertices_list[i] = MP_OBJ_FROM_PTR(vertex);
    }
    return mp_obj_new_list(3, vertices_list);
}
static MP_DEFINE_CONST_FUN_OBJ_1(triangle3d_mp_vertices_obj, triangle3d_mp_vertices);

mp_obj_t triangle3d_mp_is_facing_camera(mp_obj_t self_in, mp_obj_t camera_pos_vector)
{
    triangle3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    vector_mp_obj_t *camera_pos = MP_OBJ_TO_PTR(camera_pos_vector);

    // Calculate triangle normal using cross product
    vector_mp_obj_t vector1 = {.base = {.type = &vector_mp_type}, .x = self->x1, .y = self->y1, .z = self->z1};
    vector_mp_obj_t vector2 = {.base = {.type = &vector_mp_type}, .x = self->x2, .y = self->y2, .z = self->z2};
    vector_mp_obj_t vector3 = {.base = {.type = &vector_mp_type}, .x = self->x3, .y = self->y3, .z = self->z3};
    vector_mp_obj_t vec1 = {.base = {.type = &vector_mp_type}, .x = vector2.x - vector1.x, .y = vector2.y - vector1.y, .z = vector2.z - vector1.z};
    vector_mp_obj_t vec2 = {.base = {.type = &vector_mp_type}, .x = vector3.x - vector1.x, .y = vector3.y - vector1.y, .z = vector3.z - vector1.z};

    // Cross product to get normal (right-hand rule)
    vector_mp_obj_t normal = {
        .base = {.type = &vector_mp_type},
        .x = vec1.y * vec2.z - vec1.z * vec2.y,
        .y = vec1.z * vec2.x - vec1.x * vec2.z,
        .z = vec1.x * vec2.y - vec1.y * vec2.x};

    // Vector from triangle center to camera
    vector_mp_obj_t *center = MP_OBJ_TO_PTR(triangle3d_mp_center(self_in));
    vector_mp_obj_t to_camera = {
        .base = {.type = &vector_mp_type},
        .x = camera_pos->x - center->x,
        .y = 0.5 - center->y,          // camera height
        .z = camera_pos->y - center->z // camera_pos.y is Z in world space
    };

    // Dot product - if positive, triangle faces camera
    float dot_product = normal.x * to_camera.x + normal.y * to_camera.y + normal.z * to_camera.z;
    return mp_obj_new_bool(dot_product > 0.0f);
}
static MP_DEFINE_CONST_FUN_OBJ_2(triangle3d_mp_is_facing_camera_obj, triangle3d_mp_is_facing_camera);

static const mp_rom_map_elem_t triangle3d_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_center), MP_ROM_PTR(&triangle3d_mp_center_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_vertices), MP_ROM_PTR(&triangle3d_mp_vertices_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_facing_camera), MP_ROM_PTR(&triangle3d_mp_is_facing_camera_obj)},
};
static MP_DEFINE_CONST_DICT(triangle3d_mp_locals_dict, triangle3d_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    triangle3d_mp_type,
    MP_QSTR_Triangle3D,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, triangle3d_mp_print,
    make_new, triangle3d_mp_make_new,
    attr, triangle3d_mp_attr,
    locals_dict, &triangle3d_mp_locals_dict);