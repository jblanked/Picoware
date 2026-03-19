#include "textbox_mp.h"
#include "../lcd/lcd_config.h"

#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif

const mp_obj_type_t textbox_mp_type;

// Grow the line array if needed and append one entry.
static void textbox_add_line(textbox_mp_obj_t *self, uint32_t start, uint16_t length)
{
    if (self->total_lines >= self->line_capacity)
    {
        uint16_t new_cap = self->line_capacity ? (uint16_t)(self->line_capacity * 2) : TEXTBOX_INITIAL_LINE_CAPACITY;
        self->lines = m_renew(textbox_line_t, self->lines, self->line_capacity, new_cap);
        self->line_capacity = new_cap;
    }
    self->lines[self->total_lines].start = start;
    self->lines[self->total_lines].length = length;
    self->total_lines++;
}

// Word-wrap self->text into self->lines[].
static void textbox_wrap(textbox_mp_obj_t *self)
{
    self->total_lines = 0;

    const char *text = self->text;
    const size_t str_len = self->text_len;
    const uint16_t cpl = self->chars_per_line;

    size_t i = 0;
    size_t line_start = 0;
    uint16_t line_length = 0;

    while (i < str_len)
    {
        char c = text[i];

        // Hard newline: commit current line and reset
        if (c == '\n')
        {
            textbox_add_line(self, line_start, line_length);
            i++;
            // skip leading spaces on the new logical line
            while (i < str_len && text[i] == ' ')
                i++;
            line_start = i;
            line_length = 0;
            continue;
        }

        // Skip leading spaces at the start of a wrapped line
        if (line_length == 0)
        {
            while (i < str_len && text[i] == ' ')
                i++;
            line_start = i;
        }

        // Find the end of the current word
        size_t word_start = i;
        const char *sp = (const char *)memchr(text + i, ' ', str_len - i);
        const char *nl = (const char *)memchr(text + i, '\n', str_len - i);

        size_t word_end;
        if (!sp && !nl)
            word_end = str_len;
        else if (!sp)
            word_end = (size_t)(nl - text);
        else if (!nl)
            word_end = (size_t)(sp - text);
        else
            word_end = (sp < nl) ? (size_t)(sp - text) : (size_t)(nl - text);

        uint16_t word_len = (uint16_t)(word_end - word_start);

        // Word doesn't fit on this line → wrap before it
        if (line_length + word_len > cpl && line_length > 0)
        {
            textbox_add_line(self, line_start, line_length);
            line_start = word_start;
            line_length = 0;
        }

        // If a single word is wider than the line, hard-break it
        if (word_len > cpl)
        {
            while (word_len > 0)
            {
                uint16_t space = cpl - line_length;
                if (space == 0)
                {
                    textbox_add_line(self, line_start, line_length);
                    line_start = word_start;
                    line_length = 0;
                    space = cpl;
                }
                uint16_t take = (word_len < space) ? word_len : space;
                line_length += take;
                word_start += take;
                word_len -= take;
            }
            i = word_end;
        }
        else
        {
            line_length += word_len;
            i = word_end;
        }

        // Consume one trailing space (counts toward line length for next word gap)
        if (i < str_len && text[i] == ' ')
        {
            line_length++;
            i++;
        }
    }

    // Commit the last line; also emit an empty trailing line when text ends with '\n'
    // so the cursor lands on a fresh line rather than the end of the previous one.
    if (line_length > 0 || self->total_lines == 0 ||
        (str_len > 0 && text[str_len - 1] == '\n'))
        textbox_add_line(self, line_start, line_length);

    self->cache_valid = true;
}

