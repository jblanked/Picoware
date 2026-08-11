#ifndef MBS_HOST_H
#define MBS_HOST_H

#include <stdint.h>

#ifdef __cplusplus
extern "C"
{
#endif

    typedef struct mbs_console mbs_console;

    // Callbacks from MicroPython glue
    typedef struct mbs_host_ops
    {
        void *host;

        // graphics primitives
        void (*g_clear)(void *host, int color);
        void (*g_pixel)(void *host, int x, int y, int color);
        void (*g_line)(void *host, int x1, int y1, int x2, int y2, int color);
        void (*g_rect)(void *host, int x, int y, int w, int h, int color);
        void (*g_fill_rect)(void *host, int x, int y, int w, int h, int color);
        void (*g_circle)(void *host, int x, int y, int r, int color);
        void (*g_fill_circle)(void *host, int x, int y, int r, int color);
        void (*g_fill_tri)(void *host, int x1, int y1, int x2, int y2, int x3,
                           int y3, int color);
        void (*g_text)(void *host, int x, int y, const char *s, int color,
                       int font_size);
        void (*g_swap)(void *host);

        // draw console rows + footer
        void (*console_render)(void *host, mbs_console *c);

        // misc
        void (*log)(void *host, const char *message);
        // ms since boot (SETTICK)
        uint32_t (*now_ms)(void *host);
        // wrapped ms (ticks_ms)
        uint32_t (*ticks_add)(void *host, uint32_t base, int32_t delta);
        int32_t (*ticks_diff)(void *host, uint32_t a, uint32_t b);
        // local clock into out[6]
        void (*get_time)(void *host, int out[6]);
        // Unix epoch seconds (NOW)
        long (*epoch_now)(void *host);
    } mbs_host_ops;

#ifdef __cplusplus
}
#endif

#endif // MBS_HOST_H
