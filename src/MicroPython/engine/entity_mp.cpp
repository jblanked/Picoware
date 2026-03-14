#include "entity_mp.h"
#include "game_mp.h"
#include "image_mp.h"
#include "engine/entity.hpp"

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

// Trampoline functions for entity callbacks
static void entity_start_trampoline(Entity *e, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);
    game_mp_obj_t *game_obj = mp_obj_malloc(game_mp_obj_t, &game_mp_type);
    game_obj->context = g;
    game_obj->freed = false;
    game_obj->start = mp_const_none;
    game_obj->stop = mp_const_none;
    game_obj->update = mp_const_none;
    game_obj->draw = game_mp_get_current_draw();
    mp_call_function_2(self->start, MP_OBJ_FROM_PTR(self), MP_OBJ_FROM_PTR(game_obj));
}
static void entity_stop_trampoline(Entity *e, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);
    game_mp_obj_t *game_obj = mp_obj_malloc(game_mp_obj_t, &game_mp_type);
    game_obj->context = g;
    game_obj->freed = false;
    game_obj->start = mp_const_none;
    game_obj->stop = mp_const_none;
    game_obj->update = mp_const_none;
    game_obj->draw = game_mp_get_current_draw();
    mp_call_function_2(self->stop, MP_OBJ_FROM_PTR(self), MP_OBJ_FROM_PTR(game_obj));
}
static void entity_update_trampoline(Entity *e, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);
    game_mp_obj_t *game_obj = mp_obj_malloc(game_mp_obj_t, &game_mp_type);
    game_obj->context = g;
    game_obj->freed = false;
    game_obj->start = mp_const_none;
    game_obj->stop = mp_const_none;
    game_obj->update = mp_const_none;
    game_obj->draw = game_mp_get_current_draw();
    mp_call_function_2(self->update, MP_OBJ_FROM_PTR(self), MP_OBJ_FROM_PTR(game_obj));
}
static void entity_render_trampoline(Entity *e, Draw *d, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);
    game_mp_obj_t *game_obj = mp_obj_malloc(game_mp_obj_t, &game_mp_type);
    game_obj->context = g;
    game_obj->freed = false;
    game_obj->start = mp_const_none;
    game_obj->stop = mp_const_none;
    game_obj->update = mp_const_none;
    game_obj->draw = game_mp_get_current_draw();
    mp_call_function_2(self->render, MP_OBJ_FROM_PTR(self), MP_OBJ_FROM_PTR(game_obj));
}
static void entity_collision_trampoline(Entity *e, Entity *other, Game *g, void *ctx)
{
    entity_mp_obj_t *self = static_cast<entity_mp_obj_t *>(ctx);
    game_mp_obj_t *game_obj = mp_obj_malloc(game_mp_obj_t, &game_mp_type);
    game_obj->context = g;
    game_obj->freed = false;
    game_obj->start = mp_const_none;
    game_obj->stop = mp_const_none;
    game_obj->update = mp_const_none;
    game_obj->draw = game_mp_get_current_draw();
    mp_call_function_2(self->collision, MP_OBJ_FROM_PTR(self), MP_OBJ_FROM_PTR(game_obj));
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
    mp_obj_t native_size = mp_obj_cast_to_native_base(args[3], MP_OBJ_FROM_PTR(&vector_mp_type));
    if (native_size == MP_OBJ_NULL)
        mp_raise_TypeError(MP_ERROR_TEXT("expected Vector for size"));
    vector_mp_obj_t *size_vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_size));
    Vector size(size_vec->x, size_vec->y, size_vec->z, size_vec->integer);

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
        start_func = {entity_start_trampoline, self};
    }
    if (n_args > 8 && mp_obj_is_callable(args[8]))
    {
        self->stop = args[8];
        stop_func = {entity_stop_trampoline, self};
    }
    if (n_args > 9 && mp_obj_is_callable(args[9]))
    {
        self->update = args[9];
        update_func = {entity_update_trampoline, self};
    }
    if (n_args > 10 && mp_obj_is_callable(args[10]))
    {
        self->render = args[10];
        render_func = {entity_render_trampoline, self};
    }
    if (n_args > 11 && mp_obj_is_callable(args[11]))
    {
        self->collision = args[11];
        collision_func = {entity_collision_trampoline, self};
    }

    // Extract Image* from image_mp_obj_t for sprite args (handles Python subclass wrappers)
    Image *sprite_data = nullptr;
    Image *sprite_left_data = nullptr;
    Image *sprite_right_data = nullptr;
    if (n_args > 4 && args[4] != mp_const_none)
    {
        mp_obj_t native_img = mp_obj_cast_to_native_base(args[4], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native_img == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Image for sprite_data"));
        image_mp_obj_t *img = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_img));
        sprite_data = static_cast<Image *>(img->context);
    }
    if (n_args > 5 && args[5] != mp_const_none)
    {
        mp_obj_t native_img = mp_obj_cast_to_native_base(args[5], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native_img == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Image for sprite_left"));
        image_mp_obj_t *img = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_img));
        sprite_left_data = static_cast<Image *>(img->context);
    }
    if (n_args > 6 && args[6] != mp_const_none)
    {
        mp_obj_t native_img = mp_obj_cast_to_native_base(args[6], MP_OBJ_FROM_PTR(&image_mp_type));
        if (native_img == MP_OBJ_NULL)
            mp_raise_TypeError(MP_ERROR_TEXT("expected Image for sprite_right"));
        image_mp_obj_t *img = static_cast<image_mp_obj_t *>(MP_OBJ_TO_PTR(native_img));
        sprite_right_data = static_cast<Image *>(img->context);
    }

    // Create the C++ Entity — all state lives in this single context
    self->context = new Entity(
        name_buf, entity_type, position, size,
        sprite_data, sprite_left_data, sprite_right_data,
        start_func, stop_func, update_func,
        render_func, collision_func,
        is_8bit, s3d_type, s3d_color);

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
    // Free the name buffer we allocated in make_new (Entity doesn't own it)
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
        if (attribute == MP_QSTR_name)
        {
            destination[0] = mp_obj_new_str(ctx->name, strlen(ctx->name));
        }
        else if (attribute == MP_QSTR_type)
        {
            destination[0] = mp_obj_new_int(ctx->type);
        }
        else if (attribute == MP_QSTR_position)
        {
            destination[0] = vector_mp_init(ctx->position.x, ctx->position.y, ctx->position.z, ctx->position.integer);
        }
        else if (attribute == MP_QSTR_old_position)
        {
            destination[0] = vector_mp_init(ctx->old_position.x, ctx->old_position.y, ctx->old_position.z, ctx->old_position.integer);
        }
        else if (attribute == MP_QSTR_size)
        {
            destination[0] = vector_mp_init(ctx->size.x, ctx->size.y, ctx->size.z, ctx->size.integer);
        }
        else if (attribute == MP_QSTR_is_8bit)
        {
            destination[0] = mp_obj_new_bool(ctx->is_8bit);
        }
        else if (attribute == MP_QSTR_is_active)
        {
            destination[0] = mp_obj_new_bool(ctx->is_active);
        }
        else if (attribute == MP_QSTR_is_visible)
        {
            destination[0] = mp_obj_new_bool(ctx->is_visible);
        }
        else if (attribute == MP_QSTR_is_player)
        {
            destination[0] = mp_obj_new_bool(ctx->is_player);
        }
        else if (attribute == MP_QSTR_direction)
        {
            destination[0] = vector_mp_init(ctx->direction.x, ctx->direction.y, ctx->direction.z, ctx->direction.integer);
        }
        else if (attribute == MP_QSTR_plane)
        {
            destination[0] = vector_mp_init(ctx->plane.x, ctx->plane.y, ctx->plane.z, ctx->plane.integer);
        }
        else if (attribute == MP_QSTR_state)
        {
            destination[0] = mp_obj_new_int(ctx->state);
        }
        else if (attribute == MP_QSTR_start_position)
        {
            destination[0] = vector_mp_init(ctx->start_position.x, ctx->start_position.y, ctx->start_position.z, ctx->start_position.integer);
        }
        else if (attribute == MP_QSTR_end_position)
        {
            destination[0] = vector_mp_init(ctx->end_position.x, ctx->end_position.y, ctx->end_position.z, ctx->end_position.integer);
        }
        else if (attribute == MP_QSTR_move_timer)
        {
            destination[0] = mp_obj_new_float(ctx->move_timer);
        }
        else if (attribute == MP_QSTR_elapsed_move_timer)
        {
            destination[0] = mp_obj_new_float(ctx->elapsed_move_timer);
        }
        else if (attribute == MP_QSTR_radius)
        {
            destination[0] = mp_obj_new_float(ctx->radius);
        }
        else if (attribute == MP_QSTR_speed)
        {
            destination[0] = mp_obj_new_float(ctx->speed);
        }
        else if (attribute == MP_QSTR_attack_timer)
        {
            destination[0] = mp_obj_new_float(ctx->attack_timer);
        }
        else if (attribute == MP_QSTR_elapsed_attack_timer)
        {
            destination[0] = mp_obj_new_float(ctx->elapsed_attack_timer);
        }
        else if (attribute == MP_QSTR_strength)
        {
            destination[0] = mp_obj_new_float(ctx->strength);
        }
        else if (attribute == MP_QSTR_health)
        {
            destination[0] = mp_obj_new_float(ctx->health);
        }
        else if (attribute == MP_QSTR_max_health)
        {
            destination[0] = mp_obj_new_float(ctx->max_health);
        }
        else if (attribute == MP_QSTR_level)
        {
            destination[0] = mp_obj_new_float(ctx->level);
        }
        else if (attribute == MP_QSTR_xp)
        {
            destination[0] = mp_obj_new_float(ctx->xp);
        }
        else if (attribute == MP_QSTR_health_regen)
        {
            destination[0] = mp_obj_new_float(ctx->health_regen);
        }
        else if (attribute == MP_QSTR_elapsed_health_regen)
        {
            destination[0] = mp_obj_new_float(ctx->elapsed_health_regen);
        }
        else if (attribute == MP_QSTR_sprite_3d_type)
        {
            destination[0] = mp_obj_new_int(ctx->sprite_3d_type);
        }
        else if (attribute == MP_QSTR_sprite_rotation)
        {
            destination[0] = mp_obj_new_float(ctx->sprite_rotation);
        }
        else if (attribute == MP_QSTR_sprite_scale)
        {
            destination[0] = mp_obj_new_float(ctx->sprite_scale);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&entity_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        Entity *ctx = entity_get_context(self);
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
        else if (attribute == MP_QSTR_type)
        {
            ctx->type = static_cast<EntityType>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_position)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->position_set(vec->x, vec->y, vec->z, vec->integer);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_old_position)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->old_position.x = vec->x;
            ctx->old_position.y = vec->y;
            ctx->old_position.z = vec->z;
            ctx->old_position.integer = vec->integer;
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
        else if (attribute == MP_QSTR_is_8bit)
        {
            ctx->is_8bit = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_active)
        {
            ctx->is_active = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_visible)
        {
            ctx->is_visible = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_player)
        {
            ctx->is_player = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_direction)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->direction.x = vec->x;
            ctx->direction.y = vec->y;
            ctx->direction.z = vec->z;
            ctx->direction.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_plane)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->plane.x = vec->x;
            ctx->plane.y = vec->y;
            ctx->plane.z = vec->z;
            ctx->plane.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_state)
        {
            ctx->state = static_cast<EntityState>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_start_position)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->start_position.x = vec->x;
            ctx->start_position.y = vec->y;
            ctx->start_position.z = vec->z;
            ctx->start_position.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_end_position)
        {
            mp_obj_t native_vec = mp_obj_cast_to_native_base(destination[1], MP_OBJ_FROM_PTR(&vector_mp_type));
            if (native_vec == MP_OBJ_NULL)
                mp_raise_TypeError(MP_ERROR_TEXT("expected Vector"));
            vector_mp_obj_t *vec = static_cast<vector_mp_obj_t *>(MP_OBJ_TO_PTR(native_vec));
            ctx->end_position.x = vec->x;
            ctx->end_position.y = vec->y;
            ctx->end_position.z = vec->z;
            ctx->end_position.integer = vec->integer;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_move_timer)
        {
            ctx->move_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_elapsed_move_timer)
        {
            ctx->elapsed_move_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_radius)
        {
            ctx->radius = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_speed)
        {
            ctx->speed = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_attack_timer)
        {
            ctx->attack_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_elapsed_attack_timer)
        {
            ctx->elapsed_attack_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_strength)
        {
            ctx->strength = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_health)
        {
            ctx->health = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_max_health)
        {
            ctx->max_health = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_level)
        {
            ctx->level = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_xp)
        {
            ctx->xp = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_health_regen)
        {
            ctx->health_regen = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_elapsed_health_regen)
        {
            ctx->elapsed_health_regen = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_sprite_3d_type)
        {
            ctx->sprite_3d_type = static_cast<Sprite3DType>(mp_obj_get_int(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_sprite_rotation)
        {
            ctx->set3DSpriteRotation(mp_obj_get_float(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_sprite_scale)
        {
            ctx->set3DSpriteScale(mp_obj_get_float(destination[1]));
            destination[0] = MP_OBJ_NULL;
        }
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

static const mp_rom_map_elem_t entity_mp_locals_dict_table[] = {
    // Methods
    {MP_ROM_QSTR(MP_QSTR_has_3d_sprite), MP_ROM_PTR(&entity_mp_has_3d_sprite_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_3d_sprite_rotation), MP_ROM_PTR(&entity_mp_set_3d_sprite_rotation_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_3d_sprite_scale), MP_ROM_PTR(&entity_mp_set_3d_sprite_scale_obj)},
    {MP_ROM_QSTR(MP_QSTR_update_3d_sprite_position), MP_ROM_PTR(&entity_mp_update_3d_sprite_position_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_changed_position), MP_ROM_PTR(&entity_mp_has_changed_position_obj)},

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
