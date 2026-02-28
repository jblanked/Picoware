#include "sprite3d_mp.h"
#include "triangle3d_mp.h"
#include "engine_mp.h"

const mp_obj_type_t sprite3d_mp_type;

mp_obj_t sprite3d_mp_init(void)
{
    sprite3d_mp_obj_t *sprite3d = mp_obj_malloc_with_finaliser(sprite3d_mp_obj_t, &sprite3d_mp_type);
    sprite3d->base.type = &sprite3d_mp_type;
    sprite3d->triangles = mp_obj_new_list(0, NULL);
    sprite3d->triangle_count = 0;
    sprite3d->pos = vector_mp_init(0.0f, 0.0f, 0.0f, false);
    sprite3d->rotation_y = 0.0f;
    sprite3d->scale_factor = 1.0f;
    sprite3d->type = SPRITE_3D_CUSTOM;
    sprite3d->active = true;
    sprite3d->color = 0x0000; // default black
    sprite3d->freed = false;
    return MP_OBJ_FROM_PTR(sprite3d);
}

void sprite3d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    sprite3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Sprite3D(");
    mp_print_str(print, "type=");
    mp_obj_print_helper(print, MP_OBJ_NEW_SMALL_INT(self->type), PRINT_REPR);
    mp_print_str(print, ", pos=");
    mp_obj_print_helper(print, self->pos, PRINT_REPR);
    mp_print_str(print, ", rotation_y=");
    mp_obj_print_helper(print, mp_obj_new_float(self->rotation_y), PRINT_REPR);
    mp_print_str(print, ", scale_factor=");
    mp_obj_print_helper(print, mp_obj_new_float(self->scale_factor), PRINT_REPR);
    mp_print_str(print, ", active=");
    mp_obj_print_helper(print, self->active ? MP_OBJ_NEW_SMALL_INT(1) : MP_OBJ_NEW_SMALL_INT(0), PRINT_REPR);
    mp_print_str(print, ", color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->color), PRINT_REPR);
    mp_print_str(print, ", triangle_count=");
    mp_obj_print_helper(print, mp_obj_new_int(self->triangle_count), PRINT_REPR);
    mp_print_str(print, ", triangles=[");
    mp_obj_print_helper(print, self->triangles, PRINT_REPR);
    mp_print_str(print, "]");
    mp_print_str(print, ")");
}

mp_obj_t sprite3d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    return sprite3d_mp_init();
}

mp_obj_t sprite3d_mp_del(mp_obj_t self_in)
{
    sprite3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }
    if (self->triangles != MP_OBJ_NULL)
    {
        m_del_obj(mp_obj_list_t, MP_OBJ_TO_PTR(self->triangles));
        self->triangles = MP_OBJ_NULL;
    }
    self->triangle_count = 0;
    if (self->pos != MP_OBJ_NULL)
    {
        m_del_obj(vector_mp_obj_t, MP_OBJ_TO_PTR(self->pos));
        self->pos = MP_OBJ_NULL;
    }
    self->rotation_y = 0.0f;
    self->scale_factor = 1.0f;
    self->type = SPRITE_3D_CUSTOM;
    self->active = false;
    self->color = 0x0000;
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sprite3d_mp_del_obj, sprite3d_mp_del);

void sprite3d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    sprite3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // load attributes
        if (attribute == MP_QSTR_triangles)
        {
            destination[0] = self->triangles;
        }
        else if (attribute == MP_QSTR_pos)
        {
            destination[0] = self->pos;
        }
        else if (attribute == MP_QSTR_rotation_y)
        {
            destination[0] = mp_obj_new_float(self->rotation_y);
        }
        else if (attribute == MP_QSTR_scale_factor)
        {
            destination[0] = mp_obj_new_float(self->scale_factor);
        }
        else if (attribute == MP_QSTR_type)
        {
            destination[0] = mp_obj_new_int(self->type);
        }
        else if (attribute == MP_QSTR_active)
        {
            destination[0] = mp_obj_new_bool(self->active);
        }
        else if (attribute == MP_QSTR_color)
        {
            destination[0] = mp_obj_new_int(self->color);
        }
        else if (attribute == MP_QSTR_triangle_count)
        {
            destination[0] = mp_obj_new_int(self->triangle_count);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&sprite3d_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // store attributes
        if (attribute == MP_QSTR_pos)
        {
            self->pos = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_rotation_y)
        {
            self->rotation_y = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_scale_factor)
        {
            self->scale_factor = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_type)
        {
            self->type = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_active)
        {
            self->active = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_color)
        {
            self->color = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t sprite3d_mp_add_triangle(mp_obj_t self_in, mp_obj_t triangle_in)
{
    sprite3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_list_append(self->triangles, triangle_in);
    self->triangle_count++;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(sprite3d_mp_add_triangle_obj, sprite3d_mp_add_triangle);

mp_obj_t sprite3d_mp_clear_triangles(mp_obj_t self_in)
{
    sprite3d_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_list_t *triangles_list = MP_OBJ_TO_PTR(self->triangles);
    triangles_list->len = 0;
    self->triangle_count = 0;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(sprite3d_mp_clear_triangles_obj, sprite3d_mp_clear_triangles);

static const mp_rom_map_elem_t sprite3d_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_add_triangle), MP_ROM_PTR(&sprite3d_mp_add_triangle_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_triangles), MP_ROM_PTR(&sprite3d_mp_clear_triangles_obj)},
};
static MP_DEFINE_CONST_DICT(sprite3d_mp_locals_dict, sprite3d_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    sprite3d_mp_type,
    MP_QSTR_Sprite3D,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, sprite3d_mp_print,
    make_new, sprite3d_mp_make_new,
    attr, sprite3d_mp_attr,
    locals_dict, &sprite3d_mp_locals_dict);
