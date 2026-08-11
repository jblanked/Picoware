#ifndef MBS_GFX_H
#define MBS_GFX_H

#include "mbs_util.h"

#ifdef __cplusplus
extern "C"
{
#endif

    typedef struct mbs_host_ops mbs_host_ops;

    typedef struct mbs_gfx
    {
        mbs_host_ops *ops;
        int cur_color; // 24-bit MMBasic colour
        int bg;        // 24-bit background
        int pen_down;
        double tx, ty, thead;
        int w, h;
        int fs;
        int display_active;
        int has_drawn;
    } mbs_gfx;

    void mbs_gfx_init(mbs_gfx *g, mbs_host_ops *ops, int w, int h, int bg, int fs);
    void mbs_gfx_free(mbs_gfx *g);
    void mbs_gfx_present(mbs_gfx *g);
    void mbs_gfx_cls(mbs_gfx *g, int has_color, int color);
    void mbs_gfx_pixel(mbs_gfx *g, double x, double y, int has_color, int color);
    void mbs_gfx_line(mbs_gfx *g, double x1, double y1, double x2, double y2,
                      int has_thick, double thick, int has_color, int color);
    void mbs_gfx_box(mbs_gfx *g, double x, double y, double w, double h,
                     int has_thick, double thick, int has_outline, int outline,
                     int has_fill, int fill);
    void mbs_gfx_circle(mbs_gfx *g, double x, double y, double r,
                        mbs_ptrarr *args); // mbs_val list (may be NULL)
    void mbs_gfx_polygon(mbs_gfx *g, mbs_ptrarr *xs, mbs_ptrarr *ys,
                         int has_outline, int outline, int has_fill, int fill);
    void mbs_gfx_color(mbs_gfx *g, int has_fg, int fg, int has_bg, int bg);
    void mbs_gfx_set_font_size(mbs_gfx *g, int size);
    void mbs_gfx_text(mbs_gfx *g, double x, double y, const char *s);
    void mbs_gfx_framebuffer(mbs_gfx *g, const char *sub, mbs_ptrarr *args);
    void mbs_gfx_turtle(mbs_gfx *g, const char *sub, mbs_ptrarr *args);
    void mbs_gfx_save_image(mbs_gfx *g, const char *filename);
    int mbs_gfx_swap(mbs_gfx *g);
    int mbs_rgb_to_565(int color24);
    int mbs_gfx_named_color(const char *name, int *out);

#ifdef __cplusplus
}
#endif

#endif // MBS_GFX_H
