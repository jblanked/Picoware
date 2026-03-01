#include "camera_mp.h"
#include "engine_mp.h"
#include "entity_mp.h"
#include "game_mp.h"
#include "level_mp.h"
#include "sprite3d_mp.h"
#include "triangle3d_mp.h"

const mp_obj_type_t engine_mp_type;

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
    engine_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Engine(");
    mp_print_str(print, "game=");
    mp_obj_print_helper(print, self->game, PRINT_REPR);
    mp_print_str(print, ", fps=");
    mp_obj_print_helper(print, mp_obj_new_int(self->fps), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t engine_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 2, false);
    engine_mp_obj_t *self = mp_obj_malloc_with_finaliser(engine_mp_obj_t, &engine_mp_type);
    self->base.type = &engine_mp_type;
    self->game = args[0];
    self->fps = mp_obj_get_int(args[1]);
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t engine_mp_del(mp_obj_t self_in)
{
    engine_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }
    engine_mp_del_reference(self->game);
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(engine_mp_del_obj, engine_mp_del);

void engine_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    engine_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // load attributes
        if (attribute == MP_QSTR_game)
        {
            destination[0] = self->game;
        }
        else if (attribute == MP_QSTR_fps)
        {
            destination[0] = mp_obj_new_int(self->fps);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&engine_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // store attributes
        if (attribute == MP_QSTR_game)
        {
            engine_mp_del_reference(self->game);
            self->game = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_fps)
        {
            self->fps = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

MP_DEFINE_CONST_OBJ_TYPE(
    engine_mp_type,
    MP_QSTR_Engine,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, engine_mp_print,
    make_new, engine_mp_make_new,
    attr, engine_mp_attr);

static const mp_rom_map_elem_t engine_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_engine)},
    {MP_ROM_QSTR(MP_QSTR_Camera), MP_ROM_PTR(&camera_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Engine), MP_ROM_PTR(&engine_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Entity), MP_ROM_PTR(&entity_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Game), MP_ROM_PTR(&game_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Level), MP_ROM_PTR(&level_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Sprite3D), MP_ROM_PTR(&sprite3d_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_Triangle3D), MP_ROM_PTR(&triangle3d_mp_type)},
};
static MP_DEFINE_CONST_DICT(engine_mp_globals, engine_mp_globals_table);

const mp_obj_module_t engine_mp_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&engine_mp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_engine, engine_mp_cmodule);
