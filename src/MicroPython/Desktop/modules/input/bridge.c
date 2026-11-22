#include "desktop_input.h"
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
    return mp_obj_get_int(call_input("read"));
}

void desktop_input_game_mode(bool enable)
{
    mp_obj_t module = mp_import_name(qstr_from_str("sim_input"), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_call_function_1(mp_load_attr(module, qstr_from_str("game_mode")), mp_obj_new_bool(enable));
}
