#include <stdlib.h>
#include <string.h>
#include "mbs_console.h"
#include "mbs_host.h"

void mbs_console_init(mbs_console *c, mbs_host_ops *ops, int screen_w,
                      int screen_h, int font_w, int font_h, int fg, int bg,
                      int sel)
{
    memset(c, 0, sizeof(*c));
    c->ops = ops;
    c->font_w = font_w > 0 ? font_w : 8;
    c->font_h = font_h > 0 ? font_h : 8;
    c->screen_w = screen_w > 0 ? screen_w : 320;
    c->screen_h = screen_h > 0 ? screen_h : 240;
    c->columns = c->screen_w / c->font_w;
    if (c->columns < 8)
        c->columns = 8;
    c->rows = c->screen_h / c->font_h;
    if (c->rows < 4)
        c->rows = 4;
    c->max_lines = 400;
    c->fg = fg;
    c->bg = bg;
    c->sel = sel;
    c->dirty = 1;
    mbs_str_init(&c->footer);
    mbs_str_set(&c->footer, "BACK=exit");
    mbs_str_init(&c->cur);
    mbs_ptrarr_init(&c->lines);
    c->fs = 8;
}

void mbs_console_free(mbs_console *c)
{
    for (int i = 0; i < c->lines.len; i++)
    {
        mbs_str *s = (mbs_str *)c->lines.items[i];
        mbs_str_free(s);
        m_free(s);
    }
    mbs_ptrarr_free(&c->lines);
    mbs_str_free(&c->cur);
    mbs_str_free(&c->footer);
}

static void _trim(mbs_console *c)
{
    while (c->lines.len > c->max_lines)
    {
        mbs_str *s = (mbs_str *)c->lines.items[0];
        mbs_str_free(s);
        m_free(s);
        memmove(c->lines.items, c->lines.items + 1,
                (c->lines.len - 1) * sizeof(void *));
        c->lines.len--;
    }
}

static void _flush_line(mbs_console *c)
{
    mbs_str *line = (mbs_str *)m_malloc(sizeof(mbs_str));
    *line = mbs_str_clone(&c->cur);
    mbs_ptrarr_push(&c->lines, line);
    mbs_str_set(&c->cur, "");
    _trim(c);
}

static void _wrap_cur(mbs_console *c)
{
    while (c->cur.len > c->columns)
    {
        mbs_str *line = (mbs_str *)m_malloc(sizeof(mbs_str));
        *line = mbs_str_sub(&c->cur, 0, c->columns);
        mbs_ptrarr_push(&c->lines, line);
        mbs_str tmp = mbs_str_sub(&c->cur, c->columns, c->cur.len - c->columns);
        mbs_str_free(&c->cur);
        c->cur = tmp;
        _trim(c);
    }
}

void mbs_console_goto(mbs_console *c, int col, int row, int size)
{
    c->has_pos = 1;
    c->pos_row = row > 0 ? row : 0;
    c->pos_col = col > 0 ? col : 0;
    if (size > 0)
        c->fs = size;
    c->dirty = 1;
}

static void _output_at(mbs_console *c, const char *text, int len)
{
    int row = c->pos_row, col = c->pos_col;
    while (c->lines.len <= row)
    {
        mbs_str *line = (mbs_str *)m_malloc(sizeof(mbs_str));
        mbs_str_init(line);
        mbs_ptrarr_push(&c->lines, line);
    }
    int i = 0;
    while (i < len)
    {
        char ch = text[i];
        if (ch == '\n')
        {
            row += 1;
            col = 0;
            while (c->lines.len <= row)
            {
                mbs_str *line = (mbs_str *)m_malloc(sizeof(mbs_str));
                mbs_str_init(line);
                mbs_ptrarr_push(&c->lines, line);
            }
            i += 1;
            continue;
        }
        mbs_str *line = (mbs_str *)c->lines.items[row];
        while (line->len < col)
            mbs_str_appendc(line, ' ');
        // overwrite one character at col
        if (col < line->len)
        {
            line->data[col] = ch;
        }
        else
        {
            mbs_str_appendc(line, ch);
        }
        col += 1;
        i += 1;
    }
    c->pos_row = row;
    c->pos_col = col;
    _trim(c);
    c->dirty = 1;
}

void mbs_console_output(mbs_console *c, const char *text, int len)
{
    if (c->has_pos)
    {
        _output_at(c, text, len);
        return;
    }
    // split on '\n'
    int start = 0;
    for (int i = 0; i <= len; i++)
    {
        if (i == len || text[i] == '\n')
        {
            int part_len = i - start;
            mbs_str_append(&c->cur, text + start, part_len);
            if (i < len)
            {
                _flush_line(c);
            }
            else
            {
                _wrap_cur(c);
            }
            start = i + 1;
        }
    }
    c->dirty = 1;
}

void mbs_console_newline(mbs_console *c)
{
    _flush_line(c);
    c->dirty = 1;
}

void mbs_console_echo(mbs_console *c, char ch)
{
    mbs_str_appendc(&c->cur, ch);
    _wrap_cur(c);
    c->dirty = 1;
}

void mbs_console_backspace(mbs_console *c)
{
    if (c->cur.len > 0)
    {
        c->cur.len--;
        if (c->cur.data)
            c->cur.data[c->cur.len] = '\0';
        c->dirty = 1;
    }
}

void mbs_console_clear(mbs_console *c)
{
    for (int i = 0; i < c->lines.len; i++)
    {
        mbs_str *s = (mbs_str *)c->lines.items[i];
        mbs_str_free(s);
        m_free(s);
    }
    c->lines.len = 0;
    mbs_str_set(&c->cur, "");
    c->dirty = 1;
}

int mbs_console_pos(mbs_console *c)
{
    return c->cur.len;
}

void mbs_console_set_input_active(mbs_console *c, int active)
{
    c->input_active = active;
}

void mbs_console_set_footer(mbs_console *c, const char *footer)
{
    mbs_str_set(&c->footer, footer);
}

void mbs_console_render(mbs_console *c)
{
    if (!c->dirty)
        return;
    if (c->ops && c->ops->console_render)
        c->ops->console_render(c->ops->host, c);
    c->dirty = 0;
}
