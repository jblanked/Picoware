#include "image_mp.h"
#include "engine/image.hpp"

static inline Image *image_get_context(image_mp_obj_t *self)
{
    return static_cast<Image *>(self->context);
}

void image_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    image_mp_obj_t *self = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Image *ctx = image_get_context(self);
    mp_print_str(print, "Image(size=(");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->size.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->size.y), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t image_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // Arguments: size (Vector), is_8bit (bool), data (optional), path (optional)
    mp_arg_check_num(n_args, n_kw, 2, 4, true);
    image_mp_obj_t *self = mp_obj_malloc_with_finaliser(image_mp_obj_t, &image_mp_type);
    self->base.type = &image_mp_type;

    // Extract constructor arguments (handles Python subclass wrappers)
    mp_obj_t native_size = mp_obj_cast_to_native_base(args[0], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_size == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for size"));
    vector_mp_obj_t *size_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_size));
    Vector size(size_vec->x, size_vec->y, size_vec->z, size_vec->integer);
    self->size_obj = vector_mp_init(size_vec->x, size_vec->y, size_vec->z, size_vec->integer);
    bool is_8bit = mp_obj_is_true(args[1]);
    const void *data = nullptr;
    const char *path = "";
    if (n_args > 2)
    {
        mp_buffer_info_t bufinfo;
        mp_get_buffer_raise(args[2], &bufinfo, MP_BUFFER_READ);
        data = bufinfo.buf;
    }
    if (n_args > 3)
    {
        path = mp_obj_str_get_str(args[3]);
    }

    self->context = new Image(size, is_8bit, data, path);
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t image_mp_del(mp_obj_t self_in)
{
    image_mp_obj_t *self = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Image *ctx = image_get_context(self);
    if (ctx)
        delete ctx;
    self->context = nullptr;
    self->freed = true;
    self->size_obj = MP_OBJ_NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(image_mp_del_obj, image_mp_del);

void image_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    image_mp_obj_t *self = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_size)
        {
            destination[0] = self->size_obj;
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&image_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_size)
        {
            image_mp_set_size(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t image_mp_set_size(mp_obj_t self_in, mp_obj_t size_obj)
{
    image_mp_obj_t *self = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Image *ctx = image_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(size_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *size_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->size.x = size_vec->x;
    ctx->size.y = size_vec->y;
    ctx->size.z = size_vec->z;
    ctx->size.integer = size_vec->integer;
    self->size_obj = size_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(image_mp_set_size_obj, image_mp_set_size);

static const mp_rom_map_elem_t image_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_size), MP_ROM_PTR(&image_mp_set_size_obj)},
};
static MP_DEFINE_CONST_DICT(image_mp_locals_dict, image_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t image_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Image,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)image_mp_make_new,
            (const void *)image_mp_print,
            (const void *)image_mp_attr,
            (const void *)&image_mp_locals_dict,
        },
    };
}