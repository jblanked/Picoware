#include "desktop_input.h"
#include "../../../input/input.h"
#include "py/runtime.h"

static uint16_t desktop_last_touch_x = 0;
static uint16_t desktop_last_touch_y = 0;

void input_set_touch(uint16_t x, uint16_t y, uint16_t strength, bool pressed)
{
    (void)strength;
    desktop_last_touch_x = pressed ? x : 0;
    desktop_last_touch_y = pressed ? y : 0;
}

void desktop_input_point(uint16_t *x, uint16_t *y)
{
    *x = desktop_last_touch_x;
    *y = desktop_last_touch_y;
    desktop_last_touch_x = 0;
    desktop_last_touch_y = 0;
}

static mp_obj_t call_input(const char *name)
{
    mp_obj_t module = mp_import_name(qstr_from_str("sim_input"), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    return mp_call_function_0(mp_load_attr(module, qstr_from_str(name)));
}

bool desktop_input_init(void)
{
    input_set_touch(0, 0, 0, false);
    return mp_obj_is_true(call_input("init"));
}

void desktop_input_deinit(void)
{
    input_set_touch(0, 0, 0, false);
    call_input("deinit");
}

int desktop_input_read(void)
{
    const int key = mp_obj_get_int(call_input("read"));
    mp_obj_t *sample;
    mp_obj_get_array_fixed_n(call_input("touch_state"), 4, &sample);
    input_set_touch(mp_obj_get_int(sample[0]), mp_obj_get_int(sample[1]),
                    mp_obj_get_int(sample[2]), mp_obj_is_true(sample[3]));
    return key;
}
