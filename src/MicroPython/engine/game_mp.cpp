#include "game_mp.h"
#include "camera_mp.h"
#include "level_mp.h"
#include "engine/game.hpp"
#include <functional>

// Static reference to the current game's Python Draw object,
// so entity callbacks can propagate it to temporary game wrappers.
static mp_obj_t _game_mp_draw_ref = MP_OBJ_NULL;

mp_obj_t game_mp_get_current_draw(void)
{
    return _game_mp_draw_ref != MP_OBJ_NULL ? _game_mp_draw_ref : mp_const_none;
}

static inline Game *game_get_context(game_mp_obj_t *self)
{
    return static_cast<Game *>(self->context);
}

void game_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return;
    Game *ctx = game_get_context(self);
    mp_print_str(print, "Game(");
    mp_print_str(print, "name=");
    mp_obj_print_helper(print, mp_obj_new_str(ctx->name, strlen(ctx->name)), PRINT_REPR);
    mp_print_str(print, ", position=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->pos.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->pos.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->pos.z), PRINT_REPR);
    mp_print_str(print, "), size=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.z), PRINT_REPR);
    mp_print_str(print, "), is_active=");
    mp_obj_print_helper(print, ctx->is_active ? mp_const_true : mp_const_false, PRINT_REPR);
    mp_print_str(print, ", foreground_color=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->fg_color), PRINT_REPR);
    mp_print_str(print, ", background_color=");
    mp_obj_print_helper(print, mp_obj_new_int(ctx->bg_color), PRINT_REPR);
    mp_print_str(print, ", camera_perspective=");
    if (ctx->camera != nullptr)
    {
        if (ctx->camera->perspective == CAMERA_FIRST_PERSON)
        {
            mp_print_str(print, "first_person");
        }
        else if (ctx->camera->perspective == CAMERA_THIRD_PERSON)
        {
            mp_print_str(print, "third_person");
        }
        else
        {
            mp_obj_print_helper(print, mp_obj_new_int(ctx->camera->perspective), PRINT_REPR);
        }
    }
    else
    {
        mp_print_str(print, "None");
    }
    mp_print_str(print, ", input=");
    if (ctx->input == -1)
    {
        mp_print_str(print, "None");
    }
    else
    {
        mp_obj_print_helper(print, mp_obj_new_int(ctx->input), PRINT_REPR);
    }
    mp_print_str(print, ")");
}

mp_obj_t game_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // required: name (str), size (Vector)
    // optional: foreground_color (int), background_color (int), camera_context (Camera), start (function), stop (function), update (function), draw (Draw)
    mp_arg_check_num(n_args, n_kw, 2, 9, false);
    game_mp_obj_t *self = mp_obj_malloc_with_finaliser(game_mp_obj_t, &game_mp_type);
    self->base.type = &game_mp_type;
    self->freed = false;

    // Parse name
    size_t name_len;
    const char *name_str = mp_obj_str_get_data(args[0], &name_len);
    char *name_buf = static_cast<char *>(m_malloc(name_len + 1));
    memcpy(name_buf, name_str, name_len);
    name_buf[name_len] = '\0';

    // Parse size (handles Python subclass wrappers)
    mp_obj_t native_size = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_size == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for size"));
    vector_mp_obj_t *size_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_size));
    Vector size(size_vec->x, size_vec->y, size_vec->z, size_vec->integer);

    // Parse optional args
    uint16_t fg_color = (n_args >= 3) ? static_cast<uint16_t>(mp_obj_get_int(args[2])) : 0xFFFF;
    uint16_t bg_color = (n_args >= 4) ? static_cast<uint16_t>(mp_obj_get_int(args[3])) : 0x0000;

    // Initialize callback fields
    self->start = mp_const_none;
    self->stop = mp_const_none;
    self->update = mp_const_none;
    self->draw = mp_const_none;
    if (n_args >= 9 && args[8] != mp_const_none)
    {
        self->draw = args[8];
        _game_mp_draw_ref = args[8];
    }
    std::function<void()> start_func = nullptr;
    std::function<void()> stop_func = nullptr;
    std::function<void()> update_func = nullptr;

    if (n_args >= 6 && mp_obj_is_callable(args[5]))
    {
        self->start = args[5];
        game_mp_obj_t *self_ptr = self;
        mp_obj_t cb = args[5];
        start_func = [self_ptr, cb]()
        {
            mp_obj_t game_obj = MP_OBJ_FROM_PTR(self_ptr);
            mp_call_function_1(cb, game_obj);
        };
    }
    if (n_args >= 7 && mp_obj_is_callable(args[6]))
    {
        self->stop = args[6];
        game_mp_obj_t *self_ptr = self;
        mp_obj_t cb = args[6];
        stop_func = [self_ptr, cb]()
        {
            mp_obj_t game_obj = MP_OBJ_FROM_PTR(self_ptr);
            mp_call_function_1(cb, game_obj);
        };
    }
    if (n_args >= 8 && mp_obj_is_callable(args[7]))
    {
        self->update = args[7];
        mp_obj_t cb = args[7];
        update_func = [cb]()
        {
            // cb is typically a bound method (e.g. self._update) so call with 0 extra args
            mp_call_function_0(cb);
        };
    }

    // Create a Draw instance for the Game
    Draw *draw = new Draw();

    // Extract Camera* from camera_mp_obj_t if provided (handles Python subclass wrappers)
    Camera *camera_ctx = nullptr;
    if (n_args >= 5 && args[4] != mp_const_none)
    {
        mp_obj_t native_cam = mp_obj_cast_to_native_base(args[4], MP_OBJ_FROM_PTR(&camera_mp_type));
        if (native_cam == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Camera"));
        camera_mp_obj_t *cam_mp = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(native_cam));
        camera_ctx = static_cast<Camera *>(cam_mp->context);
    }

    // Create the C++ Game — all state lives in this single context
    self->context = new Game(name_buf, size, draw, fg_color, bg_color, camera_ctx, start_func, stop_func, update_func);

    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t game_mp_del(mp_obj_t self_in)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Game *ctx = game_get_context(self);
    // Free the name buffer we allocated in make_new
    if (ctx->name != NULL)
    {
        m_free(const_cast<char *>(ctx->name));
        ctx->name = NULL;
    }
    delete ctx;
    self->context = nullptr;
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(game_mp_del_obj, game_mp_del);

