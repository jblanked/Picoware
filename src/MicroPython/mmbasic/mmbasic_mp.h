/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "lib/mbs.h"

    typedef struct _mmbasic_obj_t
    {
        mp_obj_base_t base;
        mbs_host_ops ops;
        mbs_runtime rt;
        mbs_console console;
        mbs_gfx gfx;
        mbs_interp interp;
        uint32_t last_present_ms;
        mbs_node *program;
    } mmbasic_obj_t;

    int mmbasic_load(mmbasic_obj_t *self, const char *source, size_t len);
    mp_obj_t mmbasic_start(size_t n_args, const mp_obj_t *pos_args,
                           mp_map_t *kw_args);
    mp_obj_t mmbasic_tick(mp_obj_t self_in, mp_obj_t max_time_ms);
    mp_obj_t mmbasic_feed_char(mp_obj_t self_in, mp_obj_t ch);
    mp_obj_t mmbasic_render(mp_obj_t self_in, mp_obj_t force_in);
    mp_obj_t mmbasic_set_footer(mp_obj_t self_in, mp_obj_t text);
    mp_obj_t mmbasic_console_output(mp_obj_t self_in, mp_obj_t text);
    mp_obj_t mmbasic_has_graphics(mp_obj_t self_in);
    mp_obj_t mmbasic_del(mp_obj_t self_in);
    void mmbasic_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
    mp_obj_t mmbasic_make_new(const mp_obj_type_t *type, size_t n_args,
                              size_t n_kw, const mp_obj_t *args);

    extern const mp_obj_type_t mmbasic_type;

#ifdef __cplusplus
}
#endif
