/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "sprite3d_mp.h"
#include "engine_mp.h"

    typedef struct
    {
        mp_obj_base_t base;
        void *context; // Entity* in C++
        bool freed;
        mp_obj_t start;
        mp_obj_t stop;
        mp_obj_t update;
        mp_obj_t render;
        mp_obj_t collision;
        //
        mp_obj_t position_obj;
        mp_obj_t old_position_obj;
        mp_obj_t size_obj;
        mp_obj_t direction_obj;
        mp_obj_t plane_obj;
        mp_obj_t start_position_obj;
        mp_obj_t end_position_obj;
    } entity_mp_obj_t;

    extern const mp_obj_type_t entity_mp_type;

    void entity_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t entity_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t entity_mp_del(mp_obj_t self_in);
    void entity_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);

    mp_obj_t entity_mp_has_3d_sprite(mp_obj_t self_in);
    mp_obj_t entity_mp_set_3d_sprite_rotation(mp_obj_t self_in, mp_obj_t rotation);
    mp_obj_t entity_mp_set_3d_sprite_scale(mp_obj_t self_in, mp_obj_t scale);
    mp_obj_t entity_mp_update_3d_sprite_position(mp_obj_t self_in);

    mp_obj_t entity_mp_has_changed_position(mp_obj_t self_in);

    mp_obj_t entity_mp_set_name(mp_obj_t self_in, mp_obj_t name_obj);
    mp_obj_t entity_mp_set_type(mp_obj_t self_in, mp_obj_t type_obj);
    mp_obj_t entity_mp_set_position(mp_obj_t self_in, mp_obj_t position_obj);
    mp_obj_t entity_mp_set_old_position(mp_obj_t self_in, mp_obj_t old_position_obj);
    mp_obj_t entity_mp_set_size(mp_obj_t self_in, mp_obj_t size_obj);
    mp_obj_t entity_mp_set_is_8bit(mp_obj_t self_in, mp_obj_t is_8bit_obj);
    mp_obj_t entity_mp_set_is_active(mp_obj_t self_in, mp_obj_t is_active_obj);
    mp_obj_t entity_mp_set_is_visible(mp_obj_t self_in, mp_obj_t is_visible_obj);
    mp_obj_t entity_mp_set_is_player(mp_obj_t self_in, mp_obj_t is_player_obj);
    mp_obj_t entity_mp_set_direction(mp_obj_t self_in, mp_obj_t direction_obj);
    mp_obj_t entity_mp_set_plane(mp_obj_t self_in, mp_obj_t plane_obj);
    mp_obj_t entity_mp_set_state(mp_obj_t self_in, mp_obj_t state_obj);
    mp_obj_t entity_mp_set_start_position(mp_obj_t self_in, mp_obj_t start_position_obj);
    mp_obj_t entity_mp_set_end_position(mp_obj_t self_in, mp_obj_t end_position_obj);
    mp_obj_t entity_mp_set_move_timer(mp_obj_t self_in, mp_obj_t move_timer_obj);
    mp_obj_t entity_mp_set_elapsed_move_timer(mp_obj_t self_in, mp_obj_t elapsed_move_timer_obj);
    mp_obj_t entity_mp_set_radius(mp_obj_t self_in, mp_obj_t radius_obj);
    mp_obj_t entity_mp_set_speed(mp_obj_t self_in, mp_obj_t speed_obj);
    mp_obj_t entity_mp_set_attack_timer(mp_obj_t self_in, mp_obj_t attack_timer_obj);
    mp_obj_t entity_mp_set_elapsed_attack_timer(mp_obj_t self_in, mp_obj_t elapsed_attack_timer_obj);
    mp_obj_t entity_mp_set_strength(mp_obj_t self_in, mp_obj_t strength_obj);
    mp_obj_t entity_mp_set_health(mp_obj_t self_in, mp_obj_t health_obj);
    mp_obj_t entity_mp_set_max_health(mp_obj_t self_in, mp_obj_t max_health_obj);
    mp_obj_t entity_mp_set_level(mp_obj_t self_in, mp_obj_t level_obj);
    mp_obj_t entity_mp_set_xp(mp_obj_t self_in, mp_obj_t xp_obj);
    mp_obj_t entity_mp_set_health_regen(mp_obj_t self_in, mp_obj_t health_regen_obj);
    mp_obj_t entity_mp_set_elapsed_health_regen(mp_obj_t self_in, mp_obj_t elapsed_health_regen_obj);
    mp_obj_t entity_mp_set_sprite_rotation(mp_obj_t self_in, mp_obj_t sprite_rotation_obj);
    mp_obj_t entity_mp_set_sprite_scale(mp_obj_t self_in, mp_obj_t sprite_scale_obj);

#ifdef __cplusplus
}
#endif