void game_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    Game *ctx = game_get_context(self);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_name)
        {
            destination[0] = mp_obj_new_str(ctx->name, strlen(ctx->name));
        }
        else if (attribute == MP_QSTR_position)
        {
            destination[0] = vector_mp_init(ctx->pos.x, ctx->pos.y, ctx->pos.z, ctx->pos.integer);
        }
        else if (attribute == MP_QSTR_size)
        {
            destination[0] = vector_mp_init(ctx->size.x, ctx->size.y, ctx->size.z, ctx->size.integer);
        }
        else if (attribute == MP_QSTR_is_active)
        {
            destination[0] = ctx->is_active ? mp_const_true : mp_const_false;
        }
        else if (attribute == MP_QSTR_foreground_color)
        {
            destination[0] = mp_obj_new_int(ctx->fg_color);
        }
        else if (attribute == MP_QSTR_background_color)
        {
            destination[0] = mp_obj_new_int(ctx->bg_color);
        }
        else if (attribute == MP_QSTR_camera)
        {
            destination[0] = mp_const_none; // Return None for camera attribute for now..
        }
        else if (attribute == MP_QSTR_input)
        {
            destination[0] = mp_obj_new_int(ctx->input);
        }
        else if (attribute == MP_QSTR_draw)
        {
            destination[0] = self->draw;
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&game_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_name)
        {
            size_t name_len;
            const char *name_str = mp_obj_str_get_data(destination[1], &name_len);
            if (ctx->name != NULL)
            {
                m_free(const_cast<char *>(ctx->name));
            }
            char *name_buf = static_cast<char *>(m_malloc(name_len + 1));
            memcpy(name_buf, name_str, name_len);
            name_buf[name_len] = '\0';
            ctx->name = name_buf;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_position)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->old_pos.x = ctx->pos.x;
            ctx->old_pos.y = ctx->pos.y;
            ctx->old_pos.z = ctx->pos.z;
            ctx->old_pos.integer = ctx->pos.integer;
            ctx->pos.x = vec->x;
            ctx->pos.y = vec->y;
            ctx->pos.z = vec->z;
            ctx->pos.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_size)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->size.x = vec->x;
            ctx->size.y = vec->y;
            ctx->size.z = vec->z;
            ctx->size.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_active)
        {
            ctx->is_active = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_foreground_color)
        {
            ctx->fg_color = static_cast<uint16_t>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_background_color)
        {
            ctx->bg_color = static_cast<uint16_t>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_camera_perspective)
        {
            if (ctx->camera != nullptr)
            {
                ctx->camera->perspective = static_cast<CameraPerspective>(mp_obj_get_int(destination[1]));
            }
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_input)
        {
            ctx->input = static_cast<int>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t game_mp_get_camera(mp_obj_t self_in)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Game *ctx = game_get_context(self);
    Camera *cam = ctx->getCamera();
    if (cam == nullptr)
    {
        return mp_const_none;
    }
    // Return a new Camera MP object wrapping the Game's camera fields
    return vector_mp_init(cam->position.x, cam->position.y, cam->position.z, cam->position.integer);
}