// Draw the cursor as a static horizontal underline at the current cursor_pos.
static void textbox_draw_cursor(textbox_mp_obj_t *self, uint16_t first, uint16_t last)
{
    if (!self->show_cursor || self->total_lines == 0)
        return;

    // Find which wrapped line contains cursor_pos.
    uint16_t cursor_line = self->total_lines - 1;
    uint16_t cursor_col = 0;
    for (uint16_t i = 0; i < self->total_lines; i++)
    {
        uint32_t ls = self->lines[i].start;
        uint16_t ll = self->lines[i].length;
        // Treat empty lines as length 1 so cursor_pos==ls matches.
        uint16_t eff_len = ll > 0 ? ll : 1;
        // Also match when cursor sits on the '\n' that terminates this line
        // (the newline is NOT included in ll, leaving a one-byte gap otherwise).
        bool at_newline = (self->cursor_pos == (size_t)(ls + ll)) &&
                          (ls + ll < self->text_len) &&
                          (self->edit_buf[ls + ll] == '\n');
        if (self->cursor_pos >= ls &&
            (self->cursor_pos < ls + eff_len || i == self->total_lines - 1 || at_newline))
        {
            cursor_line = i;
            cursor_col = (uint16_t)(self->cursor_pos - ls);
            if (cursor_col > ll)
                cursor_col = ll; // clamp to end of line
            break;
        }
    }

    // Only draw if the cursor's line is currently on screen.
    if (cursor_line < first || cursor_line >= last)
        return;

    uint16_t char_w = font_get_width(FONT_DEFAULT) + font_get_spacing(FONT_DEFAULT);
    uint16_t cx = (uint16_t)(1 + cursor_col * char_w);
    // Place the 2px underline at the bottom of the character cell.
    uint16_t cy = (uint16_t)(self->pos_y + 5 + (uint32_t)(cursor_line - first) * self->spacing + self->spacing - 2);

    LCD_MP_FILL_RECTANGLE(cx, cy, char_w, 2, self->foreground_color);
}

// Draw the vertical scrollbar track + indicator.
static void textbox_draw_scrollbar(textbox_mp_obj_t *self)
{
    uint16_t track_x = self->box_width - TEXTBOX_SCROLLBAR_WIDTH - 1;
    uint16_t track_y = self->pos_y + 1;
    uint16_t track_h = (self->box_height > 2) ? (uint16_t)(self->box_height - 2) : self->box_height;

    // Track background
    LCD_MP_FILL_RECTANGLE(track_x, track_y, TEXTBOX_SCROLLBAR_WIDTH, track_h, self->background_color);

    if (self->total_lines == 0)
        return;

    // Indicator size (proportional to visible fraction)
    uint16_t bar_h;
    if (self->total_lines <= self->lines_per_screen)
    {
        bar_h = track_h; // all content visible → full bar
    }
    else
    {
        bar_h = (uint16_t)((uint32_t)track_h * self->lines_per_screen / self->total_lines);
        if (bar_h < self->spacing)
            bar_h = self->spacing; // minimum bar height
    }

    // Indicator position (follows current_line)
    uint16_t bar_y = track_y;
    if (self->total_lines > self->lines_per_screen && self->current_line >= self->lines_per_screen)
    {
        uint32_t scrollable = track_h - bar_h;
        uint32_t ratio_num = self->current_line + 1 - self->lines_per_screen;
        uint32_t ratio_den = self->total_lines - self->lines_per_screen;
        bar_y = (uint16_t)(track_y + (scrollable * ratio_num / ratio_den));
    }

    LCD_MP_FILL_RECTANGLE(track_x, bar_y, TEXTBOX_SCROLLBAR_WIDTH, bar_h, self->foreground_color);
}

// Render the visible lines and optional scrollbar, then swap.
static void textbox_display(textbox_mp_obj_t *self)
{
    // Clear the textbox region
    LCD_MP_FILL_RECTANGLE(0, self->pos_y, self->box_width, self->box_height, self->background_color);

    if (self->total_lines == 0)
    {
        LCD_MP_SWAP();
        return;
    }

    // Determine the first visible line
    // current_line is the index of the last line shown on screen.
    uint16_t first = 0;
    if (self->current_line >= self->lines_per_screen)
        first = (uint16_t)(self->current_line + 1 - self->lines_per_screen);

    uint16_t last = first + self->lines_per_screen;
    if (last > self->total_lines)
        last = self->total_lines;

    // Text drawing width (leave room for scrollbar)
    uint16_t text_x = 1;

    // Render each visible line
    char *line_buf = (char *)m_malloc(256); // temporary buffer for one line (max 255 chars + null terminator)
    for (uint16_t i = first; i < last; i++)
    {
        uint32_t s = self->lines[i].start;
        uint16_t l = self->lines[i].length;

        if (s + l > (uint32_t)self->text_len)
            break;

        // Copy into stack buffer (null-terminate, rstrip trailing space)
        uint16_t copy_len = l < 255 ? l : 255;
        memcpy(line_buf, self->text + s, copy_len);
        // rstrip
        while (copy_len > 0 && line_buf[copy_len - 1] == ' ')
            copy_len--;
        line_buf[copy_len] = '\0';

        uint16_t y = (uint16_t)(self->pos_y + 5 + (uint32_t)(i - first) * self->spacing);
        LCD_MP_TEXT(text_x, y, line_buf, self->foreground_color, FONT_DEFAULT);
    }

    if (self->show_scrollbar)
        textbox_draw_scrollbar(self);

    textbox_draw_cursor(self, first, last);

    LCD_MP_SWAP();
    m_free(line_buf);
}

