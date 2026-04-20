#include "entity_mp.h"
#include "game_mp.h"
#include "engine_mp.h"
#include "image_mp.h"
#include "pico-game-engine/engine/entity.hpp"
//
#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

static inline Entity *entity_get_context(entity_mp_obj_t *self)
{
    return static_cast<Entity *>(self->context);
}

void entity_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
        return;
    Entity *ctx = entity_get_context(self);
    mp_print_str(print, "Entity(");
    mp_print_str(print, "name=");
    mp_obj_print_helper(print, mp_obj_new_str(ctx->name, strlen(ctx->name)), PRINT_REPR);
    mp_print_str(print, ", type=");
    switch (ctx->type)
    {
    case ENTITY_PLAYER:
        mp_print_str(print, "PLAYER");
        break;
    case ENTITY_ENEMY:
        mp_print_str(print, "ENEMY");
        break;
    case ENTITY_ICON:
        mp_print_str(print, "ICON");
        break;
    case ENTITY_NPC:
        mp_print_str(print, "NPC");
        break;
    case ENTITY_3D_SPRITE:
        mp_print_str(print, "SPRITE_3D");
        break;
    default:
        mp_print_str(print, "UNKNOWN");
        break;
    }
    mp_print_str(print, ", position=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->position.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->position.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->position.z), PRINT_REPR);
    mp_print_str(print, "), size=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->size.z), PRINT_REPR);
    mp_print_str(print, "), is_8bit=");
    mp_obj_print_helper(print, mp_obj_new_bool(ctx->is_8bit), PRINT_REPR);
    mp_print_str(print, ", is_active=");
    mp_obj_print_helper(print, mp_obj_new_bool(ctx->is_active), PRINT_REPR);
    mp_print_str(print, ", is_visible=");
    mp_obj_print_helper(print, mp_obj_new_bool(ctx->is_visible), PRINT_REPR);
    mp_print_str(print, ", is_player=");
    mp_obj_print_helper(print, mp_obj_new_bool(ctx->is_player), PRINT_REPR);
    mp_print_str(print, ", direction=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->direction.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->direction.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->direction.z), PRINT_REPR);
    mp_print_str(print, "), plane=(");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->plane.x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->plane.y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->plane.z), PRINT_REPR);
    mp_print_str(print, "), state=");
    switch (ctx->state)
    {
    case ENTITY_IDLE:
        mp_print_str(print, "IDLE");
        break;
    case ENTITY_MOVING:
        mp_print_str(print, "MOVING");
        break;
    case ENTITY_MOVING_TO_START:
        mp_print_str(print, "MOVING_TO_START");
        break;
    case ENTITY_MOVING_TO_END:
        mp_print_str(print, "MOVING_TO_END");
        break;
    case ENTITY_ATTACKING:
        mp_print_str(print, "ATTACKING");
        break;
    case ENTITY_ATTACKED:
        mp_print_str(print, "ATTACKED");
        break;
    case ENTITY_DEAD:
        mp_print_str(print, "DEAD");
        break;
    default:
        mp_print_str(print, "UNKNOWN");
        break;
    }
    mp_print_str(print, ", health=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->health), PRINT_REPR);
    mp_print_str(print, ", max_health=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->max_health), PRINT_REPR);
    mp_print_str(print, ", level=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->level), PRINT_REPR);
    mp_print_str(print, ", xp=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->xp), PRINT_REPR);
    mp_print_str(print, ", health_regen=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->health_regen), PRINT_REPR);
    mp_print_str(print, ", elapsed_health_regen=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->elapsed_health_regen), PRINT_REPR);
    mp_print_str(print, ", sprite_3d_type=");
    switch (ctx->sprite_3d_type)
    {
    case SPRITE_3D_HUMANOID:
        mp_print_str(print, "HUMANOID");
        break;
    case SPRITE_3D_TREE:
        mp_print_str(print, "TREE");
        break;
    case SPRITE_3D_HOUSE:
        mp_print_str(print, "HOUSE");
        break;
    case SPRITE_3D_PILLAR:
        mp_print_str(print, "PILLAR");
        break;
    case SPRITE_3D_CUSTOM:
        mp_print_str(print, "CUSTOM");
        break;
    default:
        mp_print_str(print, "NONE");
        break;
    }
    mp_print_str(print, ", sprite_rotation=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->sprite_rotation), PRINT_REPR);
    mp_print_str(print, ", sprite_scale=");
    mp_obj_print_helper(print, mp_obj_new_float(ctx->sprite_scale), PRINT_REPR);
    mp_print_str(print, ")");
}

static void entity_start_trampoline(Entity *e, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);
    if (self->start == MP_OBJ_NULL || self->start == mp_const_none)
    {
        return;
    }
    mp_obj_t current_game = engine_mp_get_current_game();
    if (current_game == MP_OBJ_NULL || current_game == mp_const_none)
    {
        PRINT("Warning: entity_start_trampoline called but no current game context\n");
        return;
    }

    if (mp_obj_is_type(self->start, &mp_type_bound_meth))
    {
        mp_obj_t call_args[1] = {current_game};
        mp_call_function_n_kw(self->start, 1, 0, call_args);
    }
    else
    {
        mp_obj_t call_args[2] = {MP_OBJ_FROM_PTR(self), current_game};
        mp_call_function_n_kw(self->start, 2, 0, call_args);
    }
}

static void entity_stop_trampoline(Entity *e, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);
    if (self->stop == MP_OBJ_NULL || self->stop == mp_const_none)
    {
        return;
    }
    mp_obj_t current_game = engine_mp_get_current_game();
    if (current_game == MP_OBJ_NULL || current_game == mp_const_none)
    {
        PRINT("Warning: entity_stop_trampoline called but no current game context\n");
        return;
    }

    if (mp_obj_is_type(self->stop, &mp_type_bound_meth))
    {
        mp_obj_t call_args[1] = {current_game};
        mp_call_function_n_kw(self->stop, 1, 0, call_args);
    }
    else
    {
        mp_obj_t call_args[2] = {MP_OBJ_FROM_PTR(self), current_game};
        mp_call_function_n_kw(self->stop, 2, 0, call_args);
    }
}

static void entity_update_trampoline(Entity *e, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);

    if (self->update == MP_OBJ_NULL || self->update == mp_const_none)
    {
        return;
    }

    mp_obj_t current_game = engine_mp_get_current_game();
    if (current_game == MP_OBJ_NULL || current_game == mp_const_none)
    {
        PRINT("Warning: entity_update_trampoline called but no current game context\n");
        return;
    }

    if (mp_obj_is_type(self->update, &mp_type_bound_meth))
    {
        mp_obj_t call_args[1] = {current_game};
        mp_call_function_n_kw(self->update, 1, 0, call_args);
    }
    else
    {
        mp_obj_t call_args[2] = {MP_OBJ_FROM_PTR(self), current_game};
        mp_call_function_n_kw(self->update, 2, 0, call_args);
    }
}

static void entity_render_trampoline(Entity *e, Draw *d, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);

    if (self->render == MP_OBJ_NULL || self->render == mp_const_none)
    {
        return;
    }

    mp_obj_t current_game = engine_mp_get_current_game();
    if (current_game == MP_OBJ_NULL || current_game == mp_const_none)
    {
        PRINT("Warning: entity_render_trampoline called but no current game context\n");
        return;
    }
    mp_obj_t native_game = mp_obj_cast_to_native_base(current_game, MP_OBJ_FROM_PTR(&game_mp_type));
    if (native_game == MP_OBJ_NULL)
    {
        PRINT("Warning: entity_render_trampoline could not resolve native game base\n");
        return;
    }
    game_mp_obj_t *game_ptr = static_cast<game_mp_obj_t *>(MP_OBJ_TO_PTR(native_game));
    mp_obj_t draw_obj = game_ptr->draw;
    if (draw_obj == MP_OBJ_NULL || draw_obj == mp_const_none)
    {
        PRINT("Warning: entity_render_trampoline called but game has no draw object\n");
        return;
    }

    if (mp_obj_is_type(self->render, &mp_type_bound_meth))
    {
        mp_obj_t call_args[2] = {draw_obj, current_game};
        mp_call_function_n_kw(self->render, 2, 0, call_args);
    }
    else
    {
        mp_obj_t call_args[3] = {MP_OBJ_FROM_PTR(self), draw_obj, current_game};
        mp_call_function_n_kw(self->render, 3, 0, call_args);
    }
}

static void entity_collision_trampoline(Entity *e, Entity *other, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);

    if (self->collision == MP_OBJ_NULL || self->collision == mp_const_none)
        return;

    mp_obj_t current_game = engine_mp_get_current_game();
    if (current_game == MP_OBJ_NULL || current_game == mp_const_none)
    {
        PRINT("Warning: entity_collision_trampoline called but no current game context\n");
        return;
    }

    mp_obj_t other_obj = mp_const_none;
    if (other != nullptr && other->mp_ctx != nullptr)
    {
        other_obj = MP_OBJ_FROM_PTR(static_cast<entity_mp_obj_t *>(other->mp_ctx));
    }

    if (mp_obj_is_type(self->collision, &mp_type_bound_meth))
    {
        mp_obj_t call_args[2] = {other_obj, current_game};
        mp_call_function_n_kw(self->collision, 2, 0, call_args);
    }
    else
    {
        mp_obj_t call_args[3] = {MP_OBJ_FROM_PTR(self), other_obj, current_game};
        mp_call_function_n_kw(self->collision, 3, 0, call_args);
    }
}

mp_obj_t entity_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // name (str), type (EntityType), position (Vector), size (Vector), sprite_data (Image)[optional], sprite_left_data (Image)[optional], sprite_right_data (Image)[optional], start (function)[optional], stop (function)[optional], update (function)[optional], render (function)[optional], collision (function)[optional], is_8bit_sprite (bool, optional), sprite_3d_type (Sprite3DType, optional), sprite_3d_color (int, optional)
    // required: name, type, position, size
    mp_arg_check_num(n_args, n_kw, 4, 15, false);
    //
    entity_mp_obj_t *self = mp_obj_malloc_with_finaliser(entity_mp_obj_t, &entity_mp_type);
    self->base.type = &entity_mp_type;
    self->freed = false;

    // Parse name — allocate a copy since Entity stores the pointer but doesn't own it
    size_t name_len;
    const char *name_str = mp_obj_str_get_data(args[0], &name_len);
    char *name_buf = static_cast<char *>(m_malloc(name_len + 1));
    memcpy(name_buf, name_str, name_len);
    name_buf[name_len] = '\0';

    // Parse position and size from Vector MP objects (handles Python subclass wrappers)
    mp_obj_t native_pos = mp_obj_cast_to_native_base(args[2], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_pos == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for position"));
    vector_mp_obj_t *pos_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_pos));
    Vector position(pos_vec->x, pos_vec->y, pos_vec->z, pos_vec->integer);
    self->position_obj = args[2];
    mp_obj_t native_size = mp_obj_cast_to_native_base(args[3], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_size == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for size"));
    vector_mp_obj_t *size_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_size));
    Vector size(size_vec->x, size_vec->y, size_vec->z, size_vec->integer);
    self->size_obj = args[3];
    // Parse optional args
    // args layout: name[0], type[1], position[2], size[3],
    //   sprite_data[4], sprite_left[5], sprite_right[6],
    //   start[7], stop[8], update[9], render[10], collision[11],
    //   is_8bit[12], sprite_3d_type[13], sprite_3d_color[14]
    EntityType entity_type = n_args > 1 ? static_cast<EntityType>(mp_obj_get_int(args[1])) : ENTITY_PLAYER;
    bool is_8bit = n_args > 12 ? mp_obj_is_true(args[12]) : false;
    Sprite3DType s3d_type = n_args > 13 ? static_cast<Sprite3DType>(mp_obj_get_int(args[13])) : SPRITE_3D_NONE;
    uint16_t s3d_color = n_args > 14 ? (uint16_t)mp_obj_get_int(args[14]) : 0x0000;

    // Initialize callback fields
    self->start = mp_const_none;
    self->stop = mp_const_none;
    self->update = mp_const_none;
    self->render = mp_const_none;
    self->collision = mp_const_none;

    CallbackEntityGame start_func = {};
    CallbackEntityGame stop_func = {};
    CallbackEntityGame update_func = {};
    CallbackEntityDrawGame render_func = {};
    CallbackEntityEntityGame collision_func = {};

    if (n_args > 7 && mp_obj_is_callable(args[7]))
    {
        self->start = args[7];
        start_func.fn = entity_start_trampoline;
        start_func.ctx = self;
    }
    if (n_args > 8 && mp_obj_is_callable(args[8]))
    {
        self->stop = args[8];
        stop_func.fn = entity_stop_trampoline;
        stop_func.ctx = self;
    }
    if (n_args > 9 && mp_obj_is_callable(args[9]))
    {
        self->update = args[9];
        update_func.fn = entity_update_trampoline;
        update_func.ctx = self;
    }
    if (n_args > 10 && mp_obj_is_callable(args[10]))
    {
        self->render = args[10];
        render_func.fn = entity_render_trampoline;
        render_func.ctx = self;
    }
    if (n_args > 11 && mp_obj_is_callable(args[11]))
    {
        self->collision = args[11];
        collision_func.fn = entity_collision_trampoline;
        collision_func.ctx = self;
    }
    Image *sprite_data = nullptr;
    Image *sprite_left_data = nullptr;
    Image *sprite_right_data = nullptr;
    self->sprite_obj = mp_const_none;
    self->sprite_left_obj = mp_const_none;
    self->sprite_right_obj = mp_const_none;
    if (n_args > 4 && args[4] != mp_const_none)
    {
        mp_obj_t native_img = mp_obj_cast_to_native_base(args[4], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native_img == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Image for sprite_data"));
        image_mp_obj_t *img = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_img));
        sprite_data = static_cast<Image *>(img->context);
        self->sprite_obj = args[4];
    }
    if (n_args > 5 && args[5] != mp_const_none)
    {
        mp_obj_t native_img = mp_obj_cast_to_native_base(args[5], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native_img == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Image for sprite_left"));
        image_mp_obj_t *img = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_img));
        sprite_left_data = static_cast<Image *>(img->context);
        self->sprite_left_obj = args[5];
    }
    if (n_args > 6 && args[6] != mp_const_none)
    {
        mp_obj_t native_img = mp_obj_cast_to_native_base(args[6], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native_img == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Image for sprite_right"));
        image_mp_obj_t *img = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_img));
        sprite_right_data = static_cast<Image *>(img->context);
        self->sprite_right_obj = args[6];
    }

    // Create the C++ Entity
    self->context = new Entity(
        name_buf, entity_type, position, size,
        sprite_data, sprite_left_data, sprite_right_data,
        start_func, stop_func, update_func,
        render_func, collision_func,
        is_8bit, s3d_type, s3d_color);

    Entity *ctx = entity_get_context(self);
    self->old_position_obj = vector_mp_init(ctx->old_position.x, ctx->old_position.y, ctx->old_position.z, ctx->old_position.integer);
    self->direction_obj = vector_mp_init(ctx->direction.x, ctx->direction.y, ctx->direction.z, ctx->direction.integer);
    self->plane_obj = vector_mp_init(ctx->plane.x, ctx->plane.y, ctx->plane.z, ctx->plane.integer);
    self->start_position_obj = vector_mp_init(ctx->start_position.x, ctx->start_position.y, ctx->start_position.z, ctx->start_position.integer);
    self->end_position_obj = vector_mp_init(ctx->end_position.x, ctx->end_position.y, ctx->end_position.z, ctx->end_position.integer);
    ctx->mp_ctx = static_cast<void *>(self);
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t entity_mp_del(mp_obj_t self_in)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return mp_const_none;
    }
    Entity *ctx = entity_get_context(self);
    if (ctx)
    {
        if (ctx->name != NULL)
        {
            m_free(const_cast<char *>(ctx->name));
            ctx->name = NULL;
        }
        delete ctx;
    }
    self->context = nullptr;
    self->start = mp_const_none;
    self->stop = mp_const_none;
    self->update = mp_const_none;
    self->render = mp_const_none;
    self->collision = mp_const_none;
    self->position_obj = MP_OBJ_NULL;
    self->old_position_obj = MP_OBJ_NULL;
    self->size_obj = MP_OBJ_NULL;
    self->direction_obj = MP_OBJ_NULL;
    self->plane_obj = MP_OBJ_NULL;
    self->start_position_obj = MP_OBJ_NULL;
    self->end_position_obj = MP_OBJ_NULL;
    self->sprite_obj = MP_OBJ_NULL;
    self->sprite_left_obj = MP_OBJ_NULL;
    self->sprite_right_obj = MP_OBJ_NULL;
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(entity_mp_del_obj, entity_mp_del);

