#include "pico_gta_mp.h"
#include "PicoGTA/src/game.hpp"

static inline PicoGTA *pico_gta_get_context(pico_gta_mp_obj_t *self)
{
    return static_cast<PicoGTA *>(self->game);
}

void pico_gta_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    pico_gta_mp_obj_t *self = static_cast<pico_gta_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    PicoGTA *ctx = pico_gta_get_context(self);
    (void)ctx;
    mp_print_str(print, "PicoGTA()");
}

mp_obj_t pico_gta_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    pico_gta_mp_obj_t *self = mp_obj_malloc_with_finaliser(pico_gta_mp_obj_t, &pico_gta_mp_type);
    self->base.type = &pico_gta_mp_type;
    self->freed = false;
    const char *username = mp_obj_str_get_str(args[0]);
    const char *password = mp_obj_str_get_str(args[1]);
    self->game = new PicoGTA(username, password);
    PicoGTA *ctx = pico_gta_get_context(self);
    ctx->initDraw();
#ifdef PICOCALC
    keyboard_game_mode(true);
#endif
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t pico_gta_mp_del(mp_obj_t self_in)
{
    pico_gta_mp_obj_t *self = static_cast<pico_gta_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self || self->freed)
    {
        return mp_const_none;
    }
    PicoGTA *ctx = pico_gta_get_context(self);
    if (ctx)
    {
        delete ctx;
        ctx = nullptr;
    }
    self->game = nullptr;
    self->freed = true;
#ifdef PICOCALC
    keyboard_game_mode(false);
#endif
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(pico_gta_mp_del_obj, pico_gta_mp_del);

void pico_gta_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    if (destination[0] != MP_OBJ_NULL)
        return;
    pico_gta_mp_obj_t *self = static_cast<pico_gta_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self)
        return;
    if (attribute == MP_QSTR___del__)
    {
        destination[0] = MP_OBJ_FROM_PTR(&pico_gta_mp_del_obj);
        destination[1] = self_in;
    }
    else if (attribute == MP_QSTR_is_active)
    {
        PicoGTA *ctx = self->freed ? nullptr : pico_gta_get_context(self);
        destination[0] = mp_obj_new_bool(ctx ? ctx->isActive() : false);
    }
    else
    {
        // Let MicroPython resolve methods such as run from the locals dictionary.
        destination[1] = MP_OBJ_SENTINEL;
    }
}

mp_obj_t pico_gta_mp_run(mp_obj_t self_in)
{
    pico_gta_mp_obj_t *self = static_cast<pico_gta_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (!self || self->freed)
    {
        return mp_const_none;
    }
    PicoGTA *ctx = pico_gta_get_context(self);
    if (ctx)
        ctx->run();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(pico_gta_mp_run_obj, pico_gta_mp_run);

static const mp_rom_map_elem_t pico_gta_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&pico_gta_mp_run_obj)},
};
static MP_DEFINE_CONST_DICT(pico_gta_mp_locals_dict, pico_gta_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t pico_gta_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_PicoGTA,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)pico_gta_mp_make_new,
            (const void *)pico_gta_mp_print,
            (const void *)pico_gta_mp_attr,
            (const void *)&pico_gta_mp_locals_dict,
        },
    };
}

static const mp_rom_map_elem_t pico_gta_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pico_gta)},
    {MP_ROM_QSTR(MP_QSTR_PicoGTA), MP_ROM_PTR(&pico_gta_mp_type)},
};
static MP_DEFINE_CONST_DICT(pico_gta_mp_globals, pico_gta_mp_globals_table);

extern "C"
{
    extern const mp_obj_module_t pico_gta_mp_cmodule = {
        .base = {&mp_type_module},
        .globals = (mp_obj_dict_t *)&pico_gta_mp_globals,
    };

    MP_REGISTER_MODULE(MP_QSTR_pico_gta, pico_gta_mp_cmodule);
}
