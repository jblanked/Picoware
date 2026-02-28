#include "game_mp.h"
#include "camera_mp.h"
#include "engine_mp.h"
#include "level_mp.h"

const mp_obj_type_t game_mp_type;

void game_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    game_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Game(");
    mp_print_str(print, "name=");
    mp_obj_print_helper(print, mp_obj_new_str(self->name, strlen(self->name)), PRINT_REPR);
    mp_print_str(print, ", levels=");
    mp_obj_print_helper(print, self->levels, PRINT_REPR);
    mp_print_str(print, ", position=");
    mp_obj_print_helper(print, self->position, PRINT_REPR);
    mp_print_str(print, ", size=");
    mp_obj_print_helper(print, self->size, PRINT_REPR);
    mp_print_str(print, ", is_active=");
    mp_obj_print_helper(print, self->is_active ? mp_const_true : mp_const_false, PRINT_REPR);
    mp_print_str(print, ", foreground_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->foreground_color), PRINT_REPR);
    mp_print_str(print, ", background_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->background_color), PRINT_REPR);
    mp_print_str(print, ", camera_perspective=");
    if (self->camera_perspective == 0)
    {
        mp_print_str(print, "first_person");
    }
    else if (self->camera_perspective == 1)
    {
        mp_print_str(print, "third_person");
    }
    else
    {
        mp_obj_print_helper(print, mp_obj_new_int(self->camera_perspective), PRINT_REPR);
    }
    mp_print_str(print, ", input=");
    if (self->input == -1)
    {
        mp_print_str(print, "None");
    }
    else
    {
        mp_obj_print_helper(print, mp_obj_new_int(self->input), PRINT_REPR);
    }
    mp_print_str(print, ")");
}

mp_obj_t game_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // required: name, size
    // optional: foreground_color, background_color, perspective
    mp_arg_check_num(n_args, n_kw, 2, 5, false);
    game_mp_obj_t *self = mp_obj_malloc_with_finaliser(game_mp_obj_t, &game_mp_type);
    self->base.type = &game_mp_type;
    size_t name_len;
    const char *name_str = mp_obj_str_get_data(args[0], &name_len);
    self->name = m_malloc(name_len + 1);
    if (self->name != NULL)
    {
        memcpy(self->name, name_str, name_len);
        self->name[name_len] = '\0';
    }
    self->size = args[1];
    self->levels = mp_obj_new_list(0, MP_OBJ_NULL);
    self->position = vector_mp_init(0, 0, 0, true);
    self->is_active = false;
    self->foreground_color = (n_args >= 3) ? mp_obj_get_int(args[2]) : 0xFFFF;
    self->background_color = (n_args >= 4) ? mp_obj_get_int(args[3]) : 0x0000;
    self->camera_perspective = (n_args >= 5) ? mp_obj_get_int(args[4]) : CAMERA_FIRST_PERSON;
    self->input = -1;
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t game_mp_del(mp_obj_t self_in)
{
    game_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }
    if (self->name != NULL)
    {
        m_free(self->name);
        self->name = NULL;
    }
    if (self->levels != MP_OBJ_NULL)
    {
        m_del_obj(mp_obj_list_t, MP_OBJ_TO_PTR(self->levels));
        self->levels = MP_OBJ_NULL;
    }
    if (self->position != MP_OBJ_NULL)
    {
        m_del_obj(vector_mp_obj_t, MP_OBJ_TO_PTR(self->position));
        self->position = MP_OBJ_NULL;
    }
    engine_mp_del_reference(self->size);
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(game_mp_del_obj, game_mp_del);

void game_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    game_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // load attributes
        if (attribute == MP_QSTR_name)
        {
            destination[0] = mp_obj_new_str(self->name, strlen(self->name));
        }
        else if (attribute == MP_QSTR_levels)
        {
            destination[0] = self->levels;
        }
        else if (attribute == MP_QSTR_position)
        {
            destination[0] = self->position;
        }
        else if (attribute == MP_QSTR_size)
        {
            destination[0] = self->size;
        }
        else if (attribute == MP_QSTR_is_active)
        {
            destination[0] = self->is_active ? mp_const_true : mp_const_false;
        }
        else if (attribute == MP_QSTR_foreground_color)
        {
            destination[0] = mp_obj_new_int(self->foreground_color);
        }
        else if (attribute == MP_QSTR_background_color)
        {
            destination[0] = mp_obj_new_int(self->background_color);
        }
        else if (attribute == MP_QSTR_camera_perspective)
        {
            destination[0] = mp_obj_new_int(self->camera_perspective);
        }
        else if (attribute == MP_QSTR_input)
        {
            destination[0] = mp_obj_new_int(self->input);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&game_mp_del_obj);
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
                self->name = NULL;
            }
            self->name = m_malloc(name_len + 1);
            if (self->name != NULL)
            {
                memcpy(self->name, name_str, name_len);
                self->name[name_len] = '\0';
            }
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_levels)
        {
            if (self->levels != MP_OBJ_NULL)
            {
                m_del_obj(mp_obj_list_t, MP_OBJ_TO_PTR(self->levels));
                self->levels = MP_OBJ_NULL;
            }
            self->levels = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_position)
        {
            if (self->position != MP_OBJ_NULL)
            {
                m_del_obj(vector_mp_obj_t, MP_OBJ_TO_PTR(self->position));
                self->position = MP_OBJ_NULL;
            }
            self->position = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_size)
        {
            engine_mp_del_reference(self->size);
            self->size = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_is_active)
        {
            self->is_active = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_foreground_color)
        {
            self->foreground_color = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_background_color)
        {
            self->background_color = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_camera_perspective)
        {
            self->camera_perspective = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_input)
        {
            self->input = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

MP_DEFINE_CONST_OBJ_TYPE(
    game_mp_type,
    MP_QSTR_Game,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, game_mp_print,
    make_new, game_mp_make_new,
    attr, game_mp_attr);