void entity_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    if (self->freed)
    {
        return;
    }
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        Entity *ctx = entity_get_context(self);
        switch (attribute)
        {
        case MP_QSTR_name:
            destination[0] = mp_obj_new_str(ctx->name, strlen(ctx->name));
            break;
        case MP_QSTR_type:
            destination[0] = mp_obj_new_int(ctx->type);
            break;
        case MP_QSTR_position:
            destination[0] = self->position_obj;
            break;
        case MP_QSTR_old_position:
            destination[0] = self->old_position_obj;
            break;
        case MP_QSTR_size:
            destination[0] = self->size_obj;
            break;
        case MP_QSTR_is_8bit:
            destination[0] = mp_obj_new_bool(ctx->is_8bit);
            break;
        case MP_QSTR_is_active:
            destination[0] = mp_obj_new_bool(ctx->is_active);
            break;
        case MP_QSTR_is_visible:
            destination[0] = mp_obj_new_bool(ctx->is_visible);
            break;
        case MP_QSTR_is_player:
            destination[0] = mp_obj_new_bool(ctx->is_player);
            break;
        case MP_QSTR_direction:
            destination[0] = self->direction_obj;
            break;
        case MP_QSTR_plane:
            destination[0] = self->plane_obj;
            break;
        case MP_QSTR_state:
            destination[0] = mp_obj_new_int(ctx->state);
            break;
        case MP_QSTR_start_position:
            destination[0] = self->start_position_obj;
            break;
        case MP_QSTR_end_position:
            destination[0] = self->end_position_obj;
            break;
        case MP_QSTR_move_timer:
            destination[0] = mp_obj_new_float(ctx->move_timer);
            break;
        case MP_QSTR_elapsed_move_timer:
            destination[0] = mp_obj_new_float(ctx->elapsed_move_timer);
            break;
        case MP_QSTR_radius:
            destination[0] = mp_obj_new_float(ctx->radius);
            break;
        case MP_QSTR_speed:
            destination[0] = mp_obj_new_float(ctx->speed);
            break;
        case MP_QSTR_attack_timer:
            destination[0] = mp_obj_new_float(ctx->attack_timer);
            break;
        case MP_QSTR_elapsed_attack_timer:
            destination[0] = mp_obj_new_float(ctx->elapsed_attack_timer);
            break;
        case MP_QSTR_strength:
            destination[0] = mp_obj_new_float(ctx->strength);
            break;
        case MP_QSTR_health:
            destination[0] = mp_obj_new_float(ctx->health);
            break;
        case MP_QSTR_max_health:
            destination[0] = mp_obj_new_float(ctx->max_health);
            break;
        case MP_QSTR_level:
            destination[0] = mp_obj_new_float(ctx->level);
            break;
        case MP_QSTR_xp:
            destination[0] = mp_obj_new_float(ctx->xp);
            break;
        case MP_QSTR_health_regen:
            destination[0] = mp_obj_new_float(ctx->health_regen);
            break;
        case MP_QSTR_elapsed_health_regen:
            destination[0] = mp_obj_new_float(ctx->elapsed_health_regen);
            break;
        case MP_QSTR_sprite_3d_type:
            destination[0] = mp_obj_new_int(ctx->sprite_3d_type);
            break;
        case MP_QSTR_sprite_rotation:
            destination[0] = mp_obj_new_float(ctx->sprite_rotation);
            break;
        case MP_QSTR_sprite_scale:
            destination[0] = mp_obj_new_float(ctx->sprite_scale);
            break;
        case MP_QSTR_sprite:
            destination[0] = self->sprite_obj;
            break;
        case MP_QSTR_sprite_left:
            destination[0] = self->sprite_left_obj;
            break;
        case MP_QSTR_sprite_right:
            destination[0] = self->sprite_right_obj;
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&entity_mp_del_obj);
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
            entity_mp_set_name(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_type:
            entity_mp_set_type(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_position:
            entity_mp_set_position(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_old_position:
            entity_mp_set_old_position(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_size:
            entity_mp_set_size(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_is_8bit:
            entity_mp_set_is_8bit(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_is_active:
            entity_mp_set_is_active(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_is_visible:
            entity_mp_set_is_visible(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_is_player:
            entity_mp_set_is_player(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_direction:
            entity_mp_set_direction(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_plane:
            entity_mp_set_plane(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_state:
            entity_mp_set_state(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_start_position:
            entity_mp_set_start_position(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_end_position:
            entity_mp_set_end_position(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_move_timer:
            entity_mp_set_move_timer(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_elapsed_move_timer:
            entity_mp_set_elapsed_move_timer(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_radius:
            entity_mp_set_radius(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_speed:
            entity_mp_set_speed(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_attack_timer:
            entity_mp_set_attack_timer(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_elapsed_attack_timer:
            entity_mp_set_elapsed_attack_timer(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_strength:
            entity_mp_set_strength(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_health:
            entity_mp_set_health(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_max_health:
            entity_mp_set_max_health(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_level:
            entity_mp_set_level(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_xp:
            entity_mp_set_xp(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_health_regen:
            entity_mp_set_health_regen(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_elapsed_health_regen:
            entity_mp_set_elapsed_health_regen(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_sprite_3d_type:
            entity_mp_set_sprite3d_type(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_sprite_3d:
            entity_mp_set_sprite3d(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_sprite_rotation:
            entity_mp_set_3d_sprite_rotation(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_sprite_scale:
            entity_mp_set_3d_sprite_scale(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_sprite:
            entity_mp_set_sprite(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_sprite_left:
            entity_mp_set_sprite_left(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_sprite_right:
            entity_mp_set_sprite_right(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        default:
            return; // Fail
        };
    }
}

mp_obj_t entity_mp_has_3d_sprite(mp_obj_t self_in)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    return mp_obj_new_bool(ctx->has3DSprite());
}
static MP_DEFINE_CONST_FUN_OBJ_1(entity_mp_has_3d_sprite_obj, entity_mp_has_3d_sprite);

mp_obj_t entity_mp_set_3d_sprite_rotation(mp_obj_t self_in, mp_obj_t rotation)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->set3DSpriteRotation(mp_obj_get_float(rotation));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_3d_sprite_rotation_obj, entity_mp_set_3d_sprite_rotation);

mp_obj_t entity_mp_set_3d_sprite_scale(mp_obj_t self_in, mp_obj_t scale)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->set3DSpriteScale(mp_obj_get_float(scale));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_3d_sprite_scale_obj, entity_mp_set_3d_sprite_scale);

mp_obj_t entity_mp_update_3d_sprite_position(mp_obj_t self_in)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->update3DSpritePosition();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(entity_mp_update_3d_sprite_position_obj, entity_mp_update_3d_sprite_position);

mp_obj_t entity_mp_has_changed_position(mp_obj_t self_in)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    return mp_obj_new_bool(ctx->hasChangedPosition());
}
static MP_DEFINE_CONST_FUN_OBJ_1(entity_mp_has_changed_position_obj, entity_mp_has_changed_position);

mp_obj_t entity_mp_set_name(mp_obj_t self_in, mp_obj_t name_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    size_t name_len;
    const char *name_str = mp_obj_str_get_data(name_obj, &name_len);
    char *name_buf = static_cast<char *>(m_malloc(name_len + 1));
    memcpy(name_buf, name_str, name_len);
    name_buf[name_len] = '\0';
    if (ctx->name != NULL)
    {
        m_free(const_cast<char *>(ctx->name));
    }
    ctx->name = name_buf;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_name_obj, entity_mp_set_name);

mp_obj_t entity_mp_set_type(mp_obj_t self_in, mp_obj_t type_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->type = static_cast<EntityType>(mp_obj_get_int(type_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_type_obj, entity_mp_set_type);

mp_obj_t entity_mp_set_position(mp_obj_t self_in, mp_obj_t position_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(position_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->position_set(vec->x, vec->y, vec->z, vec->integer);
    self->position_obj = position_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_position_obj, entity_mp_set_position);

mp_obj_t entity_mp_set_old_position(mp_obj_t self_in, mp_obj_t old_position_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(old_position_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->old_position.x = vec->x;
    ctx->old_position.y = vec->y;
    ctx->old_position.z = vec->z;
    ctx->old_position.integer = vec->integer;
    self->old_position_obj = old_position_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_old_position_obj, entity_mp_set_old_position);

mp_obj_t entity_mp_set_size(mp_obj_t self_in, mp_obj_t size_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
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
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_size_obj, entity_mp_set_size);

mp_obj_t entity_mp_set_is_8bit(mp_obj_t self_in, mp_obj_t is_8bit_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->is_8bit = mp_obj_is_true(is_8bit_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_is_8bit_obj, entity_mp_set_is_8bit);

mp_obj_t entity_mp_set_is_active(mp_obj_t self_in, mp_obj_t is_active_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->is_active = mp_obj_is_true(is_active_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_is_active_obj, entity_mp_set_is_active);

mp_obj_t entity_mp_set_is_visible(mp_obj_t self_in, mp_obj_t is_visible_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->is_visible = mp_obj_is_true(is_visible_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_is_visible_obj, entity_mp_set_is_visible);

mp_obj_t entity_mp_set_is_player(mp_obj_t self_in, mp_obj_t is_player_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->is_player = mp_obj_is_true(is_player_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_is_player_obj, entity_mp_set_is_player);

mp_obj_t entity_mp_set_direction(mp_obj_t self_in, mp_obj_t direction_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(direction_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->direction.x = vec->x;
    ctx->direction.y = vec->y;
    ctx->direction.z = vec->z;
    ctx->direction.integer = vec->integer;
    self->direction_obj = direction_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_direction_obj, entity_mp_set_direction);

mp_obj_t entity_mp_set_plane(mp_obj_t self_in, mp_obj_t plane_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(plane_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->plane.x = vec->x;
    ctx->plane.y = vec->y;
    ctx->plane.z = vec->z;
    ctx->plane.integer = vec->integer;
    self->plane_obj = plane_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_plane_obj, entity_mp_set_plane);

mp_obj_t entity_mp_set_state(mp_obj_t self_in, mp_obj_t state_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->state = static_cast<EntityState>(mp_obj_get_int(state_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_state_obj, entity_mp_set_state);

mp_obj_t entity_mp_set_start_position(mp_obj_t self_in, mp_obj_t start_position_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(start_position_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->start_position.x = vec->x;
    ctx->start_position.y = vec->y;
    ctx->start_position.z = vec->z;
    ctx->start_position.integer = vec->integer;
    self->start_position_obj = start_position_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_start_position_obj, entity_mp_set_start_position);

mp_obj_t entity_mp_set_end_position(mp_obj_t self_in, mp_obj_t end_position_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_vec = mp_obj_cast_to_native_base(end_position_obj, MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_vec == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
    vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
    ctx->end_position.x = vec->x;
    ctx->end_position.y = vec->y;
    ctx->end_position.z = vec->z;
    ctx->end_position.integer = vec->integer;
    self->end_position_obj = end_position_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_end_position_obj, entity_mp_set_end_position);

mp_obj_t entity_mp_set_move_timer(mp_obj_t self_in, mp_obj_t move_timer_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->move_timer = mp_obj_get_float(move_timer_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_move_timer_obj, entity_mp_set_move_timer);

mp_obj_t entity_mp_set_elapsed_move_timer(mp_obj_t self_in, mp_obj_t elapsed_move_timer_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->elapsed_move_timer = mp_obj_get_float(elapsed_move_timer_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_elapsed_move_timer_obj, entity_mp_set_elapsed_move_timer);

mp_obj_t entity_mp_set_radius(mp_obj_t self_in, mp_obj_t radius_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->radius = mp_obj_get_float(radius_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_radius_obj, entity_mp_set_radius);

mp_obj_t entity_mp_set_speed(mp_obj_t self_in, mp_obj_t speed_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->speed = mp_obj_get_float(speed_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_speed_obj, entity_mp_set_speed);

mp_obj_t entity_mp_set_attack_timer(mp_obj_t self_in, mp_obj_t attack_timer_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->attack_timer = mp_obj_get_float(attack_timer_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_attack_timer_obj, entity_mp_set_attack_timer);

mp_obj_t entity_mp_set_elapsed_attack_timer(mp_obj_t self_in, mp_obj_t elapsed_attack_timer_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->elapsed_attack_timer = mp_obj_get_float(elapsed_attack_timer_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_elapsed_attack_timer_obj, entity_mp_set_elapsed_attack_timer);

mp_obj_t entity_mp_set_strength(mp_obj_t self_in, mp_obj_t strength_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->strength = mp_obj_get_float(strength_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_strength_obj, entity_mp_set_strength);

mp_obj_t entity_mp_set_health(mp_obj_t self_in, mp_obj_t health_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->health = mp_obj_get_float(health_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_health_obj, entity_mp_set_health);

mp_obj_t entity_mp_set_max_health(mp_obj_t self_in, mp_obj_t max_health_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->max_health = mp_obj_get_float(max_health_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_max_health_obj, entity_mp_set_max_health);

mp_obj_t entity_mp_set_level(mp_obj_t self_in, mp_obj_t level_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->level = mp_obj_get_float(level_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_level_obj, entity_mp_set_level);

mp_obj_t entity_mp_set_xp(mp_obj_t self_in, mp_obj_t xp_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->xp = mp_obj_get_float(xp_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_xp_obj, entity_mp_set_xp);

mp_obj_t entity_mp_set_health_regen(mp_obj_t self_in, mp_obj_t health_regen_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->health_regen = mp_obj_get_float(health_regen_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_health_regen_obj, entity_mp_set_health_regen);

mp_obj_t entity_mp_set_elapsed_health_regen(mp_obj_t self_in, mp_obj_t elapsed_health_regen_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->elapsed_health_regen = mp_obj_get_float(elapsed_health_regen_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_elapsed_health_regen_obj, entity_mp_set_elapsed_health_regen);

mp_obj_t entity_mp_set_sprite_rotation(mp_obj_t self_in, mp_obj_t sprite_rotation_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->set3DSpriteRotation(mp_obj_get_float(sprite_rotation_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_sprite_rotation_obj, entity_mp_set_sprite_rotation);

mp_obj_t entity_mp_set_sprite_scale(mp_obj_t self_in, mp_obj_t sprite_scale_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->set3DSpriteScale(mp_obj_get_float(sprite_scale_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_sprite_scale_obj, entity_mp_set_sprite_scale);

mp_obj_t entity_mp_set_sprite3d_type(mp_obj_t self_in, mp_obj_t type_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    ctx->sprite_3d_type = static_cast<Sprite3DType>(mp_obj_get_int(type_obj));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_sprite3d_type_obj, entity_mp_set_sprite3d_type);

mp_obj_t entity_mp_set_sprite3d(mp_obj_t self_in, mp_obj_t sprite3d_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_sprite3d = mp_obj_cast_to_native_base(sprite3d_obj, MP_OBJ_FROM_PTR(&sprite3d_mp_type));
    if (native_sprite3d == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Sprite3D"));
    sprite3d_mp_obj_t *sprite3d = static_cast<sprite3d_mp_obj_t *>(MP_OBJ_TO_PTR(native_sprite3d));
    ctx->sprite_3d = static_cast<Sprite3D *>(sprite3d->context);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_sprite3d_obj, entity_mp_set_sprite3d);

mp_obj_t entity_mp_set_sprite(mp_obj_t self_in, mp_obj_t sprite_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_sprite = mp_obj_cast_to_native_base(sprite_obj, MP_OBJ_FROM_PTR(&image_mp_type));
    if (native_sprite == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Image"));
    image_mp_obj_t *img = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_sprite));
    ctx->sprite = static_cast<Image *>(img->context);
    self->sprite_obj = sprite_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_sprite_obj, entity_mp_set_sprite);

mp_obj_t entity_mp_set_sprite_left(mp_obj_t self_in, mp_obj_t sprite_left_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_sprite_left = mp_obj_cast_to_native_base(sprite_left_obj, MP_OBJ_FROM_PTR(&image_mp_type));
    if (native_sprite_left == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Image"));
    image_mp_obj_t *img_left = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_sprite_left));
    ctx->sprite_left = static_cast<Image *>(img_left->context);
    self->sprite_left_obj = sprite_left_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_sprite_left_obj, entity_mp_set_sprite_left);

mp_obj_t entity_mp_set_sprite_right(mp_obj_t self_in, mp_obj_t sprite_right_obj)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(MP_OBJ_TO_PTR(self_in));
    Entity *ctx = entity_get_context(self);
    mp_obj_t native_sprite_right = mp_obj_cast_to_native_base(sprite_right_obj, MP_OBJ_FROM_PTR(&image_mp_type));
    if (native_sprite_right == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Image"));
    image_mp_obj_t *img_right = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_sprite_right));
    ctx->sprite_right = static_cast<Image *>(img_right->context);
    self->sprite_right_obj = sprite_right_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(entity_mp_set_sprite_right_obj, entity_mp_set_sprite_right);

static const mp_rom_map_elem_t entity_mp_locals_dict_table[] = {
    // Methods
    {MP_ROM_QSTR(MP_QSTR_has_3d_sprite), MP_ROM_PTR(&entity_mp_has_3d_sprite_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_3d_sprite_rotation), MP_ROM_PTR(&entity_mp_set_3d_sprite_rotation_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_3d_sprite_scale), MP_ROM_PTR(&entity_mp_set_3d_sprite_scale_obj)},
    {MP_ROM_QSTR(MP_QSTR_update_3d_sprite_position), MP_ROM_PTR(&entity_mp_update_3d_sprite_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_changed_position), MP_ROM_PTR(&entity_mp_has_changed_position_obj)},
    //
    {MP_ROM_QSTR(MP_QSTR_set_name), MP_ROM_PTR(&entity_mp_set_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_type), MP_ROM_PTR(&entity_mp_set_type_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_position), MP_ROM_PTR(&entity_mp_set_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_old_position), MP_ROM_PTR(&entity_mp_set_old_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_size), MP_ROM_PTR(&entity_mp_set_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_is_8bit), MP_ROM_PTR(&entity_mp_set_is_8bit_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_is_active), MP_ROM_PTR(&entity_mp_set_is_active_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_is_visible), MP_ROM_PTR(&entity_mp_set_is_visible_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_is_player), MP_ROM_PTR(&entity_mp_set_is_player_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_direction), MP_ROM_PTR(&entity_mp_set_direction_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_plane), MP_ROM_PTR(&entity_mp_set_plane_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_state), MP_ROM_PTR(&entity_mp_set_state_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_start_position), MP_ROM_PTR(&entity_mp_set_start_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_end_position), MP_ROM_PTR(&entity_mp_set_end_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_move_timer), MP_ROM_PTR(&entity_mp_set_move_timer_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_elapsed_move_timer), MP_ROM_PTR(&entity_mp_set_elapsed_move_timer_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_radius), MP_ROM_PTR(&entity_mp_set_radius_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_speed), MP_ROM_PTR(&entity_mp_set_speed_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_attack_timer), MP_ROM_PTR(&entity_mp_set_attack_timer_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_elapsed_attack_timer), MP_ROM_PTR(&entity_mp_set_elapsed_attack_timer_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_strength), MP_ROM_PTR(&entity_mp_set_strength_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_health), MP_ROM_PTR(&entity_mp_set_health_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_max_health), MP_ROM_PTR(&entity_mp_set_max_health_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_level), MP_ROM_PTR(&entity_mp_set_level_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_xp), MP_ROM_PTR(&entity_mp_set_xp_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_health_regen), MP_ROM_PTR(&entity_mp_set_health_regen_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_elapsed_health_regen), MP_ROM_PTR(&entity_mp_set_elapsed_health_regen_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_sprite_rotation), MP_ROM_PTR(&entity_mp_set_sprite_rotation_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_sprite_scale), MP_ROM_PTR(&entity_mp_set_sprite_scale_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_sprite3d_type), MP_ROM_PTR(&entity_mp_set_sprite3d_type_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_sprite3d), MP_ROM_PTR(&entity_mp_set_sprite3d_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_sprite), MP_ROM_PTR(&entity_mp_set_sprite_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_sprite_left), MP_ROM_PTR(&entity_mp_set_sprite_left_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_sprite_right), MP_ROM_PTR(&entity_mp_set_sprite_right_obj)},

    // Entity type constants
    {MP_ROM_QSTR(MP_QSTR_ENTITY_PLAYER), MP_ROM_INT(ENTITY_PLAYER)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_ENEMY), MP_ROM_INT(ENTITY_ENEMY)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_ICON), MP_ROM_INT(ENTITY_ICON)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_NPC), MP_ROM_INT(ENTITY_NPC)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_3D_SPRITE), MP_ROM_INT(ENTITY_3D_SPRITE)},

    // Entity state constants
    {MP_ROM_QSTR(MP_QSTR_ENTITY_IDLE), MP_ROM_INT(ENTITY_IDLE)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_MOVING), MP_ROM_INT(ENTITY_MOVING)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_MOVING_TO_START), MP_ROM_INT(ENTITY_MOVING_TO_START)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_MOVING_TO_END), MP_ROM_INT(ENTITY_MOVING_TO_END)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_ATTACKING), MP_ROM_INT(ENTITY_ATTACKING)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_ATTACKED), MP_ROM_INT(ENTITY_ATTACKED)},
    {MP_ROM_QSTR(MP_QSTR_ENTITY_DEAD), MP_ROM_INT(ENTITY_DEAD)},

    // Sprite 3D type constants
    {MP_ROM_QSTR(MP_QSTR_SPRITE_3D_NONE), MP_ROM_INT(SPRITE_3D_NONE)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_3D_HUMANOID), MP_ROM_INT(SPRITE_3D_HUMANOID)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_3D_TREE), MP_ROM_INT(SPRITE_3D_TREE)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_3D_HOUSE), MP_ROM_INT(SPRITE_3D_HOUSE)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_3D_PILLAR), MP_ROM_INT(SPRITE_3D_PILLAR)},
    {MP_ROM_QSTR(MP_QSTR_SPRITE_3D_CUSTOM), MP_ROM_INT(SPRITE_3D_CUSTOM)},
};
static MP_DEFINE_CONST_DICT(entity_mp_locals_dict, entity_mp_locals_dict_table);

extern "C"
{
    const mp_obj_type_t entity_mp_type = {
        .base = {&mp_type_type},
        .flags = MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
        .name = MP_QSTR_Entity,
        .slot_index_make_new = 1,
        .slot_index_print = 2,
        .slot_index_attr = 3,
        .slot_index_locals_dict = 4,
        .slots = {
            (const void *)entity_mp_make_new,
            (const void *)entity_mp_print,
            (const void *)entity_mp_attr,
            (const void *)&entity_mp_locals_dict,
        },
    };
}
