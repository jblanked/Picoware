#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "mbs_gfx.h"
#include "mbs_host.h"

static const struct
{
    const char *name;
    int rgb;
} NAMED_COLORS[] = {
    {"black", 0x000000},
    {"white", 0xFFFFFF},
    {"red", 0xFF0000},
    {"green", 0x00FF00},
    {"blue", 0x0000FF},
    {"yellow", 0xFFFF00},
    {"cyan", 0x00FFFF},
    {"magenta", 0xFF00FF},
    {"orange", 0xFF8000},
    {"pink", 0xFF0080},
    {"brown", 0xA52A2A},
    {"grey", 0x808080},
    {"gray", 0x808080},
    {"darkgrey", 0x404040},
    {"darkgray", 0x404040},
    {"lightgrey", 0xC0C0C0},
    {"lightgray", 0xC0C0C0},
    {"purple", 0x800080},
    {"myrtle", 0x21421E},
    {"maroon", 0x800000},
    {"navy", 0x000080},
    {"teal", 0x008080},
    {"olive", 0x808000},
    {"silver", 0xC0C0C0},
    {"lime", 0x00FF00},
    {"aqua", 0x00FFFF},
    {"fuchsia", 0xFF00FF},
    {"gold", 0xFFD700},
    {"violet", 0xEE82EE},
};

int mbs_rgb_to_565(int color24)
{
    int color = color24 & 0xFFFFFF;
    int r = (color >> 16) & 0xFF;
    int g = (color >> 8) & 0xFF;
    int b = color & 0xFF;
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
}

int mbs_gfx_named_color(const char *name, int *out)
{
    if (!name)
        return 0;
    char buf[24];
    int n = 0;
    while (name[n] && n < (int)sizeof(buf) - 1)
    {
        char c = name[n];
        if (c >= 'A' && c <= 'Z')
            c = c - 'A' + 'a';
        buf[n] = c;
        n++;
    }
    buf[n] = 0;
    while (n > 0 && (buf[n - 1] == ' ' || buf[n - 1] == '\t'))
        buf[--n] = 0;
    int b = 0;
    while (buf[b] == ' ' || buf[b] == '\t')
        b++;
    for (int i = 0; i < (int)(sizeof(NAMED_COLORS) / sizeof(NAMED_COLORS[0])); i++)
    {
        if (strcmp(NAMED_COLORS[i].name, buf + b) == 0)
        {
            *out = NAMED_COLORS[i].rgb;
            return 1;
        }
    }
    return 0;
}

void mbs_gfx_init(mbs_gfx *g, mbs_host_ops *ops, int w, int h, int bg, int fs)
{
    memset(g, 0, sizeof(*g));
    g->ops = ops;
    g->cur_color = 0xFFFFFF;
    g->pen_down = 1;
    g->tx = 0.0;
    g->ty = 0.0;
    g->thead = 0.0;
    g->w = w > 0 ? w : 320;
    g->h = h > 0 ? h : 240;
    g->bg = bg;
    g->fs = fs > 0 ? fs : 8;
    g->display_active = 0;
    g->has_drawn = 0;
}

void mbs_gfx_free(mbs_gfx *g)
{
    (void)g;
}

void mbs_gfx_present(mbs_gfx *g)
{
    if (g->ops && g->ops->g_swap && g->has_drawn)
        g->ops->g_swap(g->ops->host);
}

static int _c(mbs_gfx *g, int has_color, int color)
{
    if (!has_color)
        return mbs_rgb_to_565(g->cur_color);
    // names resolved to RGB ints
    return mbs_rgb_to_565(color);
}

void mbs_gfx_cls(mbs_gfx *g, int has_color, int color)
{
    g->has_drawn = 1;
    int c = has_color ? mbs_rgb_to_565(color) : mbs_rgb_to_565(g->bg);
    if (g->ops && g->ops->g_clear)
        g->ops->g_clear(g->ops->host, c);
}

void mbs_gfx_pixel(mbs_gfx *g, double x, double y, int has_color, int color)
{
    g->has_drawn = 1;
    if (g->ops && g->ops->g_pixel)
        g->ops->g_pixel(g->ops->host, (int)x, (int)y, _c(g, has_color, color));
}

