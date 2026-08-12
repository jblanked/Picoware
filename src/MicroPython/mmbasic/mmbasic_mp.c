#include "mmbasic_mp.h"
#include <string.h>
#include <stdio.h>
#include <time.h>
#include "py/objstr.h"
#include "py/objtuple.h"
#include "py/misc.h"
#include "lib/mbs.h"
#include "lcd_config.h"
#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif
#include "log_mp.h"
#include "storage.h"

#if defined(PANCAKE) || defined(WAVESHARE_2_06) || defined(V8) || defined(CARDPUTER)
static time_t host_rtc_now(void)
{
    return time(NULL);
}
#else
#include "pico/aon_timer.h"
static time_t host_rtc_now(void)
{
    struct timespec ts;
    aon_timer_get_time(&ts);
    return (time_t)ts.tv_sec;
}
#endif

#define MMBASIC_PRESENT_MS 33

const mp_obj_type_t mmbasic_type;

static void host_g_clear(void *h, int color)
{
    (void)h;
    LCD_MP_CLEAR((uint16_t)color);
}
static void host_g_pixel(void *h, int x, int y, int color)
{
    (void)h;
    LCD_MP_PIXEL((uint16_t)x, (uint16_t)y, (uint16_t)color);
}
static void host_g_line(void *h, int x1, int y1, int x2, int y2, int color)
{
    (void)h;
    LCD_MP_LINE((uint16_t)x1, (uint16_t)y1, (uint16_t)x2, (uint16_t)y2,
                (uint16_t)color);
}
static void host_g_rect(void *h, int x, int y, int w, int hh, int color)
{
    (void)h;
    LCD_MP_RECTANGLE((uint16_t)x, (uint16_t)y, (uint16_t)w, (uint16_t)hh,
                     (uint16_t)color);
}
static void host_g_fill_rect(void *h, int x, int y, int w, int hh, int color)
{
    (void)h;
    LCD_MP_FILL_RECTANGLE((uint16_t)x, (uint16_t)y, (uint16_t)w, (uint16_t)hh,
                          (uint16_t)color);
}
static void host_g_circle(void *h, int x, int y, int r, int color)
{
    (void)h;
    LCD_MP_CIRCLE((uint16_t)x, (uint16_t)y, (uint16_t)r, (uint16_t)color);
}
static void host_g_fill_circle(void *h, int x, int y, int r, int color)
{
    (void)h;
    LCD_MP_FILL_CIRCLE((uint16_t)x, (uint16_t)y, (uint16_t)r, (uint16_t)color);
}
static void host_g_fill_tri(void *h, int x1, int y1, int x2, int y2, int x3,
                            int y3, int color)
{
    (void)h;
    LCD_MP_FILL_TRIANGLE((uint16_t)x1, (uint16_t)y1, (uint16_t)x2, (uint16_t)y2,
                         (uint16_t)x3, (uint16_t)y3, (uint16_t)color);
}
static void host_g_text(void *h, int x, int y, const char *s, int color,
                        int font_size)
{
    (void)h;
    LCD_MP_TEXT((uint16_t)x, (uint16_t)y, s, (uint16_t)color,
                (FontSize)font_size);
}
static void host_g_swap(void *h)
{
    (void)h;
    LCD_MP_SWAP();
}

static void console_draw_text(int x, int y, const char *s, int color)
{
    LCD_MP_TEXT((uint16_t)x, (uint16_t)y, s, (uint16_t)color, FONT_DEFAULT);
}

static void host_console_render(void *h, mbs_console *c)
{
    (void)h;
    /* erase */
    LCD_MP_CLEAR((uint16_t)c->bg);
    /* display = lines + [cur]; draw the tail text_rows rows */
    int text_rows = c->rows - (c->footer.len ? 1 : 0);
    if (text_rows < 1)
        text_rows = 1;
    int total = c->lines.len + 1; /* + cur */
    int start = total - text_rows;
    if (start < 0)
        start = 0;
    int idx = start;
    int y = 0;
    for (int i = 0; i < text_rows && i < total; i++)
    {
        const char *line;
        if (idx < c->lines.len)
        {
            mbs_str *s = (mbs_str *)c->lines.items[idx];
            line = s->data ? s->data : "";
        }
        else
        {
            line = c->cur.data ? c->cur.data : "";
        }
        console_draw_text(0, y, line, c->fg);
        y += c->font_h;
        idx++;
    }
    if (c->footer.len)
    {
        console_draw_text(0, c->screen_h - c->font_h, c->footer.data, c->sel);
    }
    LCD_MP_SWAP();
}

static void host_log(void *h, const char *message)
{
    (void)h;
    log_message(message);
}

