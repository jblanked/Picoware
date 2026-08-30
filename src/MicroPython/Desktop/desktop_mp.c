#include "py/runtime.h"
#include "picoware_boards.h"

static mp_obj_t desktop_native_modules(void)
{
    mp_obj_t modules[] = {
        MP_OBJ_NEW_QSTR(MP_QSTR_auto_complete),
        MP_OBJ_NEW_QSTR(MP_QSTR_c),
        MP_OBJ_NEW_QSTR(MP_QSTR_font),
        MP_OBJ_NEW_QSTR(MP_QSTR_mjs),
        MP_OBJ_NEW_QSTR(MP_QSTR_mmbasic),
        MP_OBJ_NEW_QSTR(MP_QSTR_response),
        MP_OBJ_NEW_QSTR(MP_QSTR_video),
        MP_OBJ_NEW_QSTR(MP_QSTR_vector),
    };
    return mp_obj_new_tuple(8, modules);
}
static MP_DEFINE_CONST_FUN_OBJ_0(desktop_native_modules_obj,
                                 desktop_native_modules);

static const mp_rom_map_elem_t desktop_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_desktop)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_ID), MP_ROM_INT(BOARD_DESKTOP)},
    {MP_ROM_QSTR(MP_QSTR_native_modules),
     MP_ROM_PTR(&desktop_native_modules_obj)},
};
static MP_DEFINE_CONST_DICT(desktop_module_globals,
                            desktop_module_globals_table);

const mp_obj_module_t desktop_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&desktop_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_picoware_desktop, desktop_user_cmodule);
