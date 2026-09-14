#include "layer2d_mp.h"

#include "game_mp.h"
#include "pico-game-engine/engine/game.hpp"
#include "pico-game-engine/engine/layer2d.hpp"

extern "C" {
#include "py/stream.h"
}

static MP_DEFINE_CONST_FUN_OBJ_1(layer2d_mp_del_obj, layer2d_mp_del);

static inline Layer2D *layer2d_get_context(layer2d_mp_obj_t *self)
{
    return static_cast<Layer2D *>(self->context);
}

void layer2d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    if (destination[0] == MP_OBJ_NULL && attribute == MP_QSTR___del__)
    {
        destination[0] = MP_OBJ_FROM_PTR(&layer2d_mp_del_obj);
    }
    else if (destination[0] == MP_OBJ_NULL)
    {
        destination[1] = MP_OBJ_SENTINEL;
    }
}

mp_obj_t layer2d_mp_circle(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 5, 5, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    layer2d_get_context(self)->circle(static_cast<int16_t>(mp_obj_get_int(args[1])), static_cast<int16_t>(mp_obj_get_int(args[2])), static_cast<uint16_t>(mp_obj_get_int(args[3])), static_cast<uint16_t>(mp_obj_get_int(args[4])));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_circle_obj, 5, 5, layer2d_mp_circle);

mp_obj_t layer2d_mp_clear(mp_obj_t self_in)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self->freed)
    {
        layer2d_get_context(self)->clear();
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(layer2d_mp_clear_obj, layer2d_mp_clear);

mp_obj_t layer2d_mp_del(mp_obj_t self_in)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self == nullptr || self->freed)
    {
        return mp_const_none;
    }
    Layer2D *ctx = layer2d_get_context(self);
    delete ctx;
    self->context = nullptr;
    self->freed = true;
    return mp_const_none;
}
mp_obj_t layer2d_mp_fill_circle(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 5, 5, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    layer2d_get_context(self)->fillCircle(static_cast<int16_t>(mp_obj_get_int(args[1])), static_cast<int16_t>(mp_obj_get_int(args[2])), static_cast<uint16_t>(mp_obj_get_int(args[3])), static_cast<uint16_t>(mp_obj_get_int(args[4])));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_fill_circle_obj, 5, 5, layer2d_mp_fill_circle);

mp_obj_t layer2d_mp_fill_rect(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 6, 6, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    layer2d_get_context(self)->fillRectangle(static_cast<int16_t>(mp_obj_get_int(args[1])), static_cast<int16_t>(mp_obj_get_int(args[2])), static_cast<uint16_t>(mp_obj_get_int(args[3])), static_cast<uint16_t>(mp_obj_get_int(args[4])), static_cast<uint16_t>(mp_obj_get_int(args[5])));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_fill_rect_obj, 6, 6, layer2d_mp_fill_rect);

mp_obj_t layer2d_mp_get_command_count(mp_obj_t self_in)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    return mp_obj_new_int(layer2d_get_context(self)->getCommandCount());
}
static MP_DEFINE_CONST_FUN_OBJ_1(layer2d_mp_get_command_count_obj, layer2d_mp_get_command_count);

mp_obj_t layer2d_mp_get_pixel_bytes(mp_obj_t self_in)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    return mp_obj_new_int_from_uint(layer2d_get_context(self)->getPixelBytes());
}
static MP_DEFINE_CONST_FUN_OBJ_1(layer2d_mp_get_pixel_bytes_obj, layer2d_mp_get_pixel_bytes);

mp_obj_t layer2d_mp_image(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 6, 6, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    mp_buffer_info_t buffer;
    mp_get_buffer_raise(args[5], &buffer, MP_BUFFER_READ);
    layer2d_get_context(self)->image(static_cast<int16_t>(mp_obj_get_int(args[1])), static_cast<int16_t>(mp_obj_get_int(args[2])), static_cast<uint16_t>(mp_obj_get_int(args[3])), static_cast<uint16_t>(mp_obj_get_int(args[4])), static_cast<const uint8_t *>(buffer.buf), buffer.len);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_image_obj, 6, 6, layer2d_mp_image);

