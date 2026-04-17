#include "level_mp.h"
#include "game_mp.h"
#include "engine/game.hpp"
#include "engine/level.hpp"
#include "engine/entity.hpp"

static inline Level *level_get_context(level_mp_obj_t *self)
{
    return static_cast<Level *>(self->context);
}

void level_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return;
    Level *ctx = level_get_context(self);
    mp_print_str(print, "Level(");
    mp_print_str(print, "name=");
    mp_obj_print_helper(print, mp_obj_new_str(ctx->name, strlen(ctx->name)), PRINT_REPR);
    mp_print_str(print, ", size=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.z), PRINT_REPR);
    mp_print_str(print, "), entity_count=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->getEntityCount()), PRINT_REPR);
    mp_print_str(print, ")");
}

static void level_start_trampoline(Level &level, void *ctx)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(ctx);

    if (self->start == MP_OBJ_NULL || self->start == mp_const_none)
        return;

    if (mp_obj_is_type(self->start, &mp_type_bound_meth))
    {
        mp_call_function_n_kw(self->start, 0, 0, nullptr);
    }
    else
    {
        mp_obj_t call_args[1] = {MP_OBJ_FROM_PTR(self)};
        mp_call_function_n_kw(self->start, 1, 0, call_args);
    }
}

static void level_stop_trampoline(Level &level, void *ctx)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(ctx);

    if (self->stop == MP_OBJ_NULL || self->stop == mp_const_none)
        return;

    if (mp_obj_is_type(self->stop, &mp_type_bound_meth))
    {
        mp_call_function_n_kw(self->stop, 0, 0, nullptr);
    }
    else
    {
        mp_obj_t call_args[1] = {MP_OBJ_FROM_PTR(self)};
        mp_call_function_n_kw(self->stop, 1, 0, call_args);
    }
}

mp_obj_t level_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // args: name (str), size (Vector), game (Game), start (function)[optional], stop (function)[optional]
    mp_arg_check_num(n_args, n_kw, 3, 5, false);
    level_mp_obj_t *self = mp_obj_malloc_with_finaliser(level_mp_obj_t, &level_mp_type);
    self->base.type = &level_mp_type;
    self->freed = false;

    // Parse name
    size_t name_len;
    const char *name_str = mp_obj_str_get_data(args[0], &name_len);
    char *name_buf = static_cast<char *>(m_malloc(name_len + 1));
    memcpy(name_buf, name_str, name_len);
    name_buf[name_len] = '\0';

    // Parse size
    mp_obj_t native_size = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_size == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for size"));
    vector_mp_obj_t *size_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_size));
    Vector size(size_vec->x, size_vec->y, size_vec->z, size_vec->integer);
    self->size_obj = args[1];

    // Extract Game* from the game_mp_obj_t (handles Python subclass wrappers)
    mp_obj_t native_game = mp_obj_cast_to_native_base(args[2], MP_OBJ_FROM_PTR(&game_mp_type));
    if (native_game == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Game"));
    game_mp_obj_t *game_mp = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(native_game));
    Game *game_ctx = static_cast<Game *>(game_mp->context);

    // pointers to start and stop functions (optional)
    self->start = mp_const_none;
    self->stop = mp_const_none;
    CallbackLevel start_func = {};
    CallbackLevel stop_func = {};
    if (n_args > 3)
    {
        if (mp_obj_is_callable(args[3]))
        {
            self->start = args[3];
            start_func = {level_start_trampoline, self};
        }
    }
    if (n_args > 4)
    {
        if (mp_obj_is_callable(args[4]))
        {
            self->stop = args[4];
            stop_func = {level_stop_trampoline, self};
        }
    }
    // Create the C++ Level — all state lives in this single context
    self->context = new Level(name_buf, size, game_ctx, start_func, stop_func);

    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t level_mp_del(mp_obj_t self_in)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Level *ctx = level_get_context(self);
    if (ctx)
    {
        // Free the name buffer we allocated in make_new
        if (ctx->name != NULL)
        {
            m_free(const_cast<char *>(ctx->name));
            ctx->name = NULL;
        }
        delete ctx;
    }
    self->context = nullptr;
    self->freed = true;
    self->start = mp_const_none;
    self->stop = mp_const_none;
    self->size_obj = MP_OBJ_NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(level_mp_del_obj, level_mp_del);

void level_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        Level *ctx = level_get_context(self);
        switch (attribute)
        {
        case MP_QSTR_name:
            destination[0] = mp_obj_new_str(ctx->name, strlen(ctx->name));
            break;
        case MP_QSTR_size:
            destination[0] = self->size_obj;
            break;
        case MP_QSTR_entity_count:
            destination[0] = mp_obj_new_int(ctx->getEntityCount());
            break;
        case MP_QSTR_clear_allowed:
            destination[0] = mp_obj_new_bool(ctx->isClearAllowed());
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&level_mp_del_obj);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL; // not found here; fall through to locals_dict
            break;
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        switch (attribute)
        {
        case MP_QSTR_name:
            level_mp_set_name(self_in, destination[1]);
            break;
        case MP_QSTR_size:
            level_mp_set_size(self_in, destination[1]);
            break;
        case MP_QSTR_clear_allowed:
            level_mp_set_clear_allowed(self_in, destination[1]);
            break;
        default:
            return; // Fail
        };
        destination[0] = MP_OBJ_NULL;
    }
}

