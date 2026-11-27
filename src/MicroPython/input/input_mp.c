#include "input_mp.h"
#include "input.h"
#include "input_config.h"
#include INPUT_MP_INCLUDE

void input_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)self_in;
    (void)kind;
    mp_printf(print, "Input()");
}

mp_obj_t input_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 1, true);
    input_mp_obj_t *self = mp_obj_malloc_with_finaliser(input_mp_obj_t, &input_mp_type);
    self->base.type = &input_mp_type;
    self->was_capitalized = false;
    input_set_touch(0, 0, 0, false);
    self->initialized = INPUT_MP_INIT();
    input_back_special = n_args > 0 ? mp_obj_get_int(args[0]) != BUTTON_BACK : false;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t input_mp_del(mp_obj_t self_in)
{
    input_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self && self->initialized)
    {
        INPUT_MP_DEINIT();
        input_set_touch(0, 0, 0, false);
        self->was_capitalized = false;
        self->initialized = false;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(input_mp_del_obj, input_mp_del);

void input_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    input_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self)
        return;
    if (destination[0] == MP_OBJ_NULL)
    {
        switch (attribute)
        {
        case MP_QSTR__was_capitalized:
            destination[0] = mp_obj_new_bool(self->was_capitalized);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&input_mp_del_obj);
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
        case MP_QSTR_was_capitalized:
            self->was_capitalized = mp_obj_is_true(destination[0]);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            break;
        };
    }
}

mp_obj_t input_mp_button_to_char(mp_obj_t self_in, mp_obj_t button)
{
    input_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self || !self->initialized)
        return mp_obj_new_str("", 0);
    const int button_code = mp_obj_get_int(button);
    const char char_to_add = input_button_to_char(button_code, self->was_capitalized);
    return mp_obj_new_str(&char_to_add, 1);
}
static MP_DEFINE_CONST_FUN_OBJ_2(input_mp_button_to_char_obj, input_mp_button_to_char);

mp_obj_t input_mp_deinit(mp_obj_t self_in)
{
    input_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self && self->initialized)
    {
        INPUT_MP_DEINIT();
        input_set_touch(0, 0, 0, false);
        self->was_capitalized = false;
        self->initialized = false;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(input_mp_deinit_obj, input_mp_deinit);

mp_obj_t input_mp_get_input(mp_obj_t self_in)
{
    input_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self || !self->initialized)
        return mp_obj_new_int(-1);
    return mp_obj_new_int(INPUT_MP_READ());
}
static MP_DEFINE_CONST_FUN_OBJ_1(input_mp_get_input_obj, input_mp_get_input);

mp_obj_t input_mp_get_last_button(mp_obj_t self_in)
{
    input_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self || !self->initialized)
        return mp_obj_new_int(-1);
    return mp_obj_new_int(input_char_to_button(INPUT_MP_READ()));
}
static MP_DEFINE_CONST_FUN_OBJ_1(input_mp_get_last_button_obj, input_mp_get_last_button);

mp_obj_t input_mp_key_to_button(mp_obj_t self_in, mp_obj_t key)
{
    input_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self || !self->initialized)
        return mp_obj_new_int(-1);
    const int key_char = mp_obj_get_int(key);
    self->was_capitalized = key_char >= 65 && key_char <= 90;
    return mp_obj_new_int(input_char_to_button(key_char));
}
static MP_DEFINE_CONST_FUN_OBJ_2(input_mp_key_to_button_obj, input_mp_key_to_button);

static mp_obj_t input_mp_get_touch_point(mp_obj_t self_in)
{
    (void)self_in;
    const InputTouchState *state = input_touch_state();
    mp_obj_t point[2] = {mp_obj_new_int(state->x), mp_obj_new_int(state->y)};
    return mp_obj_new_tuple(2, point);
}
static MP_DEFINE_CONST_FUN_OBJ_1(input_mp_get_touch_point_obj, input_mp_get_touch_point);

static mp_obj_t input_mp_get_touch_gesture(mp_obj_t self_in)
{
    (void)self_in;
    return mp_obj_new_int(input_touch_state()->gesture);
}
static MP_DEFINE_CONST_FUN_OBJ_1(input_mp_get_touch_gesture_obj, input_mp_get_touch_gesture);

static mp_obj_t input_mp_is_touch_down(mp_obj_t self_in)
{
    (void)self_in;
    return mp_obj_new_bool(input_touch_state()->pressed);
}
static MP_DEFINE_CONST_FUN_OBJ_1(input_mp_is_touch_down_obj, input_mp_is_touch_down);

static const mp_rom_map_elem_t input_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_touch_point), MP_ROM_PTR(&input_mp_get_touch_point_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_touch_gesture), MP_ROM_PTR(&input_mp_get_touch_gesture_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_touch_down), MP_ROM_PTR(&input_mp_is_touch_down_obj)},
    {MP_ROM_QSTR(MP_QSTR_button_to_char), MP_ROM_PTR(&input_mp_button_to_char_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_input), MP_ROM_PTR(&input_mp_get_input_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_last_button), MP_ROM_PTR(&input_mp_get_last_button_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&input_mp_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_key_to_button), MP_ROM_PTR(&input_mp_key_to_button_obj)},
};
static MP_DEFINE_CONST_DICT(input_mp_locals_dict, input_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    input_mp_type,
    MP_QSTR_Input,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, input_mp_print,
    make_new, input_mp_make_new,
    attr, input_mp_attr,
    locals_dict, &input_mp_locals_dict);

static const mp_rom_map_elem_t input_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_input_mp)},
    {MP_ROM_QSTR(MP_QSTR_Input), MP_ROM_PTR(&input_mp_type)},
};
static MP_DEFINE_CONST_DICT(input_mp_globals, input_mp_globals_table);

const mp_obj_module_t input_mp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&input_mp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_input_mp, input_mp_module);