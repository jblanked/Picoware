#include "image_mp.h"
#include <math.h>

extern "C" {
#include "py/objtuple.h"
}
#include "pico-game-engine/engine/image.hpp"

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
    self->context = nullptr;
    self->billboard_pixels_obj = self->billboard_masks_obj = MP_OBJ_NULL;
    self->billboard_pixels = self->billboard_masks = nullptr;
    self->freed = false;

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
    if (!self)
        return mp_const_none;
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
    self->billboard_pixels_obj = self->billboard_masks_obj = MP_OBJ_NULL;
    self->billboard_pixels = self->billboard_masks = nullptr;
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
        else if (attribute == MP_QSTR_frame_count)
        {
            destination[0] = mp_obj_new_int_from_uint(image_get_context(self)->getBillboardFrameCount());
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&image_mp_del_obj);
        }
        else
        {
            destination[1] = MP_OBJ_SENTINEL;
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
    if (ctx->isBillboard())
        mp_raise_ValueError(MP_ERROR_TEXT("billboard image size is fixed"));
    ctx->size.x = size_vec->x;
    ctx->size.y = size_vec->y;
    ctx->size.z = size_vec->z;
    ctx->size.integer = size_vec->integer;
    self->size_obj = size_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(image_mp_set_size_obj, image_mp_set_size);

static mp_obj_t image_mp_billboard_buffer(mp_obj_t input, size_t expected)
{
    mp_buffer_info_t buffer;
    mp_get_buffer_raise(input, &buffer, MP_BUFFER_READ);
    if (buffer.len != expected)
        mp_raise_ValueError(MP_ERROR_TEXT("incorrect billboard buffer length"));
    return mp_obj_is_type(input, &mp_type_bytes)
        ? input : mp_obj_new_bytes(static_cast<const byte *>(buffer.buf), buffer.len);
}

static mp_obj_t image_mp_set_billboard(size_t n_args, const mp_obj_t *args)
{
    image_mp_obj_t *self = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    if (self->freed)
        mp_raise_ValueError(MP_ERROR_TEXT("Image has been released"));
    Image *ctx = image_get_context(self);
    const float width = ctx->size.x, height = ctx->size.y;
    const mp_int_t frames = n_args == 4 ? mp_obj_get_int(args[3]) : 1;
    if (!isfinite(width) || !isfinite(height) || width < 1 || height < 1 ||
        width > 1024 || height > 1024 || floorf(width) != width || floorf(height) != height)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid billboard dimensions"));
    const size_t pixel_count = size_t(width) * size_t(height);
    if (frames < 1 || uint64_t(frames) > UINT32_MAX ||
        size_t(frames) > SIZE_MAX / Image::billboardViewCount / (pixel_count * 2))
        mp_raise_ValueError(MP_ERROR_TEXT("invalid billboard frame count"));
    const size_t views = size_t(frames) * Image::billboardViewCount;
    const size_t mask_bytes = (pixel_count + 7) / 8;
    mp_obj_t pixel_root, mask_root;
    const uint8_t **pixels = nullptr, **masks = nullptr;
    const bool segmented = mp_obj_is_type(args[1], &mp_type_tuple) || mp_obj_is_type(args[1], &mp_type_list);
    Image candidate(ctx->size, false);
    if (segmented)
    {
        size_t pixel_views, mask_views;
        mp_obj_t *pixel_items, *mask_items;
        mp_obj_get_array(args[1], &pixel_views, &pixel_items);
        mp_obj_get_array(args[2], &mask_views, &mask_items);
        if (pixel_views != views || mask_views != views || views > SIZE_MAX / sizeof(void *))
            mp_raise_ValueError(MP_ERROR_TEXT("incorrect billboard view count"));
        pixel_root = mp_obj_new_tuple(views, nullptr);
        mask_root = mp_obj_new_tuple(views, nullptr);
        pixels = m_new(const uint8_t *, views);
        masks = m_new(const uint8_t *, views);
        mp_obj_tuple_t *pixel_roots = static_cast<mp_obj_tuple_t *>(MP_OBJ_TO_PTR(pixel_root));
        mp_obj_tuple_t *mask_roots = static_cast<mp_obj_tuple_t *>(MP_OBJ_TO_PTR(mask_root));
        for (size_t i = 0; i < views; ++i)
        {
            pixel_roots->items[i] = image_mp_billboard_buffer(pixel_items[i], pixel_count * 2);
            mask_roots->items[i] = image_mp_billboard_buffer(mask_items[i], mask_bytes);
            mp_buffer_info_t pixel_buffer, mask_buffer;
            mp_get_buffer_raise(pixel_roots->items[i], &pixel_buffer, MP_BUFFER_READ);
            mp_get_buffer_raise(mask_roots->items[i], &mask_buffer, MP_BUFFER_READ);
            pixels[i] = static_cast<const uint8_t *>(pixel_buffer.buf);
            masks[i] = static_cast<const uint8_t *>(mask_buffer.buf);
        }
        candidate = Image(ctx->size, false, pixels[0]);
        if (!candidate.setBillboardFrames(pixels, masks, uint32_t(frames)))
            mp_raise_ValueError(MP_ERROR_TEXT("invalid billboard image"));
    }
    else
    {
        pixel_root = image_mp_billboard_buffer(args[1], pixel_count * 2 * views);
        mask_root = image_mp_billboard_buffer(args[2], mask_bytes * views);
        mp_buffer_info_t pixel_buffer, mask_buffer;
        mp_get_buffer_raise(pixel_root, &pixel_buffer, MP_BUFFER_READ);
        mp_get_buffer_raise(mask_root, &mask_buffer, MP_BUFFER_READ);
        candidate = Image(ctx->size, false, pixel_buffer.buf);
        if (!candidate.setBillboard(static_cast<const uint8_t *>(mask_buffer.buf), uint32_t(frames)))
            mp_raise_ValueError(MP_ERROR_TEXT("invalid billboard image"));
    }
    *ctx = candidate;
    self->billboard_pixels_obj = pixel_root;
    self->billboard_masks_obj = mask_root;
    self->billboard_pixels = pixels;
    self->billboard_masks = masks;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(image_mp_set_billboard_obj, 3, 4, image_mp_set_billboard);

static mp_obj_t image_mp_view_index(size_t n_args, const mp_obj_t *args)
{
    (void)n_args;
    return mp_obj_new_int(Image::getBillboardView(mp_obj_get_float(args[1]), mp_obj_get_float(args[2]),
                                                mp_obj_get_float(args[3]), mp_obj_get_float(args[4])));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(image_mp_view_index_obj, 5, 5, image_mp_view_index);

static const mp_rom_map_elem_t image_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_billboard), MP_ROM_PTR(&image_mp_set_billboard_obj)},
    {MP_ROM_QSTR(MP_QSTR_view_index), MP_ROM_PTR(&image_mp_view_index_obj)},
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