mp_obj_t layer2d_mp_image_opaque(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 6, 6, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    mp_buffer_info_t buffer;
    mp_get_buffer_raise(args[5], &buffer, MP_BUFFER_READ);
    layer2d_get_context(self)->imageOpaque(static_cast<int16_t>(mp_obj_get_int(args[1])), static_cast<int16_t>(mp_obj_get_int(args[2])), static_cast<uint16_t>(mp_obj_get_int(args[3])), static_cast<uint16_t>(mp_obj_get_int(args[4])), static_cast<const uint8_t *>(buffer.buf), buffer.len);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_image_opaque_obj, 6, 6, layer2d_mp_image_opaque);

static mp_obj_t layer2d_mp_image_packed(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 5, 5, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    mp_int_t x = mp_obj_get_int(args[1]), y = mp_obj_get_int(args[2]);
    mp_int_t length = mp_obj_get_int(args[4]);
    if (self->freed || x < -32768 || x > 32767 || y < -32768 || y > 32767
        || length < 2 || length > 32768)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid packed image arguments"));
    mp_get_stream_raise(args[3], MP_STREAM_OP_READ);
    Layer2D *layer = layer2d_get_context(self);
    uint8_t *record = layer->allocatePacked(length);
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        layer->discardPacked(record);
        nlr_jump(nlr.ret_val);
    }
    int error = 0;
    mp_uint_t received = mp_stream_read_exactly(args[3], record, length, &error);
    if (error)
        mp_raise_OSError(error);
    if (received != static_cast<mp_uint_t>(length))
        mp_raise_ValueError(MP_ERROR_TEXT("truncated packed image"));
    if (self->freed || !layer2d_get_context(self)->imagePacked(x, y, record, length))
        mp_raise_ValueError(MP_ERROR_TEXT("invalid packed image record"));
    // Ownership has transferred. No Python allocation after the commit.
    nlr_pop();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_image_packed_obj, 5, 5, layer2d_mp_image_packed);

mp_obj_t layer2d_mp_line(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 6, 6, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    layer2d_get_context(self)->line(static_cast<int16_t>(mp_obj_get_int(args[1])), static_cast<int16_t>(mp_obj_get_int(args[2])), static_cast<int16_t>(mp_obj_get_int(args[3])), static_cast<int16_t>(mp_obj_get_int(args[4])), static_cast<uint16_t>(mp_obj_get_int(args[5])));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_line_obj, 6, 6, layer2d_mp_line);

mp_obj_t layer2d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    layer2d_mp_obj_t *self = mp_obj_malloc_with_finaliser(layer2d_mp_obj_t, &layer2d_mp_type);
    self->base.type = &layer2d_mp_type;
    self->context = new Layer2D();
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

void layer2d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    Layer2D *ctx = layer2d_get_context(self);
    mp_print_str(print, "Layer2D(command_count=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->getCommandCount()), PRINT_REPR);
    mp_print_str(print, ", pixel_bytes=");
    mp_obj_print_helper(print, mp_obj_new_int_from_uint(ctx->getPixelBytes()), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t layer2d_mp_render(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 2, 6, false);
    mp_obj_t self_in = args[0];
    mp_obj_t game_in = args[1];
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    mp_obj_t native_game = mp_obj_cast_to_native_base(game_in, MP_OBJ_FROM_PTR(&game_mp_type));
    if (native_game == MP_OBJ_NULL)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected Game"));
    }
    game_mp_obj_t *game = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(native_game));
    if (self->freed || game->freed || game->context == nullptr)
    {
        return mp_const_none;
    }
    Game *game_context = static_cast<Game *>(game->context);
    if (n_args == 2)
    {
        layer2d_get_context(self)->render(game_context->draw);
    }
    else
    {
        int16_t left = static_cast<int16_t>(mp_obj_get_int(args[2]));
        int16_t top = static_cast<int16_t>(mp_obj_get_int(args[3]));
        int16_t right = static_cast<int16_t>(mp_obj_get_int(args[4]));
        int16_t bottom = static_cast<int16_t>(mp_obj_get_int(args[5]));
        layer2d_get_context(self)->render(game_context->draw, left, top, right, bottom);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_render_obj, 2, 6, layer2d_mp_render);