mp_obj_t level_mp_clear(mp_obj_t self_in)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Level *ctx = level_get_context(self);
    ctx->clear();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(level_mp_clear_obj, level_mp_clear);

mp_obj_t level_mp_entity_add(mp_obj_t self_in, mp_obj_t entity_in)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Level *ctx = level_get_context(self);
    mp_obj_t native_entity = mp_obj_cast_to_native_base(entity_in, MP_OBJ_FROM_PTR(&entity_mp_type));
    if (native_entity == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Entity"));
    entity_mp_obj_t *entity = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(native_entity));
    if (entity->freed)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Cannot add freed entity to level"));
    }
    Entity *entity_ctx = static_cast<Entity *>(entity->context);
    if (entity_ctx == nullptr)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Entity context is null"));
    }
    ctx->entity_add(entity_ctx);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(level_mp_entity_add_obj, level_mp_entity_add);

mp_obj_t level_mp_entity_remove(mp_obj_t self_in, mp_obj_t entity_in)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Level *ctx = level_get_context(self);
    mp_obj_t native_entity = mp_obj_cast_to_native_base(entity_in, MP_OBJ_FROM_PTR(&entity_mp_type));
    if (native_entity == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Entity"));
    entity_mp_obj_t *entity = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(native_entity));
    if (entity->freed)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Cannot remove freed entity from level"));
    }
    Entity *entity_ctx = static_cast<Entity *>(entity->context);
    if (entity_ctx == nullptr)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Entity context is null"));
    }
    ctx->entity_remove(entity_ctx);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(level_mp_entity_remove_obj, level_mp_entity_remove);

mp_obj_t level_mp_set_name(mp_obj_t self_in, mp_obj_t name_obj)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Level *ctx = level_get_context(self);
    size_t name_len;
    const char *name_str = mp_obj_str_get_data(name_obj, &name_len);
    if (ctx->name != NULL)
    {
        m_free(const_cast<char *>(ctx->name));
    }
    char *name_buf = static_cast<char *>(m_malloc(name_len + 1));
    memcpy(name_buf, name_str, name_len);
    name_buf[name_len] = '\0';
    ctx->name = name_buf;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(level_mp_set_name_obj, level_mp_set_name);

mp_obj_t level_mp_set_size(mp_obj_t self_in, mp_obj_t size_obj)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Level *ctx = level_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(size_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->size.x = vec->x;
    ctx->size.y = vec->y;
    ctx->size.z = vec->z;
    ctx->size.integer = vec->integer;
    self->size_obj = size_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(level_mp_set_size_obj, level_mp_set_size);

mp_obj_t level_mp_set_clear_allowed(mp_obj_t self_in, mp_obj_t clear_allowed_obj)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Level *ctx = level_get_context(self);
    ctx->setClearAllowed(mp_obj_is_true(clear_allowed_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(level_mp_set_clear_allowed_obj, level_mp_set_clear_allowed);

mp_obj_t level_mp_get_entity(mp_obj_t self_in, mp_obj_t index_obj)
{
    level_mp_obj_t *self = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Level *ctx = level_get_context(self);
    mp_int_t index = mp_obj_get_int(index_obj);
    if (index < 0 || index >= ctx->getEntityCount())
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Entity index out of range"));
    }
    Entity *entity_ctx = ctx->getEntity(index);
    if (entity_ctx == nullptr)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Entity context is null"));
    }
    return MP_OBJ_FROM_PTR(entity_ctx->mp_ctx);
}
static MP_DEFINE_CONST_FUN_OBJ_2(level_mp_get_entity_obj, level_mp_get_entity);

static const mp_rom_map_elem_t level_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&level_mp_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_entity_add), MP_ROM_PTR(&level_mp_entity_add_obj)},
    {MP_ROM_QSTR(MP_QSTR_entity_remove), MP_ROM_PTR(&level_mp_entity_remove_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_name), MP_ROM_PTR(&level_mp_set_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_size), MP_ROM_PTR(&level_mp_set_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_clear_allowed), MP_ROM_PTR(&level_mp_set_clear_allowed_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_entity), MP_ROM_PTR(&level_mp_get_entity_obj)},
};
static MP_DEFINE_CONST_DICT(level_mp_locals_dict, level_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t level_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Level,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)level_mp_make_new,
            (const void *)level_mp_print,
            (const void *)level_mp_attr,
            (const void *)&level_mp_locals_dict,
        },
    };
}
