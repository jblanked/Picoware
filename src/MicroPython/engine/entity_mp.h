#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

#include "sprite3d_mp.h"

// entity state
typedef enum
{
    ENTITY_STATE_IDLE = 0,
    ENTITY_STATE_MOVING,
    ENTITY_STATE_MOVING_TO_START,
    ENTITY_STATE_MOVING_TO_END,
    ENTITY_STATE_ATTACKING,
    ENTITY_STATE_ATTACKED,
    ENTITY_STATE_DEAD
} EntityState;

// entity type
typedef enum
{
    ENTITY_TYPE_PLAYER = 0,
    ENTITY_TYPE_ENEMY,
    ENTITY_TYPE_ICON,
    ENTITY_TYPE_NPC,
    ENTITY_TYPE_3D_SPRITE
} EntityType;

typedef struct
{
    mp_obj_base_t base;
    char *name;
    EntityType type;
    mp_obj_t position;
    mp_obj_t old_position;
    mp_obj_t size;
    bool is_8bit;
    bool is_active;
    bool is_visible;
    bool is_player;
    mp_obj_t direction;
    mp_obj_t plane;
    EntityState state;
    mp_obj_t start_position;
    mp_obj_t end_position;
    float move_timer;
    float elapsed_move_timer;
    float radius;
    float speed;
    float attack_timer;
    float elapsed_attack_timer;
    float strength;
    float health;
    float max_health;
    float level;
    float xp;
    float health_regen;
    float elapsed_health_regen;
    mp_obj_t sprite_3d;
    Sprite3DType sprite_3d_type;
    float sprite_rotation;
    float sprite_scale;
    bool freed;
} entity_mp_obj_t;

extern const mp_obj_type_t entity_mp_type;

void entity_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t entity_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t entity_mp_del(mp_obj_t self_in);
void entity_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
mp_obj_t entity_mp_has_3d_sprite(mp_obj_t self_in);
mp_obj_t entity_mp_project_3d_to_2d(size_t n_args, const mp_obj_t *args);