static void _thick_line(mbs_gfx *g, double x1, double y1, double x2, double y2,
                        double thick, int col)
{
    if (!g->ops)
        return;
    if (x1 == x2)
    {
        g->ops->g_fill_rect(g->ops->host, (int)(x1 - thick / 2),
                            (int)(y1 < y2 ? y1 : y2), (int)thick,
                            (int)(fabs(y2 - y1) + 1), col);
    }
    else if (y1 == y2)
    {
        g->ops->g_fill_rect(g->ops->host, (int)(x1 < x2 ? x1 : x2),
                            (int)(y1 - thick / 2),
                            (int)(fabs(x2 - x1) + 1), (int)thick, col);
    }
    else
    {
        g->ops->g_line(g->ops->host, (int)x1, (int)y1, (int)x2, (int)y2, col);
    }
}

void mbs_gfx_line(mbs_gfx *g, double x1, double y1, double x2, double y2,
                  int has_thick, double thick, int has_color, int color)
{
    g->has_drawn = 1;
    int col = _c(g, has_color, color);
    if (has_thick && thick > 1)
    {
        _thick_line(g, x1, y1, x2, y2, thick, col);
    }
    else if (g->ops && g->ops->g_line)
    {
        g->ops->g_line(g->ops->host, (int)x1, (int)y1, (int)x2, (int)y2, col);
    }
}

void mbs_gfx_box(mbs_gfx *g, double x, double y, double w, double h,
                 int has_thick, double thick, int has_outline, int outline,
                 int has_fill, int fill)
{
    g->has_drawn = 1;
    if (g->ops)
    {
        if (has_fill)
            g->ops->g_fill_rect(g->ops->host, (int)x, (int)y, (int)w, (int)h,
                                _c(g, 1, fill));
        if (has_outline)
            g->ops->g_rect(g->ops->host, (int)x, (int)y, (int)w, (int)h,
                           _c(g, 1, outline));
        else if (!has_fill)
            g->ops->g_rect(g->ops->host, (int)x, (int)y, (int)w, (int)h,
                           _c(g, 0, 0));
    }
    (void)has_thick;
    (void)thick;
}

void mbs_gfx_circle(mbs_gfx *g, double x, double y, double r, mbs_ptrarr *args)
{
    g->has_drawn = 1;
    // last fill, previous outline
    mbs_val *fill = NULL;
    mbs_val *outline = NULL;
    for (int i = (args ? args->len : 0) - 1; i >= 0; i--)
    {
        mbs_val *v = (mbs_val *)args->items[i];
        if (!v)
            continue;
        if (v->kind == MBS_VAL_NUM && (v->num == -1.0 || v->num == 0.0))
        {
            // 1/0 = MMBasic booleans
            continue;
        }
        if (!fill)
            fill = v;
        else if (!outline)
            outline = v;
    }
    if (g->ops)
    {
        if (fill && mbs_val_num(fill) != 0)
            g->ops->g_fill_circle(g->ops->host, (int)x, (int)y, (int)r,
                                  _c(g, 1, (int)mbs_val_num(fill)));
        if (outline && mbs_val_num(outline) != 0)
            g->ops->g_circle(g->ops->host, (int)x, (int)y, (int)r,
                             _c(g, 1, (int)mbs_val_num(outline)));
        else if (!fill)
            g->ops->g_circle(g->ops->host, (int)x, (int)y, (int)r, _c(g, 0, 0));
    }
}

void mbs_gfx_polygon(mbs_gfx *g, mbs_ptrarr *xs, mbs_ptrarr *ys,
                     int has_outline, int outline, int has_fill, int fill)
{
    g->has_drawn = 1;
    int n = (xs->len < ys->len) ? xs->len : ys->len;
    if (n < 3 || !g->ops)
        return;
    if (has_fill && fill != 0)
    {
        int col = mbs_rgb_to_565(fill);
        for (int i = 1; i < n - 1; i++)
        {
            g->ops->g_fill_tri(g->ops->host,
                               (int)mbs_val_num((mbs_val *)xs->items[0]),
                               (int)mbs_val_num((mbs_val *)ys->items[0]),
                               (int)mbs_val_num((mbs_val *)xs->items[i]),
                               (int)mbs_val_num((mbs_val *)ys->items[i]),
                               (int)mbs_val_num((mbs_val *)xs->items[i + 1]),
                               (int)mbs_val_num((mbs_val *)ys->items[i + 1]),
                               col);
        }
    }
    if (has_outline && outline != 0)
    {
        int col = mbs_rgb_to_565(outline);
        for (int i = 0; i < n; i++)
        {
            int j = (i + 1) % n;
            g->ops->g_line(g->ops->host,
                           (int)mbs_val_num((mbs_val *)xs->items[i]),
                           (int)mbs_val_num((mbs_val *)ys->items[i]),
                           (int)mbs_val_num((mbs_val *)xs->items[j]),
                           (int)mbs_val_num((mbs_val *)ys->items[j]), col);
        }
    }
}

