#include "billboard_mp.h"
#include "image_mp.h"
#include "pico-game-engine/engine/billboard.hpp"

static inline Billboard *billboard_get_context(billboard_mp_obj_t *self)
{
    return static_cast<Billboard *>(self->context);
}

void billboard_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    billboard_mp_obj_t *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Billboard *ctx = billboard_get_context(self);
    mp_print_str(print, "Billboard(");
    mp_print_str(print, "dirs=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->num_dirs), PRINT_REPR);
    mp_print_str(print, ", poses=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->num_poses), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t billboard_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // Arguments: dirs (optional), poses (optional)
    mp_arg_check_num(n_args, n_kw, 0, 2, false);
    billboard_mp_obj_t *self = mp_obj_malloc_with_finaliser(billboard_mp_obj_t, &billboard_mp_type);
    self->base.type = &billboard_mp_type;
    self->context = nullptr;

    int dirs = n_args > 0 ? mp_obj_get_int(args[0]) : 8;
    int poses = n_args > 1 ? mp_obj_get_int(args[1]) : 1;
    if (dirs < 1 || dirs > 8 || poses < 1 || poses > 8)
        mp_raise_ValueError(MP_ERROR_TEXT("counts must be 1..8"));
    Billboard *ctx = new Billboard();
    ctx->setCounts(dirs, poses);
    self->context = ctx;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t billboard_mp_del(mp_obj_t self_in)
{
    billboard_mp_obj_t *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self)
        return mp_const_none;
    Billboard *ctx = billboard_get_context(self);
    if (ctx)
        delete ctx;
    self->context = nullptr;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(billboard_mp_del_obj, billboard_mp_del);

void billboard_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    billboard_mp_obj_t *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self)
        return;

    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&billboard_mp_del_obj);
        }
    }
}

mp_obj_t billboard_mp_set_counts(mp_obj_t self_in, mp_obj_t d, mp_obj_t p)
{
    billboard_mp_obj_t *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Billboard *ctx = billboard_get_context(self);
    int dirs = mp_obj_get_int(d);
    int poses = mp_obj_get_int(p);
    if (dirs < 1 || dirs > 8 || poses < 1 || poses > 8)
        mp_raise_ValueError(MP_ERROR_TEXT("counts must be 1..8"));
    ctx->setCounts(dirs, poses);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(billboard_mp_set_counts_obj, billboard_mp_set_counts);

mp_obj_t billboard_mp_set_direction_pose(size_t, const mp_obj_t *args)
{
    billboard_mp_obj_t *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Billboard *bb = billboard_get_context(self);
    int dir = mp_obj_get_int(args[1]);
    int pose = mp_obj_get_int(args[2]);
    if (dir < 0 || dir >= bb->num_dirs || pose < 0 || pose >= bb->num_poses)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid direction or pose"));
    Image *copy = nullptr;
    if (args[3] != mp_const_none)
    {
        mp_obj_t native = mp_obj_cast_to_native_base(args[3], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Image"));
        image_mp_obj_t *image = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native));
        if (image->freed || !image->context)
            mp_raise_ValueError(MP_ERROR_TEXT("expected live image with pixels"));
        Image *source = static_cast<Image *>(image->context);
        if (!(source->size.x >= 1 && source->size.x <= 1024 && source->size.y >= 1 && source->size.y <= 1024) ||
            uint16_t(source->size.x) != source->size.x || uint16_t(source->size.y) != source->size.y)
            mp_raise_ValueError(MP_ERROR_TEXT("expected RGB332 image"));
        copy = source->copyOwned();
        if (!copy)
            mp_raise_ValueError(MP_ERROR_TEXT("image has no readable pixel data"));
        if (!copy->getPixels())
        {
            delete copy;
            mp_raise_ValueError(MP_ERROR_TEXT("expected RGB332 image"));
        }
    }
    if (!bb->setDirectionPose(dir, pose, copy))
    {
        delete copy;
        mp_raise_ValueError(MP_ERROR_TEXT("invalid image"));
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(billboard_mp_set_direction_pose_obj, 4, 4, billboard_mp_set_direction_pose);

static const mp_rom_map_elem_t billboard_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_counts), MP_ROM_PTR(&billboard_mp_set_counts_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_direction_pose), MP_ROM_PTR(&billboard_mp_set_direction_pose_obj)},
};
static MP_DEFINE_CONST_DICT(billboard_mp_locals_dict, billboard_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t billboard_mp_type = {
        .base = {&mp_type_type},
        .name = MP_QSTR_Billboard,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)billboard_mp_make_new,
            (const void *)billboard_mp_print,
            (const void *)billboard_mp_attr,
            (const void *)&billboard_mp_locals_dict,
        }};
}