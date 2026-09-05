#include "battery.h"
#include <string.h>
#include "py/runtime.h"

static mp_obj_t battery_mp_instance;

static mjs_val_t battery_battery(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, battery_mp_instance, MP_QSTR_battery);
}

static mjs_val_t battery_has_voltage(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, battery_mp_instance, MP_QSTR_has_voltage);
}

static mjs_val_t battery_voltage(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, battery_mp_instance, MP_QSTR_voltage);
}

void battery_create(struct mjs *mjs, mjs_val_t *battery_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    // from picoware.system.battery import Battery
    mp_obj_t import_name = mp_obj_new_str("picoware.system.battery", strlen("picoware.system.battery"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_Battery));
    mp_obj_t battery_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t battery_mp_class = mp_load_attr(battery_mod, MP_QSTR_Battery);
    battery_mp_instance = mp_call_function_0(battery_mp_class);

    *battery_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *battery_obj, "battery", ~0, battery_battery);
    mjs_set_getter(mjs, *battery_obj, "hasVoltage", ~0, battery_has_voltage);
    mjs_set_getter(mjs, *battery_obj, "voltage", ~0, battery_voltage);

    nlr_pop();
}

void battery_destroy()
{
    battery_mp_instance = MP_OBJ_NULL;
}