void textbox_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "TextBox(lines=%u, current=%u)", self->total_lines, self->current_line);
}

// Constructor: TextBox(y, height, display_width, chars_per_line, spacing, fg_color, bg_color, show_scrollbar)
mp_obj_t textbox_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    if (n_args != 9)
    {
        mp_raise_TypeError(MP_ERROR_TEXT(
            "TextBox requires 9 args: y, height, display_width, chars_per_line, spacing, fg_color, bg_color, show_scrollbar, show_cursor"));
    }

    textbox_mp_obj_t *self = mp_obj_malloc_with_finaliser(textbox_mp_obj_t, &textbox_mp_type);
    self->base.type = &textbox_mp_type;

    self->pos_y = (uint16_t)mp_obj_get_int(args[0]);
    self->box_height = (uint16_t)mp_obj_get_int(args[1]);
    self->box_width = (uint16_t)mp_obj_get_int(args[2]);
    self->chars_per_line = (uint16_t)mp_obj_get_int(args[3]);
    self->spacing = (uint16_t)mp_obj_get_int(args[4]);
    self->foreground_color = (uint16_t)mp_obj_get_int(args[5]);
    self->background_color = (uint16_t)mp_obj_get_int(args[6]);
    self->show_scrollbar = mp_obj_is_true(args[7]);
    self->show_cursor = mp_obj_is_true(args[8]);
    // Reserve the 5-px top offset so the cursor underline (text_y + spacing - 2)
    // for the last visible row always lands inside the box.
    self->lines_per_screen = (self->spacing > 0 && self->box_height > 5)
                                 ? (uint16_t)((self->box_height - 5) / self->spacing)
                                 : 1;

    // Edit buffer: single allocation for all insert/delete operations.
    self->edit_buf = m_new(char, TEXTBOX_INITIAL_EDIT_CAPACITY);
    self->edit_buf_capacity = TEXTBOX_INITIAL_EDIT_CAPACITY;
    self->edit_buf[0] = '\0';
    self->text = self->edit_buf;
    self->text_len = 0;

    // Line cache
    self->lines = m_new(textbox_line_t, TEXTBOX_INITIAL_LINE_CAPACITY);
    self->line_capacity = TEXTBOX_INITIAL_LINE_CAPACITY;
    self->total_lines = 0;
    self->current_line = 0;
    self->cache_valid = false;
    self->freed = false;

    // Clear display region
    LCD_MP_FILL_RECTANGLE(0, self->pos_y, self->box_width, self->box_height, self->background_color);
    LCD_MP_SWAP();

    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t textbox_mp_del(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;

    if (self->lines)
    {
        m_del(textbox_line_t, self->lines, self->line_capacity);
        self->lines = NULL;
    }
    if (self->edit_buf)
    {
        m_del(char, self->edit_buf, self->edit_buf_capacity);
        self->edit_buf = NULL;
        self->edit_buf_capacity = 0;
    }
    self->text = NULL;
    self->text_len = 0;
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_del_obj, textbox_mp_del);

mp_obj_t textbox_mp_render(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;

    if (!self->cache_valid)
        textbox_wrap(self);

    if (self->total_lines > 0)
        self->current_line = (uint16_t)(self->total_lines - 1);
    self->cursor_pos = self->text_len;

    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_render_obj, textbox_mp_render);

mp_obj_t textbox_mp_scroll_up(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed || self->current_line == 0)
        return mp_const_none;
    self->current_line--;
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_scroll_up_obj, textbox_mp_scroll_up);

