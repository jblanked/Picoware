#include "textbox_mp.h"
#include "../lcd/lcd_config.h"
#include "../vector/vector_mp.h"

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
            line_start = i;
            line_length = 0;
            continue;
        }

        if (line_length == 0)
        {
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

    // Commit the last line
    if (line_length > 0 || self->total_lines == 0 ||
        (str_len > 0 && text[str_len - 1] == '\n'))
        textbox_add_line(self, line_start, line_length);

    self->cache_valid = true;
}

// Helper to find the wrapped line index of the current cursor position
static uint16_t textbox_get_cursor_line(textbox_mp_obj_t *self)
{
    if (self->total_lines == 0) return 0;
    
    for (uint16_t i = 0; i < self->total_lines - 1; i++) {
        // A line logically owns all bytes from its start up to the next line's start.
        if (self->cursor_pos >= self->lines[i].start && self->cursor_pos < self->lines[i+1].start) {
            return i;
        }
    }
    
    // If it hasn't matched any previous line, it must belong to the last line.
    return self->total_lines - 1;
}

// Draw the cursor as a static horizontal underline at the current cursor_pos.
static void textbox_draw_cursor(textbox_mp_obj_t *self, uint16_t first, uint16_t last)
{
    if (!self->show_cursor || self->total_lines == 0)
        return;

    uint16_t cursor_line = textbox_get_cursor_line(self);

    // Only draw if the cursor's line is currently on screen.
    if (cursor_line < first || cursor_line >= last)
        return;

    uint32_t ls = self->lines[cursor_line].start;
    uint16_t ll = self->lines[cursor_line].length;
    
    uint16_t cursor_col = (uint16_t)(self->cursor_pos - ls);
    if (cursor_col > ll)
        cursor_col = ll; // clamp to end of line

    // Lock the cursor to the physical 6-pixel font width to prevent drift
    uint16_t char_w = 6; 
    
    uint16_t cx = (uint16_t)(1 + cursor_col * char_w);
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
    if (self->total_lines > self->lines_per_screen && self->current_line > 0)
    {
        uint32_t scrollable = track_h - bar_h;
        uint32_t ratio_num = self->current_line;
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

    // --- AUTO-SCROLL LOGIC ---
    if (self->show_cursor) 
    {
        uint16_t cursor_line = textbox_get_cursor_line(self);
        
        if (cursor_line < self->current_line) {
            // Cursor moved above screen, snap view up
            self->current_line = cursor_line;
        } else if (cursor_line >= self->current_line + self->lines_per_screen) {
            // Cursor moved below screen, snap view down
            self->current_line = cursor_line - self->lines_per_screen + 1;
        }
    }

    // Determine the first visible line
    uint16_t first = self->current_line;
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
        LCD_MP_TEXT(text_x, y, line_buf, self->foreground_color, 0);
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
    self->lines_per_screen = (self->spacing > 0)
                                 ? (uint16_t)(self->box_height / self->spacing)
                                 : 1;

    // Empty text
    self->text_obj = mp_obj_new_str("", 0);
    self->text = "";
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
    self->text = NULL;
    self->text_obj = mp_const_none;
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

    // Safeguard: Clamp cursor to valid memory bounds
    if (self->cursor_pos > self->text_len) {
        self->cursor_pos = self->text_len;
    }

    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_render_obj, textbox_mp_render);

mp_obj_t textbox_mp_scroll_up(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed) return mp_const_none;

    if (self->show_cursor && self->total_lines > 0) {
        // Editor Mode: Move cursor up one logical line
        uint16_t line = textbox_get_cursor_line(self);
        if (line > 0) {
            uint16_t col = (uint16_t)(self->cursor_pos - self->lines[line].start);
            uint16_t prev_len = self->lines[line - 1].length;
            
            if (prev_len > 0 && self->text[self->lines[line - 1].start + prev_len - 1] == '\n') {
                prev_len -= 1;
            }
            
            uint16_t target_col = (col > prev_len) ? prev_len : col;
            self->cursor_pos = self->lines[line - 1].start + target_col;
        }
    } else {
        // Viewer Mode: Just scroll the screen
        if (self->current_line > 0) self->current_line--;
    }
    
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_scroll_up_obj, textbox_mp_scroll_up);

