#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "../mjs.h"

    mjs_val_t entity_get_name(struct mjs *mjs);
    mjs_val_t entity_get_type(struct mjs *mjs);
    mjs_val_t entity_get_state(struct mjs *mjs);
    mjs_val_t entity_get_position(struct mjs *mjs);
    mjs_val_t entity_get_old_position(struct mjs *mjs);
    mjs_val_t entity_get_size(struct mjs *mjs);
    mjs_val_t entity_get_direction(struct mjs *mjs);
    mjs_val_t entity_get_plane(struct mjs *mjs);
    mjs_val_t entity_get_start_position(struct mjs *mjs);
    mjs_val_t entity_get_end_position(struct mjs *mjs);
    mjs_val_t entity_get_aabb_min(struct mjs *mjs);
    mjs_val_t entity_get_aabb_max(struct mjs *mjs);
    mjs_val_t entity_get_is_8bit(struct mjs *mjs);
    mjs_val_t entity_get_is_active(struct mjs *mjs);
    mjs_val_t entity_get_is_visible(struct mjs *mjs);
    mjs_val_t entity_get_is_player(struct mjs *mjs);
    mjs_val_t entity_get_aabb_dirty(struct mjs *mjs);
    mjs_val_t entity_get_moved(struct mjs *mjs);
    mjs_val_t entity_get_move_timer(struct mjs *mjs);
    mjs_val_t entity_get_elapsed_move_timer(struct mjs *mjs);
    mjs_val_t entity_get_radius(struct mjs *mjs);
    mjs_val_t entity_get_speed(struct mjs *mjs);
    mjs_val_t entity_get_attack_timer(struct mjs *mjs);
    mjs_val_t entity_get_elapsed_attack_timer(struct mjs *mjs);
    mjs_val_t entity_get_strength(struct mjs *mjs);
    mjs_val_t entity_get_health(struct mjs *mjs);
    mjs_val_t entity_get_max_health(struct mjs *mjs);
    mjs_val_t entity_get_level(struct mjs *mjs);
    mjs_val_t entity_get_xp(struct mjs *mjs);
    mjs_val_t entity_get_health_regen(struct mjs *mjs);
    mjs_val_t entity_get_elapsed_health_regen(struct mjs *mjs);
    mjs_val_t entity_get_sprite_rotation(struct mjs *mjs);
    mjs_val_t entity_get_sprite_scale(struct mjs *mjs);
    mjs_val_t entity_get_sprite_3d_type(struct mjs *mjs);
    mjs_val_t entity_get_billboard_pose(struct mjs *mjs);
    mjs_val_t entity_get_billboard_world_height(struct mjs *mjs);
    mjs_val_t entity_get_has_3d_sprite(struct mjs *mjs);
    mjs_val_t entity_get_has_changed_position(struct mjs *mjs);

    void entity_set(struct mjs *mjs);
    void entity_update_position(struct mjs *mjs);

    void entity_create(struct mjs *mjs, mjs_val_t *entity_obj);
    void entity_destroy();

#ifdef __cplusplus
}
#endif