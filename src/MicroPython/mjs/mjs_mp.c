#include <string.h>
#include "mjs_mp.h"
#include "mjs/mjs.h"
#include "lib/lib.h"

#if defined(PICOCALC_ESP32_P4)
#include "../PicoCalc/sd/storage.h"
#elif defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC) || defined(CARDPUTER) || defined(WAVESHARE_2_06) || defined(CROWPANEL_WATCH_2_01) || defined(PANCAKE) || defined(WAVESHARE_C5_3_5) || defined(V8) || defined(POOM) || defined(PICO_DUO)
#include "../sd/storage.h"
#elif defined(FLIPPER_ZERO)
#include "../Flippper/sd/storage.h"
#elif defined(DESKTOP)
#include "../Desktop/desktop_bridge.h"
#define storage_file_size desktop_storage_file_size
#define storage_file_read desktop_storage_file_read
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
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self || !self->is_initialized)
        return mp_const_none;
    if (self->mjs)
    {
        lib_unload_modules(self->mjs);
        mjs_destroy(self->mjs);
        self->mjs = NULL;
    }
    self->is_initialized = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mjs_mp_del_obj, mjs_mp_del);

static int mjs_is_word_char(char c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '$';
}

// Condense JS in place: strip comments, collapse whitespace
static size_t mjs_condense(char *buf, size_t len)
{
    size_t i = 0, o = 0;
    int sp = 0;    // open template ${} levels
    char ret[16];  // resume sub-state per level
    int brd[16];   // brace depth per level
    char sub = 0;  // 0 code, '\\'' '"' '`' literal, 'l' line comment, 'b' block comment, 'r' regex
    char last = 0; // last significant output char
    int in_class = 0;
    while (i < len)
    {
        char c = buf[i];
        if (sub == '\'' || sub == '"' || sub == '`')
        {
            if (sub == '`' && c == '$' && i + 1 < len && buf[i + 1] == '{' && sp < 16)
            {
                ret[sp] = '`';
                brd[sp] = 1;
                sp++;
                sub = 0;
                last = '{';
            }
            if (c == '\\' && i + 1 < len)
            {
                buf[o++] = c;
                buf[o++] = buf[i + 1];
                i += 2;
                continue;
            }
            buf[o++] = c;
            if (c == sub)
            {
                sub = 0;
            }
            last = c;
            i++;
            continue;
        }
        if (sub == 'l')
        {
            if (c == '\n')
            {
                buf[o++] = '\n';
                last = '\n';
                sub = 0;
            }
            i++;
            continue;
        }
        if (sub == 'b')
        {
            if (c == '*' && i + 1 < len && buf[i + 1] == '/')
            {
                sub = 0;
                i += 2;
                continue;
            }
            if (c == '\n' || c == '\r')
            {
                buf[o++] = '\n';
            }
            i++;
            continue;
        }
        if (sub == 'r')
        {
            if (c == '\\' && i + 1 < len)
            {
                buf[o++] = c;
                buf[o++] = buf[i + 1];
                i += 2;
                continue;
            }
            if (c == '\n')
            {
                // unterminated regex, fall back to code
                sub = 0;
                last = '\n';
                i++;
                continue;
            }
            buf[o++] = c;
            if (in_class)
            {
                if (c == ']')
                    in_class = 0;
                i++;
                continue;
            }
            if (c == '[')
            {
                in_class = 1;
                i++;
                continue;
            }
            if (c == '/')
            {
                in_class = 0;
                sub = 0;
                last = c;
                i++;
                continue;
            }
            i++;
            continue;
        }
        // code context
        if (c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v')
        {
            size_t j = i;
            int nl = 0;
            while (j < len && (buf[j] == ' ' || buf[j] == '\t' || buf[j] == '\n' || buf[j] == '\r' || buf[j] == '\f' || buf[j] == '\v'))
            {
                if (buf[j] == '\n' || buf[j] == '\r')
                    nl = 1;
                j++;
            }
            char next = (j < len) ? buf[j] : 0;
            int keep = nl || (mjs_is_word_char(last) && mjs_is_word_char(next)) || (last == '+' && next == '+') || (last == '-' && next == '-') || (mjs_is_word_char(last) && (next == '+' || next == '-') && j + 1 < len && (buf[j + 1] == '+' || buf[j + 1] == '-'));
            if (keep)
            {
                buf[o++] = nl ? '\n' : ' ';
                last = nl ? '\n' : ' ';
            }
            i = j;
            continue;
        }
        if (c == '/')
        {
            if (i + 1 < len && buf[i + 1] == '/')
            {
                sub = 'l';
                i++;
                continue;
            }
            if (i + 1 < len && buf[i + 1] == '*')
            {
                sub = 'b';
                i += 2;
                continue;
            }
            int div_ctx = mjs_is_word_char(last) || last == ')' || (last == ']' && sp == 0) || last == '}' || last == '+' || last == '-';
            if (!div_ctx)
            {
                buf[o++] = c;
                sub = 'r';
                in_class = 0;
                i++;
                continue;
            }
        }
        if (c == '\'' || c == '"' || c == '`')
        {
            sub = c;
        }
        if (c == '{')
        {
            if (sp > 0)
                brd[sp - 1]++;
        }
        if (c == '}' && sp > 0)
        {
            if (--brd[sp - 1] == 0)
            {
                sp--;
                last = '}';
                sub = (sp == 0) ? 0 : ret[sp - 1];
                i++;
                continue;
            }
        }
        buf[o++] = c;
        last = c;
        i++;
    }
    return o;
}

mp_obj_t mjs_mp_exec(mp_obj_t self_in, mp_obj_t path)
{
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);

    mp_buffer_info_t bufinfo;
    if (!mp_get_buffer(path, &bufinfo, MP_BUFFER_READ))
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected a string"));
    }

    mjs_val_t result = mjs_mk_undefined();
#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC) || defined(PICOCALC_ESP32_P4) || defined(CARDPUTER) || defined(WAVESHARE_2_06) || defined(CROWPANEL_WATCH_2_01) || defined(PANCAKE) || defined(WAVESHARE_C5_3_5) || defined(V8) || defined(FLIPPER_ZERO) || defined(DESKTOP) || defined(POOM) || defined(PICO_DUO)
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
    size_t clen = mjs_condense(buf, bytes_read);
    buf[clen] = '\0';

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

    char *buf = m_new(char, bufinfo.len + 1);
    memcpy(buf, bufinfo.buf, bufinfo.len);
    size_t clen = mjs_condense(buf, bufinfo.len);
    buf[clen] = '\0';

    mjs_val_t result = mjs_mk_undefined();
    mjs_err_t err = mjs_exec(self->mjs, buf, &result);
    m_free(buf);

    if (err != MJS_OK)
    {
        const char *err_str = mjs_strerror(self->mjs, err);
        mp_raise_msg_varg(&mp_type_RuntimeError, MP_ERROR_TEXT("MJS error: %s"), err_str);
    }

    return mjs_val_to_mp_obj(self->mjs, result);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mjs_mp_run_obj, mjs_mp_run);

mp_obj_t mjs_mp_reset(mp_obj_t self_in)
{
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self && self->mjs)
    {
        lib_unload_modules(self->mjs);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mjs_mp_reset_obj, mjs_mp_reset);

void mjs_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    mjs_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
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
    {MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&mjs_mp_reset_obj)},
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
