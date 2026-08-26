#include "c_mp.h"
#include "py/gc.h"
#include <math.h>
#include "storage.h"
#include "pshell/cc/cc.h"

#define C_SOURCE_MAX 262144
#define C_PROGRAM_SPACE_SIZE (32 * 1024)

char *cc_program_space;

char *full_path(char *name)
{
    return name;
}

void get_screen_xy(int *x, int *y)
{
    *x = 320;
    *y = 320;
}

float __wrap_sinf(float value) { return sinf(value); }
float __wrap_cosf(float value) { return cosf(value); }
float __wrap_tanf(float value) { return tanf(value); }
float __wrap_asinf(float value) { return asinf(value); }
float __wrap_acosf(float value) { return acosf(value); }
float __wrap_atanf(float value) { return atanf(value); }
float __wrap_sinhf(float value) { return sinhf(value); }
float __wrap_coshf(float value) { return coshf(value); }
float __wrap_tanhf(float value) { return tanhf(value); }
float __wrap_asinhf(float value) { return asinhf(value); }
float __wrap_acoshf(float value) { return acoshf(value); }
float __wrap_atanhf(float value) { return atanhf(value); }

const mp_obj_type_t c_mp_type;

void c_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    c_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "C(is_initialized=%s)",
              self->is_initialized ? "true" : "false");
}

mp_obj_t c_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw,
                       const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    c_mp_obj_t *self = mp_obj_malloc_with_finaliser(c_mp_obj_t, &c_mp_type);
    self->base.type = &c_mp_type;
    self->is_initialized = true;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t c_mp_del(mp_obj_t self_in)
{
    c_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self)
        self->is_initialized = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(c_mp_del_obj, c_mp_del);

static int c_mp_run_source(const void *source, size_t length)
{
    cc_program_space = m_malloc(C_PROGRAM_SPACE_SIZE);
    if (!cc_program_space)
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("not enough RAM for C program"));

    int result = cc_run_source(source, length);
    m_free(cc_program_space);
    gc_collect();
    cc_program_space = NULL;
    return result;
}

mp_obj_t c_mp_run(mp_obj_t self_in, mp_obj_t source)
{
    (void)self_in;
    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(source, &bufinfo, MP_BUFFER_READ))
        mp_raise_TypeError(MP_ERROR_TEXT("expected a string"));
    return mp_obj_new_int(c_mp_run_source(bufinfo.buf, bufinfo.len));
}
static MP_DEFINE_CONST_FUN_OBJ_2(c_mp_run_obj, c_mp_run);

mp_obj_t c_mp_exec(mp_obj_t self_in, mp_obj_t path)
{
    (void)self_in;
#ifndef C_STORAGE_ENABLED
    (void)path;
    return mp_obj_new_int(-1);
#else
    const char *filename = mp_obj_str_get_str(path);
    size_t size = storage_file_size(filename);
    if (size > C_SOURCE_MAX)
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("source file is too large"));
    if (size == 0)
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("file not found"));

    char *source = m_new(char, size);
    size_t bytes_read = storage_file_read(filename, source, size);
    if (bytes_read != size)
    {
        m_del(char, source, size);
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("failed to read file"));
    }
    int result = c_mp_run_source(source, size);
    m_del(char, source, size);
    return mp_obj_new_int(result);
#endif
}
static MP_DEFINE_CONST_FUN_OBJ_2(c_mp_exec_obj, c_mp_exec);

void c_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    c_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] != MP_OBJ_NULL)
    {
        switch (attribute)
        {
        case MP_QSTR_is_initialized:
            destination[0] = mp_obj_new_bool(self->is_initialized);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&c_mp_del_obj);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            return;
        };
    }
}

static const mp_rom_map_elem_t c_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_exec), MP_ROM_PTR(&c_mp_exec_obj)},
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&c_mp_run_obj)},
};
static MP_DEFINE_CONST_DICT(c_mp_locals_dict, c_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    c_mp_type,
    MP_QSTR_C,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, c_mp_print,
    make_new, c_mp_make_new,
    attr, c_mp_attr,
    locals_dict, &c_mp_locals_dict);

static const mp_rom_map_elem_t c_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_c)},
    {MP_ROM_QSTR(MP_QSTR_C), MP_ROM_PTR(&c_mp_type)},
};
static MP_DEFINE_CONST_DICT(c_module_globals, c_module_globals_table);

const mp_obj_module_t c_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&c_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_c, c_user_cmodule);