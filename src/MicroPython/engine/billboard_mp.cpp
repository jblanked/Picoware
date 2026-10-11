#include "billboard_mp.h"
extern "C" {
#include "py/objtuple.h"
}
#include "pico-game-engine/engine/billboard.hpp"

static mp_obj_t make_new(const mp_obj_type_t *, size_t n, size_t kw, const mp_obj_t *args)
{
    mp_arg_check_num(n, kw, 0, 2, false);
    int dirs = n > 0 ? mp_obj_get_int(args[0]) : 8;
    int poses = n > 1 ? mp_obj_get_int(args[1]) : 1;
    if (dirs < 1 || dirs > 8 || poses < 1 || poses > 8)
        mp_raise_ValueError(MP_ERROR_TEXT("counts must be 1..8"));
    auto *self = mp_obj_malloc_with_finaliser(billboard_mp_obj_t, &billboard_mp_type);
    self->context = nullptr;
    for (auto &image : self->images) image = MP_OBJ_NULL;
    self->context = new Billboard();
    static_cast<Billboard *>(self->context)->setCounts(dirs, poses);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t release(mp_obj_t obj)
{
    auto *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(obj));
    delete static_cast<Billboard *>(self->context);
    self->context = nullptr;
    for (auto &image : self->images) image = MP_OBJ_NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(release_obj, release);

static Billboard *context(mp_obj_t obj)
{
    auto *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(obj));
    if (!self->context) mp_raise_ValueError(MP_ERROR_TEXT("freed Billboard"));
    return static_cast<Billboard *>(self->context);
}

static mp_obj_t set_counts(mp_obj_t obj, mp_obj_t d, mp_obj_t p)
{
    int dirs = mp_obj_get_int(d), poses = mp_obj_get_int(p);
    if (dirs < 1 || dirs > 8 || poses < 1 || poses > 8)
        mp_raise_ValueError(MP_ERROR_TEXT("counts must be 1..8"));
    context(obj)->setCounts(dirs, poses);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(set_counts_obj, set_counts);

static mp_obj_t set_direction_pose(size_t, const mp_obj_t *args)
{
    auto *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    Billboard *bb = context(args[0]);
    int dir = mp_obj_get_int(args[1]), pose = mp_obj_get_int(args[2]);
    if (dir < 0 || dir >= bb->num_dirs || pose < 0 || pose >= bb->num_poses)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid direction or pose"));
    Image *copy = nullptr;
    mp_obj_t root = mp_const_none;
    if (args[3] != mp_const_none)
    {
        mp_obj_t native = mp_obj_cast_to_native_base(args[3], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native == MP_OBJ_NULL) mp_raise_TypeError(MP_ERROR_TEXT("expected Image"));
        auto *image = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native));
        if (image->freed || !image->context || image->data_obj == MP_OBJ_NULL)
            mp_raise_ValueError(MP_ERROR_TEXT("expected live image with pixels"));
        auto *source = static_cast<Image *>(image->context);
        if (!source->getPixels() || !(source->size.x >= 1 && source->size.x <= 1024 &&
            source->size.y >= 1 && source->size.y <= 1024) ||
            uint16_t(source->size.x) != source->size.x || uint16_t(source->size.y) != source->size.y)
            mp_raise_ValueError(MP_ERROR_TEXT("expected RGB332 image"));
        mp_buffer_info_t pixels;
        mp_get_buffer_raise(image->data_obj, &pixels, MP_BUFFER_READ);
        if (pixels.len != size_t(source->size.x) * size_t(source->size.y))
            mp_raise_ValueError(MP_ERROR_TEXT("incorrect pixel length"));
        mp_obj_t pixels_obj = mp_obj_is_type(image->data_obj, &mp_type_bytes) ? image->data_obj
            : mp_obj_new_bytes(static_cast<const byte *>(pixels.buf), pixels.len);
        mp_obj_t roots[] = {args[3], pixels_obj};
        root = mp_obj_new_tuple(2, roots);
        mp_get_buffer_raise(pixels_obj, &pixels, MP_BUFFER_READ);
        copy = new Image(source->size, pixels.buf, "", source->has_mask ? source->mask : nullptr);
    }
    if (!bb->setDirectionPose(dir, pose, copy))
    {
        delete copy;
        mp_raise_ValueError(MP_ERROR_TEXT("invalid image"));
    }
    self->images[dir * 8 + pose] = root;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(set_direction_pose_obj, 4, 4, set_direction_pose);

static mp_obj_t view_for_facing(mp_obj_t obj, mp_obj_t angle, mp_obj_t pose)
{
    auto *self = static_cast<billboard_mp_obj_t *>(MP_OBJ_TO_PTR(obj));
    Billboard *bb = context(obj);
    Image *image = bb->viewForFacing(mp_obj_get_float(angle), mp_obj_get_int(pose));
    if (!image) return mp_const_none;
    for (int d = 0; d < bb->num_dirs; ++d)
        for (int p = 0; p < bb->num_poses; ++p)
            if (bb->dirs[d][p] == image)
                return static_cast<mp_obj_tuple_t *>(MP_OBJ_TO_PTR(self->images[d * 8 + p]))->items[0];
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(view_for_facing_obj, view_for_facing);

static const mp_rom_map_elem_t locals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&release_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_counts), MP_ROM_PTR(&set_counts_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_direction_pose), MP_ROM_PTR(&set_direction_pose_obj)},
    {MP_ROM_QSTR(MP_QSTR_view_for_facing), MP_ROM_PTR(&view_for_facing_obj)},
};
static MP_DEFINE_CONST_DICT(locals, locals_table);
extern "C" {
    const mp_obj_type_t billboard_mp_type = {
        .base = {&mp_type_type}, .name = MP_QSTR_Billboard,
        .slot_index_make_new = 1, .slot_index_locals_dict = 2,
        .slots = {(const void *)make_new, (const void *)&locals},
    };
}