mp_obj_t game_mp_set_camera(mp_obj_t self_in, mp_obj_t camera_in)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Game *ctx = game_get_context(self);
    mp_obj_t native_cam = mp_obj_cast_to_native_base(camera_in, MP_OBJ_FROM_PTR(&camera_mp_type));
    if (native_cam == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Camera"));
    camera_mp_obj_t *cam_mp = static_cast<camera_mp_obj_t *>(MP_OBJ_TO_PTR(native_cam));
    Camera *cam_ctx = static_cast<Camera *>(cam_mp->context);
    ctx->setCamera(*cam_ctx);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(game_mp_set_camera_obj, game_mp_set_camera);

mp_obj_t game_mp_set_input(mp_obj_t self_in, mp_obj_t input_in)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return mp_const_none;
    Game *ctx = game_get_context(self);
    ctx->input = static_cast<int>(mp_obj_get_int(input_in));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(game_mp_set_input_obj, game_mp_set_input);

mp_obj_t game_mp_level_add(mp_obj_t self_in, mp_obj_t level_in)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Game *ctx = game_get_context(self);
    mp_obj_t native_level = mp_obj_cast_to_native_base(level_in, MP_OBJ_FROM_PTR(&level_mp_type));
    if (native_level == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Level"));
    level_mp_obj_t *level = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(native_level));
    Level *level_ctx = static_cast<Level *>(level->context);
    ctx->level_add(level_ctx);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(game_mp_level_add_obj, game_mp_level_add);

mp_obj_t game_mp_level_remove(mp_obj_t self_in, mp_obj_t level_in)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Game *ctx = game_get_context(self);
    mp_obj_t native_level = mp_obj_cast_to_native_base(level_in, MP_OBJ_FROM_PTR(&level_mp_type));
    if (native_level == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Level"));
    level_mp_obj_t *level = static_cast<level_mp_obj_t *>(MP_OBJ_TO_PTR(native_level));
    Level *level_ctx = static_cast<Level *>(level->context);
    ctx->level_remove(level_ctx);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(game_mp_level_remove_obj, game_mp_level_remove);

mp_obj_t game_mp_level_switch(mp_obj_t self_in, mp_obj_t index_in)
{
    game_mp_obj_t *self = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Game *ctx = game_get_context(self);
    if (mp_obj_is_str(index_in))
    {
        // Switch by name
        const char *name = mp_obj_str_get_str(index_in);
        ctx->level_switch(name);
    }
    else
    {
        // Switch by index
        int index = mp_obj_get_int(index_in);
        ctx->level_switch(index);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(game_mp_level_switch_obj, game_mp_level_switch);

static const mp_rom_map_elem_t game_mp_locals_dict_table[] = {
    // Methods
    {MP_ROM_QSTR(MP_QSTR_set_camera), MP_ROM_PTR(&game_mp_set_camera_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_input), MP_ROM_PTR(&game_mp_set_input_obj)},
    {MP_ROM_QSTR(MP_QSTR_level_add), MP_ROM_PTR(&game_mp_level_add_obj)},
    {MP_ROM_QSTR(MP_QSTR_level_remove), MP_ROM_PTR(&game_mp_level_remove_obj)},
    {MP_ROM_QSTR(MP_QSTR_level_switch), MP_ROM_PTR(&game_mp_level_switch_obj)},

    // Constants
    {MP_ROM_QSTR(MP_QSTR_MAX_LEVELS), MP_ROM_INT(MAX_LEVELS)},
};
static MP_DEFINE_CONST_DICT(game_mp_locals_dict, game_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t game_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Game,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)game_mp_make_new,
            (const void *)game_mp_print,
            (const void *)game_mp_attr,
            (const void *)&game_mp_locals_dict,
        },
    };
}
