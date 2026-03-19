#include "camera_mp.h"
#include "engine_mp.h"
#include "entity_mp.h"
#include "game_mp.h"
#include "image_mp.h"
#include "level_mp.h"
#include "sprite3d_mp.h"
#include "triangle3d_mp.h"
#include "engine/engine.hpp"

static inline GameEngine *engine_get_context(engine_mp_obj_t *self)
{
    return static_cast<GameEngine *>(self->context);
}

static mp_obj_t engine_mp_game_global = MP_OBJ_NULL;

mp_obj_t engine_mp_get_current_game(void)
{
    return engine_mp_game_global;
}

void engine_mp_del_reference(mp_obj_t mp_obj)
{
    if (mp_obj == MP_OBJ_NULL)
    {
        return;
    }
    mp_obj_t del_method = mp_load_attr(mp_obj, MP_QSTR___del__);
    if (del_method != MP_OBJ_NULL)
    {
        mp_call_function_0(del_method);
    }
    mp_obj = MP_OBJ_NULL;
}

void engine_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    engine_mp_obj_t *self = static_cast<engine_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return;
    GameEngine *ctx = engine_get_context(self);
    Game *game = ctx->getGame();
    mp_print_str(print, "Engine(");
    mp_print_str(print, "game=");
    if (game != nullptr)
    {
        mp_obj_print_helper(print, mp_obj_new_str(game->name, strlen(game->name)), PRINT_REPR);
    }
    else
    {
        mp_print_str(print, "None");
    }
    mp_print_str(print, ")");
}

mp_obj_t engine_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 2, false);
    engine_mp_obj_t *self = mp_obj_malloc_with_finaliser(engine_mp_obj_t, &engine_mp_type);
    self->base.type = &engine_mp_type;
    mp_obj_t native_game = mp_obj_cast_to_native_base(args[0], MP_OBJ_FROM_PTR(&game_mp_type));
    if (native_game == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Game"));
    game_mp_obj_t *game_mp = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(native_game));
    Game *game_ctx = static_cast<Game *>(game_mp->context);
    self->game_obj = args[0];
    engine_mp_game_global = self->game_obj;
    float fps = (float)mp_obj_get_int(args[1]);
    self->context = new GameEngine(game_ctx, fps);
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t engine_mp_del(mp_obj_t self_in)
{
    engine_mp_obj_t *self = static_cast<engine_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    GameEngine *ctx = engine_get_context(self);
    if (ctx)
        delete ctx;
    self->context = nullptr;
    self->freed = true;
    self->game_obj = MP_OBJ_NULL;
    engine_mp_game_global = MP_OBJ_NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(engine_mp_del_obj, engine_mp_del);

mp_obj_t engine_mp_run(mp_obj_t self_in)
{
    engine_mp_obj_t *self = static_cast<engine_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return mp_const_none;
    GameEngine *ctx = engine_get_context(self);
    ctx->run();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(engine_mp_run_obj, engine_mp_run);

mp_obj_t engine_mp_run_async(size_t n_args, const mp_obj_t *args)
{
    engine_mp_obj_t *self = static_cast<engine_mp_obj_t *>(MP_OBJ_TO_PTR(args[0]));
    if (self->freed)
        return mp_const_none;
    GameEngine *ctx = engine_get_context(self);
    bool should_delay = n_args > 1 ? mp_obj_is_true(args[1]) : true;
    ctx->runAsync(should_delay);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(engine_mp_run_async_obj, 1, 2, engine_mp_run_async);

mp_obj_t engine_mp_stop(mp_obj_t self_in)
{
    engine_mp_obj_t *self = static_cast<engine_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return mp_const_none;
    // remove below for now.. we got a freeze
    // I think its because python still holds references
    // but no matter what I did before/after calling stop
    // nothing helped.. regardless we used m_malloc on all contexts
    // so gc will clean them up
    // GameEngine *ctx = engine_get_context(self);
    //  ctx->stop();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(engine_mp_stop_obj, engine_mp_stop);

mp_obj_t engine_mp_update_game_input(mp_obj_t self_in, mp_obj_t input)
{
    engine_mp_obj_t *self = static_cast<engine_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return mp_const_none;
    GameEngine *ctx = engine_get_context(self);
    ctx->updateGameInput((uint8_t)mp_obj_get_int(input));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(engine_mp_update_game_input_obj, engine_mp_update_game_input);

void engine_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    engine_mp_obj_t *self = static_cast<engine_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return;
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_game)
        {
            destination[0] = self->game_obj;
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&engine_mp_del_obj);
        }
    }
}

static const mp_rom_map_elem_t engine_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&engine_mp_run_obj)},
    {MP_ROM_QSTR(MP_QSTR_run_async), MP_ROM_PTR(&engine_mp_run_async_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&engine_mp_stop_obj)},
    {MP_ROM_QSTR(MP_QSTR_update_game_input), MP_ROM_PTR(&engine_mp_update_game_input_obj)}};
static MP_DEFINE_CONST_DICT(engine_mp_locals_dict, engine_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t engine_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Engine,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)engine_mp_make_new,
            (const void *)engine_mp_print,
            (const void *)engine_mp_attr,
            (const void *)&engine_mp_locals_dict,
        },
    };
}

static const mp_rom_map_elem_t engine_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_engine)},
    {MP_ROM_QSTR(MP_QSTR_Camera), MP_ROM_PTR(&camera_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Engine), MP_ROM_PTR(&engine_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Entity), MP_ROM_PTR(&entity_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Game), MP_ROM_PTR(&game_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Image), MP_ROM_PTR(&image_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Level), MP_ROM_PTR(&level_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Sprite3D), MP_ROM_PTR(&sprite3d_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Triangle3D), MP_ROM_PTR(&triangle3d_mp_type)},
};
static MP_DEFINE_CONST_DICT(engine_mp_globals, engine_mp_globals_table);

extern "C"
{
    extern const mp_obj_module_t engine_mp_cmodule = {
        .base = {&mp_type_module},
        .globals = (mp_obj_dict_t *)&engine_mp_globals,
    };

    MP_REGISTER_MODULE(MP_QSTR_engine, engine_mp_cmodule);
}
