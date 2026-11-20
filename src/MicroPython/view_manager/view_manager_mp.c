#include "view_manager_mp.h"

void view_manager_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "ViewManager(active=%s, stack_depth=%u, view_count=%u)",
              self->_active ? "true" : "false",
              self->_stack_depth,
              self->_view_count);
}

mp_obj_t view_manager_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // no arguments
    mp_arg_check_num(n_args, n_kw, 0, 0, true);
    view_manager_mp_obj_t *self = mp_obj_malloc_with_finaliser(view_manager_mp_obj_t, &view_manager_mp_type);
    self->base.type = &view_manager_mp_type;
    self->_active = true;
    self->_current_view = mp_const_none;
    self->_stack_depth = 0;
    self->_view_count = 0;
    self->views = mp_obj_new_list(10, NULL);
    self->view_stack = mp_obj_new_list(10, NULL);
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t view_manager_mp_del(mp_obj_t self_in)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
    {
        self->_active = false;
        self->_current_view = mp_const_none;
        self->_stack_depth = 0;
        self->_view_count = 0;
        self->views = mp_obj_new_list(0, NULL);
        self->view_stack = mp_obj_new_list(0, NULL);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(view_manager_mp_del_obj, view_manager_mp_del);

void view_manager_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self)
        return;
    if (destination[0] == MP_OBJ_NULL)
    {
        switch (attribute)
        {
        case MP_QSTR__active:
            destination[0] = mp_obj_new_bool(self->_active);
            break;
        case MP_QSTR__current_view:
            destination[0] = self->_current_view;
            break;
        case MP_QSTR__stack_depth:
            destination[0] = mp_obj_new_int(self->_stack_depth);
            break;
        case MP_QSTR__view_count:
            destination[0] = mp_obj_new_int(self->_view_count);
            break;
        case MP_QSTR_views:
            destination[0] = self->views;
            break;
        case MP_QSTR_view_stack:
            destination[0] = self->view_stack;
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&view_manager_mp_del_obj);
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
        case MP_QSTR__active:
            view_manager_mp_set_active(self_in, destination[0]);
            break;
        case MP_QSTR__current_view:
            view_manager_mp_set_current_view(self_in, destination[0]);
            break;
        case MP_QSTR__stack_depth:
            view_manager_mp_set_stack_depth(self_in, destination[0]);
            break;
        case MP_QSTR__view_count:
            view_manager_mp_set_view_count(self_in, destination[0]);
            break;
        case MP_QSTR_views:
            view_manager_mp_set_views(self_in, destination[0]);
            break;
        case MP_QSTR_view_stack:
            view_manager_mp_set_view_stack(self_in, destination[0]);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            break;
        };
    }
}

mp_obj_t view_manager_mp_set_active(mp_obj_t self_in, mp_obj_t active)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->_active = mp_obj_is_true(active);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(view_manager_mp_set_active_obj, view_manager_mp_set_active);

mp_obj_t view_manager_mp_set_current_view(mp_obj_t self_in, mp_obj_t view)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->_current_view = view;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(view_manager_mp_set_current_view_obj, view_manager_mp_set_current_view);

mp_obj_t view_manager_mp_set_stack_depth(mp_obj_t self_in, mp_obj_t depth)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->_stack_depth = mp_obj_get_int(depth);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(view_manager_mp_set_stack_depth_obj, view_manager_mp_set_stack_depth);

mp_obj_t view_manager_mp_set_view_count(mp_obj_t self_in, mp_obj_t count)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->_view_count = mp_obj_get_int(count);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(view_manager_mp_set_view_count_obj, view_manager_mp_set_view_count);

mp_obj_t view_manager_mp_set_views(mp_obj_t self_in, mp_obj_t views)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->views = views;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(view_manager_mp_set_views_obj, view_manager_mp_set_views);

mp_obj_t view_manager_mp_set_view_stack(mp_obj_t self_in, mp_obj_t view_stack)
{
    view_manager_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->view_stack = view_stack;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(view_manager_mp_set_view_stack_obj, view_manager_mp_set_view_stack);

static const mp_rom_map_elem_t view_manager_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_set_active), MP_ROM_PTR(&view_manager_mp_set_active_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_current_view), MP_ROM_PTR(&view_manager_mp_set_current_view_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_stack_depth), MP_ROM_PTR(&view_manager_mp_set_stack_depth_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_view_count), MP_ROM_PTR(&view_manager_mp_set_view_count_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_views), MP_ROM_PTR(&view_manager_mp_set_views_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_view_stack), MP_ROM_PTR(&view_manager_mp_set_view_stack_obj)},
};
static MP_DEFINE_CONST_DICT(view_manager_mp_locals_dict, view_manager_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    view_manager_mp_type,
    MP_QSTR_ViewManager,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, view_manager_mp_print,
    make_new, view_manager_mp_make_new,
    attr, view_manager_mp_attr,
    locals_dict, &view_manager_mp_locals_dict);

static const mp_rom_map_elem_t view_manager_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_view_manager)},
    {MP_ROM_QSTR(MP_QSTR_ViewManager), MP_ROM_PTR(&view_manager_mp_type)},
};
static MP_DEFINE_CONST_DICT(view_manager_mp_globals, view_manager_mp_globals_table);

const mp_obj_module_t view_manager_mp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&view_manager_mp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_view_manager, view_manager_mp_module);