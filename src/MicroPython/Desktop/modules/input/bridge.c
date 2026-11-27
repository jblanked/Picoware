#include "desktop_input.h"
#include "../../../input/input.h"
#include "py/runtime.h"

static mp_obj_t call_input(const char *name)
{
    mp_obj_t module = mp_import_name(qstr_from_str("sim_input"), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    return mp_call_function_0(mp_load_attr(module, qstr_from_str(name)));
}

bool desktop_input_init(void)
{
    return mp_obj_is_true(call_input("init"));
}

void desktop_input_deinit(void)
{
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