static uint32_t host_now_ms(void *h)
{
    (void)h;
    return mp_hal_ticks_ms();
}
static uint32_t host_ticks_add(void *h, uint32_t base, int32_t delta)
{
    (void)h;
    return (uint32_t)(base + delta);
}
static int32_t host_ticks_diff(void *h, uint32_t a, uint32_t b)
{
    (void)h;
    return (int32_t)(a - b);
}
static void host_get_time(void *h, int out[6])
{
    (void)h;
    time_t t = host_rtc_now();
    struct tm tm;
    localtime_r(&t, &tm);
    out[0] = tm.tm_year + 1900; /* year */
    out[1] = tm.tm_mon + 1;     /* month */
    out[2] = tm.tm_mday;        /* day */
    out[3] = tm.tm_hour;        /* hour */
    out[4] = tm.tm_min;         /* min */
    out[5] = tm.tm_sec;         /* sec */
}
static long host_epoch_now(void *h)
{
    (void)h;
    return (long)host_rtc_now();
}

int mmbasic_load(mmbasic_obj_t *self, const char *source, size_t len)
{
    if (self->program)
    {
        mbs_node_free(self->program);
        self->program = NULL;
    }
    mbs_error err;
    self->program = mbs_parse_source(source, (int)len, NULL, &err);
    if (!self->program)
        return 0;
    mbs_runtime_free(&self->rt);
    mbs_runtime_init(&self->rt, self->program, NULL);
    mbs_runtime_set_owner(&self->rt, &self->interp);
    return 1;
}

mp_obj_t mmbasic_start(size_t n_args, const mp_obj_t *pos_args,
                       mp_map_t *kw_args)
{
    enum
    {
        ARG_source,
        ARG_path
    };
    static const mp_arg_t allowed_args[] = {
        {MP_QSTR_source, MP_ARG_OBJ, {.u_obj = mp_const_none}},
        {MP_QSTR_path, MP_ARG_OBJ, {.u_obj = mp_const_none}},
    };
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(pos_args[0]);
    mp_arg_val_t args[2];
    mp_arg_parse_all(n_args - 1, pos_args + 1, kw_args, 2, allowed_args, args);
    mp_obj_t source = args[ARG_source].u_obj;
    mp_obj_t path = args[ARG_path].u_obj;

    if (source != mp_const_none)
    {
        const char *s = mp_obj_str_get_str(source);
        if (!mmbasic_load(self, s, strlen(s)))
            return mp_const_false;
    }
    else if (path != mp_const_none)
    {
        const char *fn = mp_obj_str_get_str(path);
        size_t size = storage_file_size(fn);
        if (size == 0 || size > 262144)
            return mp_const_false;
        char *buf = m_new(char, size);
        size_t n = storage_file_read(fn, buf, size);
        int ok = (n == size) && mmbasic_load(self, buf, (int)n);
        m_del(char, buf, size);
        if (!ok)
            return mp_const_false;
    }
    else
    {
        return mp_const_false;
    }

    mbs_interp_start(&self->interp);
    mbs_console_set_footer(&self->console, "BACK=exit");
    mbs_console_output(&self->console, "MMBasic 6.03  (Picoware)",
                       (int)strlen("MMBasic 6.03  (Picoware)"));
    mbs_console_output(&self->console, "-----------------------",
                       (int)strlen("-----------------------"));
    mbs_console_output(&self->console, "", 0);
    mbs_console_render(&self->console);
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(mmbasic_start_obj, 1, mmbasic_start);

mp_obj_t mmbasic_tick(mp_obj_t self_in, mp_obj_t max_time_ms)
{
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int mt = mp_obj_get_int(max_time_ms);
    mbs_tickstate st = mbs_interp_tick(&self->interp, 0, mt);
    mp_obj_t tuple[3] = {
        mp_obj_new_int(st.status),
        mp_obj_new_str(st.message, strlen(st.message)),
        mp_obj_new_int(st.line),
    };
    return mp_obj_new_tuple(3, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_2(mmbasic_tick_obj, mmbasic_tick);

mp_obj_t mmbasic_feed_char(mp_obj_t self_in, mp_obj_t ch)
{
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(self_in);
    size_t len;
    const char *s = mp_obj_str_get_data(ch, &len);
    if (len > 0 && s[0])
        mbs_interp_feed_char(&self->interp, s[0]);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mmbasic_feed_char_obj, mmbasic_feed_char);

mp_obj_t mmbasic_render(mp_obj_t self_in, mp_obj_t force_in)
{
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(self_in);
    bool force = mp_obj_is_true(force_in);

    mbs_console_set_input_active(&self->console,
                                 mbs_interp_is_input_pending(&self->interp));
    if (self->gfx.has_drawn)
    {
        uint32_t now = mp_hal_ticks_ms();
        if (force || self->last_present_ms == 0 ||
            (int32_t)(now - self->last_present_ms) >= MMBASIC_PRESENT_MS)
        {
            mbs_gfx_present(&self->gfx);
            self->last_present_ms = now;
        }
    }
    else
    {
        mbs_console_render(&self->console);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mmbasic_render_obj, mmbasic_render);

mp_obj_t mmbasic_set_footer(mp_obj_t self_in, mp_obj_t text)
{
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mbs_console_set_footer(&self->console, mp_obj_str_get_str(text));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mmbasic_set_footer_obj, mmbasic_set_footer);

mp_obj_t mmbasic_console_output(mp_obj_t self_in, mp_obj_t text)
{
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(self_in);
    size_t len;
    const char *s = mp_obj_str_get_data(text, &len);
    mbs_console_output(&self->console, s, (int)len);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mmbasic_console_output_obj, mmbasic_console_output);

mp_obj_t mmbasic_has_graphics(mp_obj_t self_in)
{
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(self->gfx.has_drawn);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mmbasic_has_graphics_obj, mmbasic_has_graphics);

mp_obj_t mmbasic_del(mp_obj_t self_in)
{
    mmbasic_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self)
        return mp_const_none;
    if (self->program)
    {
        mbs_node_free(self->program);
        self->program = NULL;
    }
    mbs_interp_free(&self->interp);
    mbs_runtime_free(&self->rt);
    mbs_console_free(&self->console);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mmbasic_del_obj, mmbasic_del);

void mmbasic_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    (void)self_in;
    if (destination[0] == MP_OBJ_NULL)
    {
        switch (attribute)
        {
        case MP_QSTR_has_graphics:
            destination[0] = MP_OBJ_FROM_PTR(&mmbasic_has_graphics_obj);
            return;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&mmbasic_del_obj);
            return;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            return;
        }
    }
}

static const mp_rom_map_elem_t mmbasic_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR__start), MP_ROM_PTR(&mmbasic_start_obj)},
    {MP_ROM_QSTR(MP_QSTR_tick), MP_ROM_PTR(&mmbasic_tick_obj)},
    {MP_ROM_QSTR(MP_QSTR_feed_char), MP_ROM_PTR(&mmbasic_feed_char_obj)},
    {MP_ROM_QSTR(MP_QSTR_render), MP_ROM_PTR(&mmbasic_render_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_footer), MP_ROM_PTR(&mmbasic_set_footer_obj)},
    {MP_ROM_QSTR(MP_QSTR_console_output), MP_ROM_PTR(&mmbasic_console_output_obj)},
};
static MP_DEFINE_CONST_DICT(mmbasic_locals_dict, mmbasic_locals_dict_table);

