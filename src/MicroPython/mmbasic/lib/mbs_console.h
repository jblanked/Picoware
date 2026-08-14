#ifndef MBS_CONSOLE_H
#define MBS_CONSOLE_H

#include "mbs_util.h"

#ifdef __cplusplus
extern "C"
{
#endif

    struct mbs_host_ops;

    typedef struct mbs_console
    {
        struct mbs_host_ops *ops;
        int columns, rows;
        int max_lines;
        int font_w, font_h;
        int screen_w, screen_h;
        int fg, bg, sel;
        mbs_str footer;
        mbs_ptrarr lines;     // completed lines
        mbs_str cur;          // current in-progress line
        mbs_str *tmp_display; // scratch for render
        int dirty;
        int input_active;
        int has_pos; // PRINT @(col,row[,size]) active
        int pos_row, pos_col;
        int fs;
    } mbs_console;

    void mbs_console_init(mbs_console *c, struct mbs_host_ops *ops, int screen_w,
                          int screen_h, int font_w, int font_h, int fg, int bg,
                          int sel);
    void mbs_console_free(mbs_console *c);
    void mbs_console_goto(mbs_console *c, int col, int row, int size);
    void mbs_console_output(mbs_console *c, const char *text, int len);
    void mbs_console_newline(mbs_console *c);
    void mbs_console_echo(mbs_console *c, char ch);
    void mbs_console_backspace(mbs_console *c);
    void mbs_console_clear(mbs_console *c);
    int mbs_console_pos(mbs_console *c); // POS(): current print column
    void mbs_console_set_input_active(mbs_console *c, int active);
    void mbs_console_set_footer(mbs_console *c, const char *footer);
    void mbs_console_render(mbs_console *c);

#ifdef __cplusplus
}
#endif

#endif // MBS_CONSOLE_H