void mbs_gfx_color(mbs_gfx *g, int has_fg, int fg, int has_bg, int bg)
{
    if (has_fg)
        g->cur_color = fg;
    if (has_bg)
        g->bg = bg;
}

void mbs_gfx_set_font_size(mbs_gfx *g, int size)
{
    static const int sizes[5] = {8, 8, 12, 16, 20};
    if (size >= 0 && size <= 4)
        g->fs = sizes[size];
    else
        g->fs = 8;
}

void mbs_gfx_text(mbs_gfx *g, double x, double y, const char *s)
{
    g->has_drawn = 1;
    if (g->ops && g->ops->g_text)
        g->ops->g_text(g->ops->host, (int)x, (int)y, s,
                       mbs_rgb_to_565(g->cur_color), g->fs);
}

static void _turtle_step(mbs_gfx *g, double dist)
{
    double rad = g->thead * M_PI / 180.0;
    double nx = g->tx + dist * cos(rad);
    double ny = g->ty - dist * sin(rad);
    if (g->pen_down && g->ops && g->ops->g_line)
        g->ops->g_line(g->ops->host, (int)g->tx, (int)g->ty, (int)nx, (int)ny,
                       mbs_rgb_to_565(g->cur_color));
    g->tx = nx;
    g->ty = ny;
}

void mbs_gfx_framebuffer(mbs_gfx *g, const char *sub, mbs_ptrarr *args)
{
    (void)args;
    if (strcmp(sub, "create") == 0 || strcmp(sub, "write") == 0)
    {
        g->display_active = 1;
        g->has_drawn = 1;
        mbs_gfx_cls(g, 0, 0);
    }
    else if (strcmp(sub, "copy") == 0)
    {
        g->display_active = 1;
        g->has_drawn = 1;
        mbs_gfx_swap(g);
    }
    else if (strcmp(sub, "close") == 0)
    {
        g->display_active = 0;
    }
}

void mbs_gfx_turtle(mbs_gfx *g, const char *sub, mbs_ptrarr *args)
{
    double a0 = (args && args->len > 0 && args->items[0]) ? mbs_val_num((mbs_val *)args->items[0]) : 0.0;
    double a1 = (args && args->len > 1 && args->items[1]) ? mbs_val_num((mbs_val *)args->items[1]) : 0.0;
    if (strcmp(sub, "reset") == 0 || strcmp(sub, "home") == 0)
    {
        mbs_gfx_cls(g, 0, 0);
        g->pen_down = 1;
        g->tx = g->w / 2.0;
        g->ty = g->h / 2.0;
        g->thead = 0.0;
    }
    else if (strcmp(sub, "pen down") == 0)
    {
        g->pen_down = 1;
    }
    else if (strcmp(sub, "pen up") == 0)
    {
        g->pen_down = 0;
    }
    else if (strcmp(sub, "forward") == 0)
    {
        _turtle_step(g, a0);
    }
    else if (strcmp(sub, "back") == 0)
    {
        _turtle_step(g, -a0);
    }
    else if (strcmp(sub, "right") == 0)
    {
        g->thead = fmod(g->thead + a0, 360.0);
        if (g->thead < 0)
            g->thead += 360.0;
    }
    else if (strcmp(sub, "left") == 0)
    {
        g->thead = fmod(g->thead - a0, 360.0);
        if (g->thead < 0)
            g->thead += 360.0;
    }
    else if (strcmp(sub, "set xy") == 0 || strcmp(sub, "setxy") == 0)
    {
        g->tx = a0;
        g->ty = a1;
    }
    else if (strcmp(sub, "set heading") == 0 ||
             strcmp(sub, "setheading") == 0 ||
             strcmp(sub, "heading") == 0)
    {
        g->thead = fmod(a0, 360.0);
        if (g->thead < 0)
            g->thead += 360.0;
    }
}

void mbs_gfx_save_image(mbs_gfx *g, const char *filename)
{
    (void)g;
    (void)filename;
}

int mbs_gfx_swap(mbs_gfx *g)
{
    if (g->ops && g->ops->g_swap)
        g->ops->g_swap(g->ops->host);
    return 1;
}