mp_obj_t textbox_mp_scroll_down(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed || self->total_lines == 0) return mp_const_none;

    if (self->show_cursor) {
        // Editor Mode: Move cursor down one logical line
        uint16_t line = textbox_get_cursor_line(self);
        if (line < self->total_lines - 1) {
            uint16_t col = (uint16_t)(self->cursor_pos - self->lines[line].start);
            uint16_t next_len = self->lines[line + 1].length;
            
            if (next_len > 0 && self->text[self->lines[line + 1].start + next_len - 1] == '\n') {
                next_len -= 1;
            }

            uint16_t target_col = (col > next_len) ? next_len : col;
            self->cursor_pos = self->lines[line + 1].start + target_col;
        }
    } else {
        // Viewer Mode: Just scroll the screen
        if (self->current_line + self->lines_per_screen < self->total_lines) {
            self->current_line++;
        }
    }
    
    textbox_display(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_scroll_down_obj, textbox_mp_scroll_down);

mp_obj_t textbox_mp_clear(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
        return mp_const_none;

    self->text_obj = mp_obj_new_str("", 0);
    self->text = "";
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

    if (new_len == self->text_len && memcmp(new_text, self->text, new_len) == 0)
        return mp_const_none;

    self->text_obj = text_in; 
    self->text = new_text;
    self->text_len = new_len;
    self->cache_valid = false;

    textbox_wrap(self);
    
    // STRICT BOUNDS ONLY: No auto-shifting. Let Python or scroll functions handle movement.
    if (self->cursor_pos > self->text_len) {
        self->cursor_pos = self->text_len;
    }

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


mp_obj_t textbox_mp_set_cursor(mp_obj_t self_in, mp_obj_t pos_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed) return mp_const_none;
    
    size_t pos = (size_t)mp_obj_get_int(pos_in);
    if (pos <= self->text_len) {
        self->cursor_pos = pos;
    } else {
        self->cursor_pos = self->text_len;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(textbox_mp_set_cursor_obj, textbox_mp_set_cursor);

mp_obj_t textbox_mp_get_cursor(mp_obj_t self_in)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed) return mp_obj_new_int(0);
    return mp_obj_new_int((mp_int_t)self->cursor_pos);
}
static MP_DEFINE_CONST_FUN_OBJ_1(textbox_mp_get_cursor_obj, textbox_mp_get_cursor);


void textbox_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    textbox_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attribute
        if (attribute == MP_QSTR_text)
            destination[0] = self->text_obj;
        else if (attribute == MP_QSTR_total_lines)
            destination[0] = mp_obj_new_int(self->total_lines);
        else if (attribute == MP_QSTR_current_line)
            destination[0] = mp_obj_new_int(self->current_line);
        else if (attribute == MP_QSTR_foreground_color)
            destination[0] = mp_obj_new_int(self->foreground_color);
        else if (attribute == MP_QSTR_background_color)
            destination[0] = mp_obj_new_int(self->background_color);
        else if (attribute == MP_QSTR_show_scrollbar)
            destination[0] = mp_obj_new_bool(self->show_scrollbar);
        else if (attribute == MP_QSTR_show_cursor)
            destination[0] = mp_obj_new_bool(self->show_cursor);
        else if (attribute == MP_QSTR_lines_per_screen)
            destination[0] = mp_obj_new_int(self->lines_per_screen);
        else if (attribute == MP_QSTR_cursor)
            destination[0] = mp_obj_new_int((mp_int_t)self->cursor_pos);
        else if (attribute == MP_QSTR___del__)
            destination[0] = MP_OBJ_FROM_PTR(&textbox_mp_del_obj);
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attribute
        if (attribute == MP_QSTR_foreground_color)
        {
            self->foreground_color = (uint16_t)mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_background_color)
        {
            self->background_color = (uint16_t)mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_show_cursor)
        {
            self->show_cursor = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_cursor)
        {
            size_t pos = (size_t)mp_obj_get_int(destination[1]);
            if (pos <= self->text_len)
                self->cursor_pos = pos;
            destination[0] = MP_OBJ_NULL;
        }
        else if (attribute == MP_QSTR_show_scrollbar)
        {
            self->show_scrollbar = mp_obj_get_int(destination[1]);
            destination[0] = MP_OBJ_NULL;
        }
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
    {MP_ROM_QSTR(MP_QSTR__get_cursor), MP_ROM_PTR(&textbox_mp_get_cursor_obj)},
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