#include "framebuffer2d_mp.h"

#include "game_mp.h"
#include "layer2d_mp.h"
#include "pico-game-engine/engine/framebuffer2d.hpp"
#include "pico-game-engine/engine/game.hpp"
#include "pico-game-engine/engine/layer2d.hpp"

static mp_obj_t framebuffer2d_mp_del(mp_obj_t self_in);
static MP_DEFINE_CONST_FUN_OBJ_1(framebuffer2d_mp_del_obj, framebuffer2d_mp_del);

static inline FrameBuffer2D *framebuffer2d_get_context(framebuffer2d_mp_obj_t *self)
{
    return static_cast<FrameBuffer2D *>(self->context);
}

static inline Layer2D *framebuffer2d_get_layer(mp_obj_t layer_in)
{
    mp_obj_t native_layer = mp_obj_cast_to_native_base(layer_in, MP_OBJ_FROM_PTR(&layer2d_mp_type));
    if (native_layer == MP_OBJ_NULL)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected Layer2D"));
    }
    layer2d_mp_obj_t *layer = static_cast<layer2d_mp_obj_t *>(MP_OBJ_TO_PTR(native_layer));
    if (layer->freed || layer->context == nullptr)
    {
        return nullptr;
    }
    return static_cast<Layer2D *>(layer->context);
}

static void framebuffer2d_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    framebuffer2d_mp_obj_t *self = static_cast<framebuffer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    if (destination[0] == MP_OBJ_NULL && attribute == MP_QSTR___del__)
    {
        destination[0] = MP_OBJ_FROM_PTR(&framebuffer2d_mp_del_obj);
    }
    else if (destination[0] == MP_OBJ_NULL)
    {
        destination[1] = MP_OBJ_SENTINEL;
    }
}

static mp_obj_t framebuffer2d_mp_clear(mp_obj_t self_in, mp_obj_t color_in)
{
    framebuffer2d_mp_obj_t *self = static_cast<framebuffer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self->freed)
    {
        framebuffer2d_get_context(self)->clear(static_cast<uint16_t>(mp_obj_get_int(color_in)));
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(framebuffer2d_mp_clear_obj, framebuffer2d_mp_clear);

static mp_obj_t framebuffer2d_mp_del(mp_obj_t self_in)
{
    framebuffer2d_mp_obj_t *self = static_cast<framebuffer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self == nullptr || self->freed)
    {
        return mp_const_none;
    }
    delete framebuffer2d_get_context(self);
    self->context = nullptr;
    self->freed = true;
    return mp_const_none;
}

static mp_obj_t framebuffer2d_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 2, false);
    framebuffer2d_mp_obj_t *self = mp_obj_malloc_with_finaliser(framebuffer2d_mp_obj_t, &framebuffer2d_mp_type);
    self->base.type = &framebuffer2d_mp_type;
    self->context = new FrameBuffer2D(static_cast<uint16_t>(mp_obj_get_int(args[0])), static_cast<uint16_t>(mp_obj_get_int(args[1])));
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t framebuffer2d_mp_present(mp_obj_t self_in, mp_obj_t game_in)
{
    framebuffer2d_mp_obj_t *self = static_cast<framebuffer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    mp_obj_t native_game = mp_obj_cast_to_native_base(game_in, MP_OBJ_FROM_PTR(&game_mp_type));
    if (native_game == MP_OBJ_NULL)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected Game"));
    }
    game_mp_obj_t *game = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(native_game));
    if (!self->freed && !game->freed && game->context != nullptr)
    {
        Game *game_context = static_cast<Game *>(game->context);
        framebuffer2d_get_context(self)->blit(game_context->draw);
        game_context->draw->swap();
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(framebuffer2d_mp_present_obj, framebuffer2d_mp_present);

static void framebuffer2d_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    framebuffer2d_mp_obj_t *self = static_cast<framebuffer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self->freed)
    {
        mp_print_str(print, "FrameBuffer2D");
    }
}

static mp_obj_t framebuffer2d_mp_render(mp_obj_t self_in, mp_obj_t layer_in)
{
    framebuffer2d_mp_obj_t *self = static_cast<framebuffer2d_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self->freed)
    {
        Layer2D *layer = framebuffer2d_get_layer(layer_in);
        if (layer != nullptr)
        {
            framebuffer2d_get_context(self)->render(*layer);
        }
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(framebuffer2d_mp_render_obj, framebuffer2d_mp_render);

static const mp_rom_map_elem_t framebuffer2d_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&framebuffer2d_mp_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_present), MP_ROM_PTR(&framebuffer2d_mp_present_obj)},
    {MP_ROM_QSTR(MP_QSTR_render), MP_ROM_PTR(&framebuffer2d_mp_render_obj)},
};
static MP_DEFINE_CONST_DICT(framebuffer2d_mp_locals_dict, framebuffer2d_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t framebuffer2d_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_FrameBuffer2D,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)framebuffer2d_mp_make_new,
            (const void *)framebuffer2d_mp_print,
            (const void *)framebuffer2d_mp_attr,
            (const void *)&framebuffer2d_mp_locals_dict,
        },
    };
}
