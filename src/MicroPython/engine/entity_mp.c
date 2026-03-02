#include "entity_mp.h"
#include "engine_mp.h"

const mp_obj_type_t entity_mp_type;

void entity_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    entity_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Entity(");
    mp_print_str(print, "name=");
    mp_obj_print_helper(print, mp_obj_new_str(self->name, strlen(self->name)), PRINT_REPR);
    mp_print_str(print, ", type=");
    switch (self->type)
    {
    case ENTITY_TYPE_PLAYER:
        mp_print_str(print, "PLAYER");
        break;
    case ENTITY_TYPE_ENEMY:
        mp_print_str(print, "ENEMY");
        break;
    case ENTITY_TYPE_ICON:
        mp_print_str(print, "ICON");
        break;
    case ENTITY_TYPE_NPC:
        mp_print_str(print, "NPC");
        break;
    case ENTITY_TYPE_3D_SPRITE:
        mp_print_str(print, "SPRITE_3D");
        break;
    default:
        mp_print_str(print, "UNKNOWN");
        break;
    }
    mp_print_str(print, ", position=(");
    vector_mp_obj_t *pos_vec = MP_OBJ_TO_PTR(self->position);
    mp_obj_print_helper(print, mp_obj_new_float(pos_vec->x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(pos_vec->y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(pos_vec->z), PRINT_REPR);
    mp_print_str(print, "), size=(");
    vector_mp_obj_t *size_vec = MP_OBJ_TO_PTR(self->size);
    mp_obj_print_helper(print, mp_obj_new_float(size_vec->x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(size_vec->y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(size_vec->z), PRINT_REPR);
    mp_print_str(print, "), is_8bit=");
    mp_obj_print_helper(print, mp_obj_new_bool(self->is_8bit), PRINT_REPR);
    mp_print_str(print, ", is_active=");
    mp_obj_print_helper(print, mp_obj_new_bool(self->is_active), PRINT_REPR);
    mp_print_str(print, ", is_visible=");
    mp_obj_print_helper(print, mp_obj_new_bool(self->is_visible), PRINT_REPR);
    mp_print_str(print, ", is_player=");
    mp_obj_print_helper(print, mp_obj_new_bool(self->is_player), PRINT_REPR);
    mp_print_str(print, ", direction=(");
    vector_mp_obj_t *dir_vec = MP_OBJ_TO_PTR(self->direction);
    mp_obj_print_helper(print, mp_obj_new_float(dir_vec->x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(dir_vec->y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(dir_vec->z), PRINT_REPR);
    mp_print_str(print, "), plane=(");
    vector_mp_obj_t *plane_vec = MP_OBJ_TO_PTR(self->plane);
    mp_obj_print_helper(print, mp_obj_new_float(plane_vec->x), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(plane_vec->y), PRINT_REPR);
    mp_print_str(print, ", ");
    mp_obj_print_helper(print, mp_obj_new_float(plane_vec->z), PRINT_REPR);
    mp_print_str(print, "), state=");
    switch (self->state)
    {
    case ENTITY_STATE_IDLE:
        mp_print_str(print, "IDLE");
        break;
    case ENTITY_STATE_MOVING:
        mp_print_str(print, "MOVING");
        break;
    case ENTITY_STATE_MOVING_TO_START:
        mp_print_str(print, "MOVING_TO_START");
        break;
    case ENTITY_STATE_MOVING_TO_END:
        mp_print_str(print, "MOVING_TO_END");
        break;
    case ENTITY_STATE_ATTACKING:
        mp_print_str(print, "ATTACKING");
        break;
    case ENTITY_STATE_ATTACKED:
        mp_print_str(print, "ATTACKED");
        break;
    case ENTITY_STATE_DEAD:
        mp_print_str(print, "DEAD");
        break;
    default:
        mp_print_str(print, "UNKNOWN");
        break;
    }
    mp_print_str(print, ", health=");
    mp_obj_print_helper(print, mp_obj_new_float(self->health), PRINT_REPR);
    mp_print_str(print, ", max_health=");
    mp_obj_print_helper(print, mp_obj_new_float(self->max_health), PRINT_REPR);
    mp_print_str(print, ", level=");
    mp_obj_print_helper(print, mp_obj_new_float(self->level), PRINT_REPR);
    mp_print_str(print, ", xp=");
    mp_obj_print_helper(print, mp_obj_new_float(self->xp), PRINT_REPR);
    mp_print_str(print, ", health_regen=");
    mp_obj_print_helper(print, mp_obj_new_float(self->health_regen), PRINT_REPR);
    mp_print_str(print, ", elapsed_health_regen=");
    mp_obj_print_helper(print, mp_obj_new_float(self->elapsed_health_regen), PRINT_REPR);
    mp_print_str(print, ", sprite_3d_type=");
    switch (self->sprite_3d_type)
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
    mp_obj_print_helper(print, mp_obj_new_float(self->sprite_rotation), PRINT_REPR);
    mp_print_str(print, ", sprite_scale=");
    mp_obj_print_helper(print, mp_obj_new_float(self->sprite_scale), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t entity_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // name (str), type (EntityType), position (Vector), size (Vector), sprite_3d_type (Sprite3DType), is_8bit (bool)
    // required: name, type, position, size
    mp_arg_check_num(n_args, n_kw, 4, 6, true);
    //
    entity_mp_obj_t *self = mp_obj_malloc_with_finaliser(entity_mp_obj_t, &entity_mp_type);
    self->base.type = &entity_mp_type;
    self->freed = false;
    self->name = NULL;
    if (n_args > 0)
    {
        size_t name_len;
        const char *name_str = mp_obj_str_get_data(args[0], &name_len);
        self->name = m_malloc(name_len + 1);
        if (self->name != NULL)
        {
            memcpy(self->name, name_str, name_len);
            self->name[name_len] = '\0';
        }
    }
    self->type = n_args > 1 ? mp_obj_get_int(args[1]) : ENTITY_TYPE_PLAYER;
    //
    if (n_args > 2)
    {
        self->position = args[2];
        self->old_position = args[2];
        self->start_position = args[2];
        self->end_position = args[2];
    }
    else
    {
        self->position = MP_OBJ_NULL;
        self->old_position = MP_OBJ_NULL;
        self->start_position = MP_OBJ_NULL;
        self->end_position = MP_OBJ_NULL;
    }
    //
    if (n_args > 3)
    {
        self->size = args[3];
        vector_mp_obj_t *size_vec = MP_OBJ_TO_PTR(self->size);
        self->radius = size_vec->x / 2.0f;
    }
    else
    {
        self->size = MP_OBJ_NULL;
        self->radius = 0.0f;
    }
    self->is_8bit = n_args > 5 ? mp_obj_is_true(args[5]) : false;
    self->is_active = true;
    self->is_visible = true;
    self->is_player = false;
    self->direction = vector_mp_init(1.0f, 0.0f, 0.0f, true);
    self->plane = vector_mp_init(0.0f, 0.0f, 0.0f, false);
    self->state = ENTITY_STATE_IDLE;
    self->move_timer = 0.0f;
    self->elapsed_move_timer = 0.0f;
    self->speed = 0.0f;
    self->attack_timer = 0.0f;
    self->elapsed_attack_timer = 0.0f;
    self->strength = 0.0f;
    self->health = 0.0f;
    self->max_health = 100.0f;
    self->level = 0.0f;
    self->xp = 0.0f;
    self->health_regen = 0.0f;
    self->elapsed_health_regen = 0.0f;
    self->sprite_3d = sprite3d_mp_init();
    self->sprite_3d_type = n_args > 4 ? mp_obj_get_int(args[4]) : SPRITE_3D_NONE;
    self->sprite_rotation = 0.0f;
    self->sprite_scale = 1.0f;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t entity_mp_del(mp_obj_t self_in)
{
    entity_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }
    if (self->name != NULL)
    {
        m_free(self->name);
        self->name = NULL;
    }
    engine_mp_del_reference(self->position);
    engine_mp_del_reference(self->old_position);
    engine_mp_del_reference(self->size);
    if (self->direction != MP_OBJ_NULL)
    {
        m_del_obj(vector_mp_obj_t, MP_OBJ_TO_PTR(self->direction));
        self->direction = MP_OBJ_NULL;
    }
    if (self->plane != MP_OBJ_NULL)
    {
        m_del_obj(vector_mp_obj_t, MP_OBJ_TO_PTR(self->plane));
        self->plane = MP_OBJ_NULL;
    }
    engine_mp_del_reference(self->start_position);
    engine_mp_del_reference(self->end_position);
    if (self->sprite_3d != MP_OBJ_NULL)
    {
        m_del_obj(sprite3d_mp_obj_t, MP_OBJ_TO_PTR(self->sprite_3d));
        self->sprite_3d = MP_OBJ_NULL;
    }
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(entity_mp_del_obj, entity_mp_del);

void entity_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    entity_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // load attributes
        if (attribute == MP_QSTR_name)
        {
            destination[0] = mp_obj_new_str(self->name, strlen(self->name));
        }
        else if (attribute == MP_QSTR_type)
        {
            destination[0] = mp_obj_new_int(self->type);
        }
        else if (attribute == MP_QSTR_position)
        {
            destination[0] = self->position;
        }
        else if (attribute == MP_QSTR_old_position)
        {
            destination[0] = self->old_position;
        }
        else if (attribute == MP_QSTR_size)
        {
            destination[0] = self->size;
        }
        else if (attribute == MP_QSTR_is_8bit)
        {
            destination[0] = mp_obj_new_bool(self->is_8bit);
        }
        else if (attribute == MP_QSTR_is_active)
        {
            destination[0] = mp_obj_new_bool(self->is_active);
        }
        else if (attribute == MP_QSTR_is_visible)
        {
            destination[0] = mp_obj_new_bool(self->is_visible);
        }
        else if (attribute == MP_QSTR_is_player)
        {
            destination[0] = mp_obj_new_bool(self->is_player);
        }
        else if (attribute == MP_QSTR_direction)
        {
            destination[0] = self->direction;
        }
        else if (attribute == MP_QSTR_plane)
        {
            destination[0] = self->plane;
        }
        else if (attribute == MP_QSTR_state)
        {
            destination[0] = mp_obj_new_int(self->state);
        }
        else if (attribute == MP_QSTR_start_position)
        {
            destination[0] = self->start_position;
        }
        else if (attribute == MP_QSTR_end_position)
        {
            destination[0] = self->end_position;
        }
        else if (attribute == MP_QSTR_move_timer)
        {
            destination[0] = mp_obj_new_float(self->move_timer);
        }
        else if (attribute == MP_QSTR_elapsed_move_timer)
        {
            destination[0] = mp_obj_new_float(self->elapsed_move_timer);
        }
        else if (attribute == MP_QSTR_radius)
        {
            destination[0] = mp_obj_new_float(self->radius);
        }
        else if (attribute == MP_QSTR_speed)
        {
            destination[0] = mp_obj_new_float(self->speed);
        }
        else if (attribute == MP_QSTR_attack_timer)
        {
            destination[0] = mp_obj_new_float(self->attack_timer);
        }
        else if (attribute == MP_QSTR_elapsed_attack_timer)
        {
            destination[0] = mp_obj_new_float(self->elapsed_attack_timer);
        }
        else if (attribute == MP_QSTR_strength)
        {
            destination[0] = mp_obj_new_float(self->strength);
        }
        else if (attribute == MP_QSTR_health)
        {
            destination[0] = mp_obj_new_float(self->health);
        }
        else if (attribute == MP_QSTR_max_health)
        {
            destination[0] = mp_obj_new_float(self->max_health);
        }
        else if (attribute == MP_QSTR_level)
        {
            destination[0] = mp_obj_new_float(self->level);
        }
        else if (attribute == MP_QSTR_xp)
        {
            destination[0] = mp_obj_new_float(self->xp);
        }
        else if (attribute == MP_QSTR_health_regen)
        {
            destination[0] = mp_obj_new_float(self->health_regen);
        }
        else if (attribute == MP_QSTR_elapsed_health_regen)
        {
            destination[0] = mp_obj_new_float(self->elapsed_health_regen);
        }
        else if (attribute == MP_QSTR_sprite_3d)
        {
            destination[0] = self->sprite_3d;
        }
        else if (attribute == MP_QSTR_sprite_3d_type)
        {
            destination[0] = mp_obj_new_int(self->sprite_3d_type);
        }
        else if (attribute == MP_QSTR_sprite_rotation)
        {
            destination[0] = mp_obj_new_float(self->sprite_rotation);
        }
        else if (attribute == MP_QSTR_sprite_scale)
        {
            destination[0] = mp_obj_new_float(self->sprite_scale);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&entity_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // store attributes
        if (attribute == MP_QSTR_name)
        {
            size_t name_len;
            const char *name_str = mp_obj_str_get_data(destination[1], &name_len);
            if (self->name != NULL)
            {
                m_free(self->name);
            }
            self->name = m_malloc(name_len + 1);
            if (self->name != NULL)
            {
                memcpy(self->name, name_str, name_len);
                self->name[name_len] = '\0';
            }
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_type)
        {
            self->type = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_position)
        {
            self->old_position = self->position;
            self->position = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_old_position)
        {
            self->old_position = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_size)
        {
            self->size = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_8bit)
        {
            self->is_8bit = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_active)
        {
            self->is_active = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_visible)
        {
            self->is_visible = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_player)
        {
            self->is_player = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_direction)
        {
            self->direction = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_plane)
        {
            self->plane = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_state)
        {
            self->state = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_start_position)
        {
            self->start_position = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_end_position)
        {
            self->end_position = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_move_timer)
        {
            self->move_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_elapsed_move_timer)
        {
            self->elapsed_move_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_radius)
        {
            self->radius = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_speed)
        {
            self->speed = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_attack_timer)
        {
            self->attack_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_elapsed_attack_timer)
        {
            self->elapsed_attack_timer = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_strength)
        {
            self->strength = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_health)
        {
            self->health = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_max_health)
        {
            self->max_health = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_level)
        {
            self->level = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_xp)
        {
            self->xp = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_health_regen)
        {
            self->health_regen = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_elapsed_health_regen)
        {
            self->elapsed_health_regen = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_sprite_3d)
        {
            if (self->sprite_3d != MP_OBJ_NULL)
            {
                m_del_obj(sprite3d_mp_obj_t, MP_OBJ_TO_PTR(self->sprite_3d));
                self->sprite_3d = MP_OBJ_NULL;
            }
            self->sprite_3d = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_sprite_3d_type)
        {
            self->sprite_3d_type = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_sprite_rotation)
        {
            self->sprite_rotation = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_sprite_scale)
        {
            self->sprite_scale = mp_obj_get_float(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

mp_obj_t entity_mp_has_3d_sprite(mp_obj_t self_in)
{
    entity_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(self->sprite_3d_type != SPRITE_3D_NONE && self->sprite_3d != MP_OBJ_NULL);
}
static MP_DEFINE_CONST_FUN_OBJ_1(entity_mp_has_3d_sprite_obj, entity_mp_has_3d_sprite);

mp_obj_t entity_mp_project_3d_to_2d(size_t n_args, const mp_obj_t *args)
{
    // self, vertex (Vector), player_pos (Vector), player_dir (Vector), view_height (float), screen_size (Vector)
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("project_3d_to_2d requires 6 arguments: self, vertex, player_pos, player_dir, view_height, screen_size"));
    }

    vector_mp_obj_t *vertex = MP_OBJ_TO_PTR(args[1]);
    vector_mp_obj_t *player_pos = MP_OBJ_TO_PTR(args[2]);
    vector_mp_obj_t *player_dir = MP_OBJ_TO_PTR(args[3]);
    float view_height = mp_obj_get_float(args[4]);
    vector_mp_obj_t *screen_size = MP_OBJ_TO_PTR(args[5]);

    // Transform world coordinates to camera coordinates
    float world_dx = vertex->x - player_pos->x;
    float world_dz = vertex->z - player_pos->y; // player_pos->y is actually the Z coordinate in world space
    float world_dy = vertex->y - view_height;   // Height difference from camera

    // Transform to camera space with camera coordinate system
    float camera_x = world_dx * player_dir->y + world_dz * -player_dir->x;
    float camera_z = world_dx * player_dir->x + world_dz * player_dir->y;

    // Prevent division by zero and reject points behind camera
    if (camera_z <= 0.01f)
    {
        return vector_mp_init(-1.0f, -1.0f, 0.0f, false); // Invalid point (behind camera)
    }
    else
    {
        // Project to screen coordinates - scale based on screen size
        float screen_x = (camera_x / camera_z) * screen_size->y + (screen_size->x / 2.0f);
        float screen_y = (-world_dy / camera_z) * screen_size->y + (screen_size->y / 2.0f);

        return vector_mp_init(screen_x, screen_y, 0.0f, false);
    }
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(entity_mp_project_3d_to_2d_obj, 6, 6, entity_mp_project_3d_to_2d);

static const mp_rom_map_elem_t entity_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_has_sprite3d), MP_ROM_PTR(&entity_mp_has_3d_sprite_obj)},
    {MP_ROM_QSTR(MP_QSTR_project_3d_to_2d), MP_ROM_PTR(&entity_mp_project_3d_to_2d_obj)},
};
static MP_DEFINE_CONST_DICT(entity_mp_locals_dict, entity_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    entity_mp_type,
    MP_QSTR_Entity,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, entity_mp_print,
    make_new, entity_mp_make_new,
    attr, entity_mp_attr,
    locals_dict, &entity_mp_locals_dict);