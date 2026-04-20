#include "ghouls_mp.h"
#include "Ghouls/src/game.hpp"

static inline GhoulsGame *ghouls_get_context(ghouls_mp_obj_t *self)
{
    return static_cast<GhoulsGame *>(self->game);
}

void ghouls_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    ghouls_mp_obj_t *self = static_cast<ghouls_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    GhoulsGame *ctx = ghouls_get_context(self);
    (void)ctx;
    mp_print_str(print, "GhoulsGame()");
}

mp_obj_t ghouls_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    ghouls_mp_obj_t *self = mp_obj_malloc_with_finaliser(ghouls_mp_obj_t, &ghouls_mp_type);
    self->base.type = &ghouls_mp_type;
    self->freed = false;
    const char *username = mp_obj_str_get_str(args[0]);
    const char *password = mp_obj_str_get_str(args[1]);
    bool soundEnabled = true;
    if (n_args == 3)
    {
        soundEnabled = mp_obj_is_true(args[2]);
    }
    self->game = new GhoulsGame(username, password, soundEnabled);
    GhoulsGame *ctx = ghouls_get_context(self);
    ctx->initDraw();
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t ghouls_mp_del(mp_obj_t self_in)
{
    ghouls_mp_obj_t *self = static_cast<ghouls_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    GhoulsGame *ctx = ghouls_get_context(self);
    if (ctx)
    {
        delete ctx;
        ctx = nullptr;
    }
    self->game = nullptr;
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(ghouls_mp_del_obj, ghouls_mp_del);

void ghouls_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    ghouls_mp_obj_t *self = static_cast<ghouls_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_is_active)
        {
            GhoulsGame *ctx = ghouls_get_context(self);
            destination[0] = mp_obj_new_bool(ctx ? ctx->isActive() : false);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&ghouls_mp_del_obj);
        }
    }
}

mp_obj_t ghouls_mp_update_draw(mp_obj_t self_in)
{
    ghouls_mp_obj_t *self = static_cast<ghouls_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    GhoulsGame *ctx = ghouls_get_context(self);
    if (ctx)
        ctx->updateDraw();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(ghouls_mp_update_draw_obj, ghouls_mp_update_draw);

mp_obj_t ghouls_mp_update_input(mp_obj_t self_in, mp_obj_t button_pressed_obj)
{
    ghouls_mp_obj_t *self = static_cast<ghouls_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    GhoulsGame *ctx = ghouls_get_context(self);
    if (ctx)
    {
        int button_pressed = mp_obj_get_int(button_pressed_obj);
        ctx->updateInput(button_pressed, false);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(ghouls_mp_update_input_obj, ghouls_mp_update_input);

static const mp_rom_map_elem_t ghouls_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_update_draw), MP_ROM_PTR(&ghouls_mp_update_draw_obj)},
    {MP_ROM_QSTR(MP_QSTR_update_input), MP_ROM_PTR(&ghouls_mp_update_input_obj)},
};
static MP_DEFINE_CONST_DICT(ghouls_mp_locals_dict, ghouls_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t ghouls_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Ghouls,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)ghouls_mp_make_new,
            (const void *)ghouls_mp_print,
            (const void *)ghouls_mp_attr,
            (const void *)&ghouls_mp_locals_dict,
        },
    };
}

static const mp_rom_map_elem_t ghouls_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ghouls)},
    {MP_ROM_QSTR(MP_QSTR_Ghouls), MP_ROM_PTR(&ghouls_mp_type)},
};
static MP_DEFINE_CONST_DICT(ghouls_mp_globals, ghouls_mp_globals_table);

extern "C"
{
    extern const mp_obj_module_t ghouls_mp_cmodule = {
        .base = {&mp_type_module},
        .globals = (mp_obj_dict_t *)&ghouls_mp_globals,
    };

    MP_REGISTER_MODULE(MP_QSTR_ghouls, ghouls_mp_cmodule);
}
