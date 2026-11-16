#include "view_mp.h"

void view_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    view_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "View(active=%s)", self->active ? "True" : "False");
}

mp_obj_t view_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // Arguments: name (str), start (function), run (function), stop (function)
    mp_arg_check_num(n_args, n_kw, 4, 4, true);
    view_mp_obj_t *self = mp_obj_malloc_with_finaliser(view_mp_obj_t, &view_mp_type);
    self->base.type = &view_mp_type;
    const char *name = mp_obj_str_get_str(args[0]);
    self->name = m_malloc(strlen(name) + 1);
    if (!self->name)
    {
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("not enough memory for name"));
    }
    memcpy(self->name, name, strlen(name) + 1);
    self->start = n_args > 1 ? args[1] : mp_const_none;
    self->run = n_args > 2 ? args[2] : mp_const_none;
    self->stop = n_args > 3 ? args[3] : mp_const_none;
    self->active = false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t view_mp_del(mp_obj_t self_in)
{
    view_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self)
        return mp_const_none;
    if (self->name)
        m_free(self->name);
    self->name = NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(view_mp_del_obj, view_mp_del);

void view_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    view_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        switch (attribute)
        {
        case MP_QSTR_name:
            destination[0] = mp_obj_new_str(self->name, strlen(self->name));
            break;
        case MP_QSTR_active:
            destination[0] = mp_obj_new_bool(self->active);
            break;
        case MP_QSTR_start:
            destination[0] = self->start;
            break;
        case MP_QSTR_run:
            destination[0] = self->run;
            break;
        case MP_QSTR_stop:
            destination[0] = self->stop;
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&view_mp_del_obj);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            break;
        };
    }
    else
    {
        switch (attribute)
        {
        case MP_QSTR_active:
            self->active = mp_obj_is_true(destination[0]);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            break;
        };
    }
}

mp_obj_t view_mp_set_active(mp_obj_t self_in, mp_obj_t active)
{
    view_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->active = mp_obj_is_true(active);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(view_mp_set_active_obj, view_mp_set_active);

static const mp_rom_map_elem_t view_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_active), MP_ROM_PTR(&view_mp_set_active_obj)},
};
static MP_DEFINE_CONST_DICT(view_mp_locals_dict, view_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    view_mp_type,
    MP_QSTR_View,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, view_mp_print,
    make_new, view_mp_make_new,
    attr, view_mp_attr,
    locals_dict, &view_mp_locals_dict);

static const mp_rom_map_elem_t view_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_view)},
    {MP_ROM_QSTR(MP_QSTR_View), MP_ROM_PTR(&view_mp_type)},
};
static MP_DEFINE_CONST_DICT(view_mp_globals, view_mp_globals_table);

const mp_obj_module_t view_mp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&view_mp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_view, view_mp_module);