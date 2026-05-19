#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "stdio.h"
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "touch.h"

#ifndef STATIC
#define STATIC static
#endif

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

typedef struct
{
    mp_obj_base_t base;
    uint16_t x;          // X coordinate of the touch point
    uint16_t y;          // Y coordinate of the touch point
    uint16_t strength;   // Touch strength (pressure level)
    uint8_t touch_count; // Number of touch points detected (for multi-touch support)
    bool pressed;        // Whether the touch panel is currently being pressed
} touch_mp_obj_t;

const mp_obj_type_t touch_mp_type;

STATIC void touch_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    touch_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Touch(");
    mp_print_str(print, "x=");
    mp_obj_print_helper(print, mp_obj_new_int(self->x), PRINT_REPR);
    mp_print_str(print, ", y=");
    mp_obj_print_helper(print, mp_obj_new_int(self->y), PRINT_REPR);
    mp_print_str(print, ", strength=");
    mp_obj_print_helper(print, mp_obj_new_int(self->strength), PRINT_REPR);
    mp_print_str(print, ", touch_count=");
    mp_obj_print_helper(print, mp_obj_new_int(self->touch_count), PRINT_REPR);
    mp_print_str(print, ", pressed=");
    mp_obj_print_helper(print, mp_obj_new_bool(self->pressed), PRINT_REPR);
    mp_print_str(print, ")");
}

STATIC mp_obj_t touch_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    touch_mp_obj_t *self = mp_obj_malloc_with_finaliser(touch_mp_obj_t, &touch_mp_type);
    if (!touch_init())
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to initialize touch panel"));
    }
    self->base.type = &touch_mp_type;
    self->x = 0;
    self->y = 0;
    self->strength = 0;
    self->touch_count = 0;
    self->pressed = false;
    return MP_OBJ_FROM_PTR(self);
}

STATIC mp_obj_t touch_mp_del(mp_obj_t self_in)
{
    touch_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)self;
    touch_deinit();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(touch_mp_del_obj, touch_mp_del);

STATIC void touch_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    touch_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        if (attribute == MP_QSTR_x)
        {
            destination[0] = mp_obj_new_int(self->x);
        }
        else if (attribute == MP_QSTR_y)
        {
            destination[0] = mp_obj_new_int(self->y);
        }
        else if (attribute == MP_QSTR_strength)
        {
            destination[0] = mp_obj_new_int(self->strength);
        }
        else if (attribute == MP_QSTR_touch_count)
        {
            destination[0] = mp_obj_new_int(self->touch_count);
        }
        else if (attribute == MP_QSTR_pressed)
        {
            destination[0] = mp_obj_new_bool(self->pressed);
        }
        else if (attribute == MP_QSTR___del__)
        {
            destination[0] = MP_OBJ_FROM_PTR(&touch_mp_del_obj);
        }
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        if (attribute == MP_QSTR_x)
        {
            self->x = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_y)
        {
            self->y = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_strength)
        {
            self->strength = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_touch_count)
        {
            self->touch_count = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_pressed)
        {
            self->pressed = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
    }
}

STATIC mp_obj_t touch_mp_read(mp_obj_t self_in)
{
    touch_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!touch_read())
    {
        PRINT("Failed to read touch data\n");
        return mp_obj_new_bool(false);
    }
    TouchPoint point = touch_get_point();
    self->x = point.x;
    self->y = point.y;
    self->strength = point.strength;
    self->touch_count = point.touch_count;
    self->pressed = point.pressed;
    return mp_obj_new_bool(self->pressed);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(touch_mp_read_obj, touch_mp_read);

STATIC const mp_rom_map_elem_t touch_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&touch_mp_read_obj)},
};
STATIC MP_DEFINE_CONST_DICT(touch_mp_locals_dict, touch_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    touch_mp_type,
    MP_QSTR_Touch,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, touch_mp_print,
    make_new, touch_mp_make_new,
    attr, touch_mp_attr,
    locals_dict, &touch_mp_locals_dict);

STATIC const mp_rom_map_elem_t touch_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_touch)},
    {MP_ROM_QSTR(MP_QSTR_GPIO_INT), MP_ROM_INT(TOUCH_GPIO_INT)},
    {MP_ROM_QSTR(MP_QSTR_Touch), MP_ROM_PTR(&touch_mp_type)},
};
STATIC MP_DEFINE_CONST_DICT(touch_module_globals, touch_module_globals_table);

// Define module
const mp_obj_module_t touch_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&touch_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_touch, touch_user_cmodule);