static mp_obj_t layer2d_mp_reserve_commands(mp_obj_t self_in, mp_obj_t capacity_in)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    mp_int_t capacity = mp_obj_get_int(capacity_in);
    if (self->freed || capacity < 1 || capacity > 32768
        || !layer2d_get_context(self)->reserveCommands(static_cast<uint16_t>(capacity)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid command reserve"));
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(layer2d_mp_reserve_commands_obj, layer2d_mp_reserve_commands);

static mp_obj_t layer2d_mp_reserve_packed(mp_obj_t self_in, mp_obj_t capacity_in)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    mp_int_t capacity = mp_obj_get_int(capacity_in);
    if (self->freed || capacity < 2 || capacity > 32768
        || !layer2d_get_context(self)->reservePacked(static_cast<size_t>(capacity)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid packed image reserve"));
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(layer2d_mp_reserve_packed_obj, layer2d_mp_reserve_packed);

mp_obj_t layer2d_mp_text(size_t n_args, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, 0, 5, 6, false);
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    const char *value = mp_obj_str_get_str(args[3]);
    FontSize font = n_args == 6 ? static_cast<FontSize>(mp_obj_get_int(args[5])) : ENGINE_FONT_DEFAULT;
    layer2d_get_context(self)->text(static_cast<int16_t>(mp_obj_get_int(args[1])), static_cast<int16_t>(mp_obj_get_int(args[2])), value, static_cast<uint16_t>(mp_obj_get_int(args[4])), font);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(layer2d_mp_text_obj, 5, 6, layer2d_mp_text);

static mp_obj_t layer2d_mp_translate(mp_obj_t self_in, mp_obj_t dx_in, mp_obj_t dy_in)
{
    layer2d_mp_obj_t *self = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    mp_int_t dx = mp_obj_get_int(dx_in), dy = mp_obj_get_int(dy_in);
    if (self->freed)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("layer has been released"));
    }
    if (dx < -65535 || dx > 65535 || dy < -65535 || dy > 65535 ||
        !layer2d_get_context(self)->translate(static_cast<int32_t>(dx), static_cast<int32_t>(dy)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("layer translation out of range"));
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(layer2d_mp_translate_obj, layer2d_mp_translate);

static const mp_rom_map_elem_t layer2d_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&layer2d_mp_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_circle), MP_ROM_PTR(&layer2d_mp_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_circle), MP_ROM_PTR(&layer2d_mp_fill_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_rect), MP_ROM_PTR(&layer2d_mp_fill_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_command_count), MP_ROM_PTR(&layer2d_mp_get_command_count_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_pixel_bytes), MP_ROM_PTR(&layer2d_mp_get_pixel_bytes_obj)},
    {MP_ROM_QSTR(MP_QSTR_image), MP_ROM_PTR(&layer2d_mp_image_obj)},
    {MP_ROM_QSTR(MP_QSTR_image_opaque), MP_ROM_PTR(&layer2d_mp_image_opaque_obj)},
    {MP_ROM_QSTR(MP_QSTR_image_packed), MP_ROM_PTR(&layer2d_mp_image_packed_obj)},
    {MP_ROM_QSTR(MP_QSTR_line), MP_ROM_PTR(&layer2d_mp_line_obj)},
    {MP_ROM_QSTR(MP_QSTR_render), MP_ROM_PTR(&layer2d_mp_render_obj)},
    {MP_ROM_QSTR(MP_QSTR_reserve_commands), MP_ROM_PTR(&layer2d_mp_reserve_commands_obj)},
    {MP_ROM_QSTR(MP_QSTR_reserve_packed), MP_ROM_PTR(&layer2d_mp_reserve_packed_obj)},
    {MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&layer2d_mp_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_translate), MP_ROM_PTR(&layer2d_mp_translate_obj)},
};
static MP_DEFINE_CONST_DICT(layer2d_mp_locals_dict, layer2d_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t layer2d_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Layer2D,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)layer2d_mp_make_new,
            (const void *)layer2d_mp_print,
            (const void *)layer2d_mp_attr,
            (const void *)&layer2d_mp_locals_dict,
        },
    };
}
