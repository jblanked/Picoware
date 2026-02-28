#include "level_mp.h"
#include "engine_mp.h"

const mp_obj_type_t level_mp_type;

void level_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    level_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Level(");
    mp_print_str(print, "name=");
    mp_obj_print_helper(print, mp_obj_new_str(self->name, strlen(self->name)), PRINT_REPR);
    mp_print_str(print, ", size=");
    mp_obj_print_helper(print, self->size, PRINT_REPR);
    mp_print_str(print, ", entities=");
    mp_obj_print_helper(print, self->entities, PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t level_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    level_mp_obj_t *self = mp_obj_malloc_with_finaliser(level_mp_obj_t, &level_mp_type);
    self->base.type = &level_mp_type;
    size_t name_len;
    const char *name_str = mp_obj_str_get_data(args[0], &name_len);
    self->name = m_malloc(name_len + 1);
    if (self->name != NULL)
    {
        memcpy(self->name, name_str, name_len);
        self->name[name_len] = '\0';
    }
    self->size = args[1];
    self->entities = mp_obj_new_list(0, MP_OBJ_NULL);
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t level_mp_del(mp_obj_t self_in)
{
    level_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }
    if (self->name != NULL)
    {
        m_free(self->name);
        self->name = NULL;
    }
    engine_mp_del_reference(self->size);
    if (self->entities != MP_OBJ_NULL)
    {
        m_del_obj(mp_obj_list_t, MP_OBJ_TO_PTR(self->entities));
        self->entities = MP_OBJ_NULL;
    }
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(level_mp_del_obj, level_mp_del);

void level_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    level_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // load attributes
        if (attribute == MP_QSTR_name)
        {
            destination[0] = mp_obj_new_str(self->name, strlen(self->name));
        }
        else if (attribute == MP_QSTR_size)
        {
            destination[0] = self->size;
        }
        else if (attribute == MP_QSTR_entities)
        {
            destination[0] = self->entities;
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&level_mp_del_obj);
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
        else if (attribute == MP_QSTR_size)
        {
            engine_mp_del_reference(self->size);
            self->size = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_entities)
        {
            if (self->entities != MP_OBJ_NULL)
            {
                m_del_obj(mp_obj_list_t, MP_OBJ_TO_PTR(self->entities));
                self->entities = MP_OBJ_NULL;
            }
            self->entities = destination[1];
            destination[0] = MP_OBJ_NULL;
        }
    }
}

MP_DEFINE_CONST_OBJ_TYPE(
    level_mp_type,
    MP_QSTR_Level,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, level_mp_print,
    make_new, level_mp_make_new,
    attr, level_mp_attr);