mp_obj_t mmbasic_make_new(const mp_obj_type_t *type, size_t n_args,
                          size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 9, 9, false);
    int fg = mp_obj_get_int(args[0]);
    int bg = mp_obj_get_int(args[1]);
    int sel = mp_obj_get_int(args[2]);
    int screen_w = mp_obj_get_int(args[3]);
    int screen_h = mp_obj_get_int(args[4]);
    int font_w = mp_obj_get_int(args[5]);
    int font_h = mp_obj_get_int(args[6]);
    int draw_bg = mp_obj_get_int(args[7]);
    int fdef_size = mp_obj_get_int(args[8]);
    mmbasic_obj_t *self = mp_obj_malloc_with_finaliser(mmbasic_obj_t, &mmbasic_type);
    self->base.type = &mmbasic_type;
    self->last_present_ms = 0;

    /* host callbacks */
    self->ops.host = self;
    self->ops.g_clear = host_g_clear;
    self->ops.g_pixel = host_g_pixel;
    self->ops.g_line = host_g_line;
    self->ops.g_rect = host_g_rect;
    self->ops.g_fill_rect = host_g_fill_rect;
    self->ops.g_circle = host_g_circle;
    self->ops.g_fill_circle = host_g_fill_circle;
    self->ops.g_fill_tri = host_g_fill_tri;
    self->ops.g_text = host_g_text;
    self->ops.g_swap = host_g_swap;
    self->ops.console_render = host_console_render;
    self->ops.log = host_log;
    self->ops.now_ms = host_now_ms;
    self->ops.ticks_add = host_ticks_add;
    self->ops.ticks_diff = host_ticks_diff;
    self->ops.get_time = host_get_time;
    self->ops.epoch_now = host_epoch_now;

    mbs_console_init(&self->console, &self->ops, screen_w, screen_h, font_w,
                     font_h, fg, bg, sel);
    mbs_gfx_init(&self->gfx, &self->ops, screen_w, screen_h, draw_bg,
                 fdef_size);
    mbs_runtime_init(&self->rt, NULL, NULL);
    mbs_interp_init(&self->interp, &self->rt, &self->console, &self->gfx,
                    &self->ops);
    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    mmbasic_type,
    MP_QSTR_MMBasic,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    make_new, mmbasic_make_new,
    attr, mmbasic_attr,
    locals_dict, &mmbasic_locals_dict);

static const mp_rom_map_elem_t mmbasic_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mmbasic)},
    {MP_ROM_QSTR(MP_QSTR_MMBasic), MP_ROM_PTR(&mmbasic_type)},
};
static MP_DEFINE_CONST_DICT(mmbasic_module_globals, mmbasic_module_globals_table);

const mp_obj_module_t mmbasic_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mmbasic_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_mmbasic, mmbasic_user_cmodule);
