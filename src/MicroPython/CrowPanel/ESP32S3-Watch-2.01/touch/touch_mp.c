#include "touch.h"

#include "board_config.h"
#include "py/obj.h"
#include "py/runtime.h"

typedef struct
{
    mp_obj_base_t base;
    uint16_t x;
    uint16_t y;
    uint16_t strength;
    uint8_t touch_count;
    bool pressed;
} touch_mp_obj_t;

const mp_obj_type_t touch_mp_type;

static mp_obj_t touch_mp_read(mp_obj_t self_in)
{
    touch_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!touch_read())
    {
        return mp_obj_new_bool(false);
    }

    const TouchPoint point = touch_get_point();
    self->x = point.x;
    self->y = point.y;
    self->strength = point.strength;
    self->touch_count = point.touch_count;
    self->pressed = point.pressed;
    return mp_obj_new_bool(self->pressed);
}
static MP_DEFINE_CONST_FUN_OBJ_1(touch_mp_read_obj, touch_mp_read);

static mp_obj_t touch_mp_del(mp_obj_t self_in)
{
    (void)self_in;
    touch_deinit();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(touch_mp_del_obj, touch_mp_del);

static mp_obj_t touch_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw,
                                  const mp_obj_t *args)
{
    (void)args;
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    if (!touch_init())
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to initialize AXS5106L touch"));
    }

    touch_mp_obj_t *self = mp_obj_malloc_with_finaliser(touch_mp_obj_t, type);
    self->base.type = type;
    self->x = 0;
    self->y = 0;
    self->strength = 0;
    self->touch_count = 0;
    self->pressed = false;
    return MP_OBJ_FROM_PTR(self);
}

static void touch_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    touch_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] != MP_OBJ_NULL)
    {
        return;
    }

    switch (attribute)
    {
    case MP_QSTR_x:
        destination[0] = mp_obj_new_int(self->x);
        break;
    case MP_QSTR_y:
        destination[0] = mp_obj_new_int(self->y);
        break;
    case MP_QSTR_strength:
        destination[0] = mp_obj_new_int(self->strength);
        break;
    case MP_QSTR_touch_count:
        destination[0] = mp_obj_new_int(self->touch_count);
        break;
    case MP_QSTR_pressed:
        destination[0] = mp_obj_new_bool(self->pressed);
        break;
    case MP_QSTR_read:
        destination[0] = MP_OBJ_FROM_PTR(&touch_mp_read_obj);
        destination[1] = self_in;
        break;
    case MP_QSTR___del__:
        destination[0] = MP_OBJ_FROM_PTR(&touch_mp_del_obj);
        break;
    default:
        destination[1] = MP_OBJ_SENTINEL;
        break;
    }
}

static const mp_rom_map_elem_t touch_mp_locals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&touch_mp_read_obj)},
};
static MP_DEFINE_CONST_DICT(touch_mp_locals, touch_mp_locals_table);

MP_DEFINE_CONST_OBJ_TYPE(
    touch_mp_type,
    MP_QSTR_Touch,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    make_new, touch_mp_make_new,
    attr, touch_mp_attr,
    locals_dict, &touch_mp_locals);

static const mp_rom_map_elem_t touch_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_touch)},
    {MP_ROM_QSTR(MP_QSTR_GPIO_INT), MP_ROM_INT(WATCH_TOUCH_INT_GPIO)},
    {MP_ROM_QSTR(MP_QSTR_Touch), MP_ROM_PTR(&touch_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&touch_mp_read_obj)},
};
static MP_DEFINE_CONST_DICT(touch_module_globals, touch_module_globals_table);

const mp_obj_module_t touch_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&touch_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_touch, touch_user_cmodule);