mp_obj_t textbox_mp_scroll_down(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed || self->total_lines == 0 || self->current_line >= self->total_lines - 1)
        return mp_const_none;
    self->current_line++;
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_scroll_down_obj, textbox_mp_scroll_down);

mp_obj_t textbox_mp_clear(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;

    self->edit_buf[0] = '\0';
    self->text = self->edit_buf;
    self->text_len = 0;
    self->total_lines = 0;
    self->current_line = 0;
    self->cache_valid = false;

    LCD_MP_FILL_RECTANGLE(0, self->pos_y, self->box_width, self->box_height, self->background_color);
    LCD_MP_SWAP();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_clear_obj, textbox_mp_clear);

mp_obj_t textbox_mp_set_text(mp_obj_t self_in, mp_obj_t text_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;

    size_t new_len;
    const char *new_text = mp_obj_str_get_data(text_in, &new_len);

    // No-op if text unchanged
    if (new_len == self->text_len && memcmp(new_text, self->text, new_len) == 0)
        return mp_const_none;

    // Copy into the mutable edit buffer; grow only when more space is needed.
    if (new_len + 1 > self->edit_buf_capacity)
    {
        size_t new_cap = new_len + 1 + 64;
        self->edit_buf = m_renew(char, self->edit_buf, self->edit_buf_capacity, new_cap);
        self->edit_buf_capacity = new_cap;
    }
    memcpy(self->edit_buf, new_text, new_len);
    self->edit_buf[new_len] = '\0';
    self->text = self->edit_buf;
    self->text_len = new_len;
    self->cache_valid = false;

    // re-wrap + display
    textbox_wrap(self);
    if (self->total_lines > 0)
        self->current_line = (uint16_t)(self->total_lines - 1);
    self->cursor_pos = self->text_len;
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(textbox_mp_set_text_obj, textbox_mp_set_text);

mp_obj_t textbox_mp_set_current_line(mp_obj_t self_in, mp_obj_t line_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed || self->total_lines == 0)
        return mp_const_none;

    int line = mp_obj_get_int(line_in);
    if (line < 0 || line >= (int)self->total_lines)
        return mp_const_none;

    self->current_line = (uint16_t)line;
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(textbox_mp_set_current_line_obj, textbox_mp_set_current_line);

// Returns the wrapped-line index that contains cursor_pos.
static uint16_t textbox_cursor_line(textbox_mp_obj_t *self)
{
    if (self->total_lines == 0)
        return 0;
    uint16_t cl = self->total_lines - 1;
    for (uint16_t i = 0; i < self->total_lines; i++)
    {
        uint32_t ls = self->lines[i].start;
        uint16_t ll = self->lines[i].length;
        // Treat empty lines as length 1 so cursor_pos==ls still matches.
        uint16_t eff_len = ll > 0 ? ll : 1;
        // Also match when cursor sits on the '\n' that terminates this line
        // (the newline is NOT included in ll, leaving a one-byte gap otherwise).
        bool at_newline = (self->cursor_pos == (size_t)(ls + ll)) &&
                          (ls + ll < self->text_len) &&
                          (self->edit_buf[ls + ll] == '\n');
        if (self->cursor_pos >= ls &&
            (self->cursor_pos < ls + eff_len || i == self->total_lines - 1 || at_newline))
        {
            cl = i;
            break;
        }
    }
    return cl;
}

// Adjusts current_line so the cursor's wrapped line is inside the visible window.
static void textbox_scroll_to_cursor(textbox_mp_obj_t *self)
{
    if (self->total_lines == 0)
        return;
    uint16_t cl = textbox_cursor_line(self);
    uint16_t first = (self->current_line >= self->lines_per_screen)
                         ? (uint16_t)(self->current_line + 1 - self->lines_per_screen)
                         : 0;
    uint16_t last = first + self->lines_per_screen;
    if (last > self->total_lines)
        last = self->total_lines;
    if (cl < first)
    {
        // Cursor is above the viewport – make it the first visible line.
        uint16_t new_cl = (uint16_t)(cl + self->lines_per_screen - 1);
        self->current_line = (new_cl < self->total_lines) ? new_cl : (uint16_t)(self->total_lines - 1);
    }
    else if (cl >= last)
    {
        // Cursor is below the viewport – make it the last visible line.
        self->current_line = (cl < self->total_lines) ? cl : (uint16_t)(self->total_lines - 1);
    }
}

mp_obj_t textbox_mp_set_cursor(mp_obj_t self_in, mp_obj_t pos_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;
    if (!self->cache_valid)
        textbox_wrap(self);
    size_t pos = (size_t)mp_obj_get_int(pos_in);
    if (pos <= self->text_len)
        self->cursor_pos = pos;
    textbox_scroll_to_cursor(self);
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(textbox_mp_set_cursor_obj, textbox_mp_set_cursor);

mp_obj_t textbox_mp_cursor_up(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;
    if (!self->cache_valid)
        textbox_wrap(self);
    if (self->total_lines == 0)
        return mp_const_none;
    uint16_t cl = textbox_cursor_line(self);
    if (cl == 0)
        return mp_const_none; // already on first line
    uint16_t col = (uint16_t)(self->cursor_pos - self->lines[cl].start);
    uint16_t prev_len = self->lines[cl - 1].length;
    if (col > prev_len)
        col = prev_len;
    self->cursor_pos = self->lines[cl - 1].start + col;
    textbox_scroll_to_cursor(self);
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_cursor_up_obj, textbox_mp_cursor_up);

mp_obj_t textbox_mp_cursor_down(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;
    if (!self->cache_valid)
        textbox_wrap(self);
    if (self->total_lines == 0)
        return mp_const_none;
    uint16_t cl = textbox_cursor_line(self);
    if (cl >= self->total_lines - 1)
        return mp_const_none; // already on last line
    uint16_t col = (uint16_t)(self->cursor_pos - self->lines[cl].start);
    uint16_t next_len = self->lines[cl + 1].length;
    if (col > next_len)
        col = next_len;
    self->cursor_pos = self->lines[cl + 1].start + col;
    textbox_scroll_to_cursor(self);
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_cursor_down_obj, textbox_mp_cursor_down);

// Insert a string (char_in) at the current cursor position and advance the cursor.
mp_obj_t textbox_mp_insert_char(mp_obj_t self_in, mp_obj_t char_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;
    size_t char_len;
    const char *ch = mp_obj_str_get_data(char_in, &char_len);
    if (char_len == 0)
        return mp_const_none;
    if (!self->cache_valid)
        textbox_wrap(self);

    size_t new_len = self->text_len + char_len;

    // Grow only when text would exceed capacity (amortised with headroom).
    if (new_len + 1 > self->edit_buf_capacity)
    {
        size_t new_cap = new_len + 64;
        self->edit_buf = m_renew(char, self->edit_buf, self->edit_buf_capacity, new_cap);
        self->edit_buf_capacity = new_cap;
        self->text = self->edit_buf; // pointer may move on realloc
    }

    // Shift every byte after cursor_pos right by char_len to open a gap.
    size_t i = self->text_len;
    while (i > self->cursor_pos)
    {
        self->edit_buf[i + char_len - 1] = self->edit_buf[i - 1];
        i--;
    }

    // Write the new character(s) directly into the gap.
    size_t j = 0;
    while (j < char_len)
    {
        self->edit_buf[self->cursor_pos + j] = ch[j];
        j++;
    }

    self->text_len = new_len;
    self->edit_buf[new_len] = '\0';
    self->cursor_pos += char_len;
    self->cache_valid = false;

    textbox_wrap(self);
    textbox_scroll_to_cursor(self);
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(textbox_mp_insert_char_obj, textbox_mp_insert_char);

// Delete the character immediately before the cursor (backspace) and move cursor back.
mp_obj_t textbox_mp_delete_char(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed || self->cursor_pos == 0)
        return mp_const_none;
    if (!self->cache_valid)
        textbox_wrap(self);

    // Shift every byte from cursor_pos onward one slot left,
    // overwriting the byte at cursor_pos - 1 (the deleted character).
    size_t i = self->cursor_pos;
    while (i < self->text_len)
    {
        self->edit_buf[i - 1] = self->edit_buf[i];
        i++;
    }
    self->text_len--;
    self->edit_buf[self->text_len] = '\0';
    self->cursor_pos--;
    self->cache_valid = false;

    textbox_wrap(self);
    textbox_scroll_to_cursor(self);
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_delete_char_obj, textbox_mp_delete_char);

void textbox_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attribute
        switch (attribute)
        {
        case MP_QSTR_text:
            destination[0] = mp_obj_new_str(self->edit_buf, self->text_len);
            break;
        case MP_QSTR_total_lines:
            destination[0] = mp_obj_new_int(self->total_lines);
            break;
        case MP_QSTR_current_line:
            destination[0] = mp_obj_new_int(self->current_line);
            break;
        case MP_QSTR_foreground_color:
            destination[0] = mp_obj_new_int(self->foreground_color);
            break;
        case MP_QSTR_background_color:
            destination[0] = mp_obj_new_int(self->background_color);
            break;
        case MP_QSTR_show_scrollbar:
            destination[0] = mp_obj_new_bool(self->show_scrollbar);
            break;
        case MP_QSTR_show_cursor:
            destination[0] = mp_obj_new_bool(self->show_cursor);
            break;
        case MP_QSTR_lines_per_screen:
            destination[0] = mp_obj_new_int(self->lines_per_screen);
            break;
        case MP_QSTR_cursor:
            destination[0] = mp_obj_new_int(self->cursor_pos);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&textbox_mp_del_obj);
            break;
        default:
            return; // Fail
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attribute
        switch (attribute)
        {
        case MP_QSTR_foreground_color:
            self->foreground_color = (uint16_t)mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_background_color:
            self->background_color = (uint16_t)mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_show_cursor:
            self->show_cursor = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
            break;
        case MP_QSTR_cursor:
        {
            textbox_mp_set_cursor(self_in, destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        break;
        case MP_QSTR_show_scrollbar:
        {
            self->show_scrollbar = mp_obj_is_true(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        break;
        default:
            return; // Fail
        };
    }
}

static const mp_rom_map_elem_t textbox_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_render), MP_ROM_PTR(&textbox_mp_render_obj)},
    {MP_ROM_QSTR(MP_QSTR__scroll_up), MP_ROM_PTR(&textbox_mp_scroll_up_obj)},
    {MP_ROM_QSTR(MP_QSTR__scroll_down), MP_ROM_PTR(&textbox_mp_scroll_down_obj)},
    {MP_ROM_QSTR(MP_QSTR__clear), MP_ROM_PTR(&textbox_mp_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR__set_text), MP_ROM_PTR(&textbox_mp_set_text_obj)},
    {MP_ROM_QSTR(MP_QSTR__set_current_line), MP_ROM_PTR(&textbox_mp_set_current_line_obj)},
    {MP_ROM_QSTR(MP_QSTR__set_cursor), MP_ROM_PTR(&textbox_mp_set_cursor_obj)},
    {MP_ROM_QSTR(MP_QSTR__cursor_up), MP_ROM_PTR(&textbox_mp_cursor_up_obj)},
    {MP_ROM_QSTR(MP_QSTR__cursor_down), MP_ROM_PTR(&textbox_mp_cursor_down_obj)},
    {MP_ROM_QSTR(MP_QSTR__insert_char), MP_ROM_PTR(&textbox_mp_insert_char_obj)},
    {MP_ROM_QSTR(MP_QSTR__delete_char), MP_ROM_PTR(&textbox_mp_delete_char_obj)},
};
static MP_DEFINE_CONST_DICT(textbox_mp_locals_dict, textbox_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    textbox_mp_type,
    MP_QSTR_TextBox,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, textbox_mp_print,
    make_new, textbox_mp_make_new,
    attr, textbox_mp_attr,
    locals_dict, &textbox_mp_locals_dict);

static const mp_rom_map_elem_t textbox_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_textbox)},
    {MP_ROM_QSTR(MP_QSTR_TextBox), MP_ROM_PTR(&textbox_mp_type)},
};
static MP_DEFINE_CONST_DICT(textbox_mp_globals, textbox_mp_globals_table);

const mp_obj_module_t textbox_mp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&textbox_mp_globals,
};
MP_REGISTER_MODULE(MP_QSTR_textbox, textbox_mp_module);