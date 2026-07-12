#include <string.h>
#include "mjs_mp.h"
#include "mjs/mjs.h"
#include "lib/lib.h"

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC) || defined(CARDPUTER) || defined(WAVESHARE_2_06)
#include "../sd/storage.h"
#endif

const mp_obj_type_t mjs_mp_type;

void mjs_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "MJS(is_initialized=");
    mp_print_str(print, self->is_initialized ? "true" : "false");
    mp_print_str(print, ")");
}

mp_obj_t mjs_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mjs_mp_obj_t *self = mp_obj_malloc_with_finaliser(mjs_mp_obj_t, &mjs_mp_type);
    self->base.type = &mjs_mp_type;
    self->is_initialized = false;
    self->mjs = NULL;
    self->mjs = mjs_create();
    if (!self->mjs)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("failed to create MJS engine"));
    }
    lib_register_globals(self->mjs);
    self->is_initialized = true;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t mjs_mp_del(mp_obj_t self_in)
{
    lib_unload_modules();
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self)
        return mp_const_none;
    if (self->mjs)
    {
        mjs_destroy(self->mjs);
        self->mjs = NULL;
    }
    self->is_initialized = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mjs_mp_del_obj, mjs_mp_del);

mp_obj_t mjs_mp_exec(mp_obj_t self_in, mp_obj_t path)
{
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);

    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(path, &bufinfo, MP_BUFFER_READ))
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected a string"));
    }

    mjs_val_t result = mjs_mk_undefined();
#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC) || defined(CARDPUTER) || defined(WAVESHARE_2_06)
    size_t fsize = storage_file_size(bufinfo.buf);
    if (fsize == 0)
    {
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("file not found"));
    }

    char *buf = m_new(char, fsize + 1);
    size_t bytes_read = storage_file_read(bufinfo.buf, buf, fsize);
    if (bytes_read == 0)
    {
        m_free(buf);
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("failed to read file"));
    }
    buf[bytes_read] = '\0';

    mjs_err_t err = mjs_exec(self->mjs, buf, &result);
    m_free(buf);

    if (err != MJS_OK)
    {
        const char *err_str = mjs_strerror(self->mjs, err);
        mp_raise_msg_varg(&mp_type_RuntimeError, MP_ERROR_TEXT("MJS error: %s"), err_str);
    }
#else
    (void)result;
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("storage not available"));
#endif
    return mjs_val_to_mp_obj(self->mjs, result);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mjs_mp_exec_obj, mjs_mp_exec);

mp_obj_t mjs_mp_run(mp_obj_t self_in, mp_obj_t js_code)
{
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);

    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(js_code, &bufinfo, MP_BUFFER_READ))
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected a string"));
    }

    mjs_val_t result = mjs_mk_undefined();
    mjs_err_t err = mjs_exec(self->mjs, bufinfo.buf, &result);

    if (err != MJS_OK)
    {
        const char *err_str = mjs_strerror(self->mjs, err);
        mp_raise_msg_varg(&mp_type_RuntimeError, MP_ERROR_TEXT("MJS error: %s"), err_str);
    }

    return mjs_val_to_mp_obj(self->mjs, result);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mjs_mp_run_obj, mjs_mp_run);

void mjs_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] != MP_OBJ_NULL)
    {
        // Load attributes
        switch (attribute)
        {
        case MP_QSTR_is_initialized:
            destination[0] = mp_obj_new_bool(self->is_initialized);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&mjs_mp_del_obj);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            return;
        };
    }
}

static const mp_rom_map_elem_t mjs_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&mjs_mp_run_obj)},
    {MP_ROM_QSTR(MP_QSTR_exec), MP_ROM_PTR(&mjs_mp_exec_obj)},
};
static MP_DEFINE_CONST_DICT(mjs_mp_locals_dict, mjs_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    mjs_mp_type,
    MP_QSTR_MJS,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, mjs_mp_print,
    make_new, mjs_mp_make_new,
    attr, mjs_mp_attr,
    locals_dict, &mjs_mp_locals_dict);

static const mp_rom_map_elem_t mjs_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mjs)},
    {MP_ROM_QSTR(MP_QSTR_MJS), MP_ROM_PTR(&mjs_mp_type)},
};
static MP_DEFINE_CONST_DICT(mjs_module_globals, mjs_module_globals_table);

// Define module
const mp_obj_module_t mjs_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mjs_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_mjs, mjs_user_cmodule);
