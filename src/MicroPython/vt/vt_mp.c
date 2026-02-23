#include "vt_mp.h"
#include <string.h>

#if defined(PICOCALC)
#include "../../lcd/lcd_config.h"
#else
#include "../../../lcd/lcd_config.h"
#endif

#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif

#define VT_MAX_SYNTAX_ENTRIES 48      // max keyword→color entries
#define VT_MAX_TOKENS 64              // max tokens per line (53-char terminal width)
#define VT_TEXT_BUF_SIZE LCD_MP_WIDTH // text accumulation buffer for drawing
#define VT_LINE_BUF_SIZE LCD_MP_WIDTH // max raw line length (matches screen width)

typedef struct
{
    const char *keyword;
    size_t keyword_len;
    uint16_t color;
} vt_syntax_entry_t;

#define TOKEN_NORMAL 0
#define TOKEN_STRING 1

typedef struct
{
    uint16_t start;
    uint16_t end;
    uint8_t type;
} vt_token_t;

static const char *DELIMITERS = " \t\n+-*/=<>()[]{}:,;\"'#";

static inline bool is_delimiter(char c)
{
    const char *d = DELIMITERS;
    while (*d)
    {
        if (c == *d)
            return true;
        d++;
    }
    return false;
}

static bool is_compound_delimiter(const char *text, size_t pos, size_t len)
{
    if (pos + 1 >= len)
        return false;
    char a = text[pos], b = text[pos + 1];
    return (a == '=' && b == '=') || (a == '!' && b == '=') ||
           (a == '<' && b == '=') || (a == '>' && b == '=') ||
           (a == '-' && b == '>') || (a == '+' && b == '=') ||
           (a == '-' && b == '=') || (a == '*' && b == '=') ||
           (a == '/' && b == '=');
}

static size_t vt_strip_comment(const char *text, size_t text_len)
{
    bool in_str = false;
    bool esc = false;
    char quote = 0;

    for (size_t i = 0; i < text_len; i++)
    {
        char ch = text[i];
        if (esc)
        {
            esc = false;
            continue;
        }
        if (ch == '\\')
        {
            esc = true;
            continue;
        }
        if (ch == '\'' || ch == '"')
        {
            if (!in_str)
            {
                in_str = true;
                quote = ch;
            }
            else if (ch == quote)
            {
                in_str = false;
            }
        }
        else if (ch == '#' && !in_str)
        {
            return i;
        }
    }
    return text_len;
}

static size_t vt_tokenize(const char *text, size_t text_len, vt_token_t *tokens, size_t max_tokens)
{
    size_t i = 0;
    size_t token_idx = 0;
    bool in_str = false;
    char str_char = 0;
    size_t start_pos = 0;

    while (i < text_len && token_idx < max_tokens)
    {
        char ch = text[i];

        if (in_str)
        {
            if (ch == str_char && (i == 0 || text[i - 1] != '\\'))
            {
                in_str = false;
                tokens[token_idx].start = (uint16_t)start_pos;
                tokens[token_idx].end = (uint16_t)(i + 1);
                tokens[token_idx].type = TOKEN_STRING;
                token_idx++;
                start_pos = i + 1;
            }
            i++;
            continue;
        }

        if (ch == '"' || ch == '\'')
        {
            if (start_pos < i)
            {
                tokens[token_idx].start = (uint16_t)start_pos;
                tokens[token_idx].end = (uint16_t)i;
                tokens[token_idx].type = TOKEN_NORMAL;
                token_idx++;
            }
            in_str = true;
            str_char = ch;
            start_pos = i;
            i++;
            continue;
        }

        if (is_compound_delimiter(text, i, text_len))
        {
            if (start_pos < i)
            {
                tokens[token_idx].start = (uint16_t)start_pos;
                tokens[token_idx].end = (uint16_t)i;
                tokens[token_idx].type = TOKEN_NORMAL;
                token_idx++;
            }
            if (token_idx < max_tokens)
            {
                tokens[token_idx].start = (uint16_t)i;
                tokens[token_idx].end = (uint16_t)(i + 2);
                tokens[token_idx].type = TOKEN_NORMAL;
                token_idx++;
            }
            start_pos = i + 2;
            i += 2;
            continue;
        }

        if (is_delimiter(ch))
        {
            if (start_pos < i)
            {
                tokens[token_idx].start = (uint16_t)start_pos;
                tokens[token_idx].end = (uint16_t)i;
                tokens[token_idx].type = TOKEN_NORMAL;
                token_idx++;
            }
            if (token_idx < max_tokens)
            {
                tokens[token_idx].start = (uint16_t)i;
                tokens[token_idx].end = (uint16_t)(i + 1);
                tokens[token_idx].type = TOKEN_NORMAL;
                token_idx++;
            }
            start_pos = i + 1;
        }
        i++;
    }

    // Remaining text
    if (start_pos < text_len && token_idx < max_tokens)
    {
        tokens[token_idx].start = (uint16_t)start_pos;
        tokens[token_idx].end = (uint16_t)text_len;
        tokens[token_idx].type = TOKEN_NORMAL;
        token_idx++;
    }

    return token_idx;
}

static uint16_t vt_lookup_keyword_color(
    const char *token, size_t token_len,
    const vt_syntax_entry_t *syntax_map, size_t syntax_count,
    uint16_t default_color)
{
    for (size_t i = 0; i < syntax_count; i++)
    {
        if (syntax_map[i].keyword_len == token_len &&
            memcmp(token, syntax_map[i].keyword, token_len) == 0)
        {
            return syntax_map[i].color;
        }
    }
    return default_color;
}

static void vt_highlight_and_render_line(
    const char *raw_line, size_t raw_len,
    uint16_t y_pos, uint16_t fg_color,
    uint16_t string_color, uint16_t comment_color,
    const vt_syntax_entry_t *syntax_map, size_t syntax_count,
    uint8_t char_width, uint8_t font_size,
    vt_token_t *tokens, char *buf)
{
    // Strip comment
    size_t code_len = vt_strip_comment(raw_line, raw_len);
    bool has_comment = (code_len < raw_len);

    // Tokenize code part
    size_t token_count = vt_tokenize(raw_line, code_len, tokens, VT_MAX_TOKENS);

    // Draw each token
    uint16_t x_offset = 0;

    for (size_t i = 0; i < token_count; i++)
    {
        uint16_t start = tokens[i].start;
        uint16_t end = tokens[i].end;
        size_t tok_len = end - start;
        if (tok_len == 0)
            continue;

        // Copy token text
        size_t copy_len = (tok_len < VT_TEXT_BUF_SIZE - 1) ? tok_len : (VT_TEXT_BUF_SIZE - 1);
        memcpy(buf, raw_line + start, copy_len);
        buf[copy_len] = '\0';

        uint16_t color;
        if (tokens[i].type == TOKEN_STRING)
        {
            color = string_color;
        }
        else
        {
            color = vt_lookup_keyword_color(
                raw_line + start, tok_len,
                syntax_map, syntax_count, fg_color);
        }

        LCD_MP_TEXT(x_offset, y_pos, buf, color, font_size);
        x_offset += (uint16_t)(copy_len * char_width);
    }

    // Draw comment part if present
    if (has_comment)
    {
        size_t comment_len = raw_len - code_len;
        size_t copy_len = (comment_len < VT_TEXT_BUF_SIZE - 1) ? comment_len : (VT_TEXT_BUF_SIZE - 1);
        memcpy(buf, raw_line + code_len, copy_len);
        buf[copy_len] = '\0';
        LCD_MP_TEXT(x_offset, y_pos, buf, comment_color, font_size);
    }
}

mp_obj_t vt_mp_render(size_t n_args, const mp_obj_t *args)
{
    // args[0]  = terminal_buffer: list of lists of single-char strings
    // args[1]  = screen_height (int)
    // args[2]  = screen_width (int)
    // args[3]  = char_height (int, pixels)
    // args[4]  = char_width (int, pixels)
    // args[5]  = background_color (uint16_t)
    // args[6]  = foreground_color (uint16_t)
    // args[7]  = cursor_visible (bool)
    // args[8]  = cursor_x (pixel)
    // args[9]  = cursor_y (pixel)
    // args[10] = cursor_w (pixel)
    // args[11] = cursor_h (pixel)
    // args[12] = cursor_color (uint16_t)
    // args[13] = syntax_map list [(keyword_str, tft_color_int), ...]
    // args[14] = string_color (uint16_t)
    // args[15] = comment_color (uint16_t)
    // args[16] = font_size (uint8_t, optional)
    if (n_args < 16)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("render requires at least 16 arguments"));
    }

    mp_obj_t terminal_buffer = args[0];
    int screen_height = mp_obj_get_int(args[1]);
    int screen_width = mp_obj_get_int(args[2]);
    uint8_t char_height = (uint8_t)mp_obj_get_int(args[3]);
    uint8_t char_width = (uint8_t)mp_obj_get_int(args[4]);
    uint16_t bg_color = (uint16_t)mp_obj_get_int(args[5]);
    uint16_t fg_color = (uint16_t)mp_obj_get_int(args[6]);
    bool cursor_visible = mp_obj_is_true(args[7]);
    uint16_t cursor_x = (uint16_t)mp_obj_get_int(args[8]);
    uint16_t cursor_y = (uint16_t)mp_obj_get_int(args[9]);
    uint16_t cursor_w = (uint16_t)mp_obj_get_int(args[10]);
    uint16_t cursor_h = (uint16_t)mp_obj_get_int(args[11]);
    uint16_t cursor_color = (uint16_t)mp_obj_get_int(args[12]);
    mp_obj_t syntax_map_list = args[13];
    uint16_t string_color = (uint16_t)mp_obj_get_int(args[14]);
    uint16_t comment_color = (uint16_t)mp_obj_get_int(args[15]);
    uint8_t font_size = FONT_DEFAULT;
    if (n_args >= 17)
    {
        font_size = (uint8_t)mp_obj_get_int(args[16]);
    }

    // Build syntax map from Python list of (keyword, tft_color) tuples
    size_t map_count = 0;
    mp_obj_t *map_items = NULL;
    mp_obj_get_array(syntax_map_list, &map_count, &map_items);

    // Allocate working buffers on the MicroPython heap
    vt_syntax_entry_t *syntax_map = (vt_syntax_entry_t *)m_malloc(VT_MAX_SYNTAX_ENTRIES * sizeof(vt_syntax_entry_t));
    size_t actual_map_count = (map_count < VT_MAX_SYNTAX_ENTRIES) ? map_count : VT_MAX_SYNTAX_ENTRIES;

    for (size_t i = 0; i < actual_map_count; i++)
    {
        size_t tuple_len = 0;
        mp_obj_t *tuple_items = NULL;
        mp_obj_get_array(map_items[i], &tuple_len, &tuple_items);
        if (tuple_len >= 2)
        {
            size_t str_len = 0;
            syntax_map[i].keyword = mp_obj_str_get_data(tuple_items[0], &str_len);
            syntax_map[i].keyword_len = str_len;
            syntax_map[i].color = (uint16_t)mp_obj_get_int(tuple_items[1]);
        }
    }

    // Clear the screen
    LCD_MP_CLEAR(bg_color);

    // Get the terminal buffer (list of lists)
    size_t buf_rows = 0;
    mp_obj_t *buf_row_items = NULL;
    mp_obj_get_array(terminal_buffer, &buf_rows, &buf_row_items);

    char *line_buf = (char *)m_malloc(VT_LINE_BUF_SIZE);
    vt_token_t *tokens = (vt_token_t *)m_malloc(VT_MAX_TOKENS * sizeof(vt_token_t));
    char *tok_buf = (char *)m_malloc(VT_TEXT_BUF_SIZE);

    size_t rows_to_process = (buf_rows < (size_t)screen_height) ? buf_rows : (size_t)screen_height;

    for (size_t y = 0; y < rows_to_process; y++)
    {
        // Get this row (list of single-char strings)
        size_t row_len = 0;
        mp_obj_t *row_items = NULL;
        mp_obj_get_array(buf_row_items[y], &row_len, &row_items);

        // Build the raw line string, rstrip spaces
        size_t cols = (row_len < (size_t)screen_width) ? row_len : (size_t)screen_width;
        if (cols > VT_LINE_BUF_SIZE - 1)
            cols = VT_LINE_BUF_SIZE - 1;

        for (size_t x = 0; x < cols; x++)
        {
            const char *ch = mp_obj_str_get_str(row_items[x]);
            line_buf[x] = ch[0];
        }

        // rstrip spaces
        size_t line_len = cols;
        while (line_len > 0 && line_buf[line_len - 1] == ' ')
        {
            line_len--;
        }

        if (line_len == 0)
            continue;

        line_buf[line_len] = '\0';

        uint16_t y_pos = (uint16_t)(y * char_height);
        vt_highlight_and_render_line(
            line_buf, line_len,
            y_pos, fg_color,
            string_color, comment_color,
            syntax_map, actual_map_count,
            char_width, font_size,
            tokens, tok_buf);
    }

    // Draw cursor if visible
    if (cursor_visible)
    {
        LCD_MP_FILL_RECTANGLE(cursor_x, cursor_y, cursor_w, cursor_h, cursor_color);
    }

    // Swap buffers
    LCD_MP_SWAP();

    // Free heap buffers
    m_free(tok_buf);
    m_free(tokens);
    m_free(line_buf);
    m_free(syntax_map);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(vt_mp_render_obj, 16, 17, vt_mp_render);

static const mp_rom_map_elem_t vt_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_vt)},
    {MP_ROM_QSTR(MP_QSTR_render), MP_ROM_PTR(&vt_mp_render_obj)},
};
static MP_DEFINE_CONST_DICT(vt_globals, vt_globals_table);

const mp_obj_module_t vt_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&vt_globals,
};

MP_REGISTER_MODULE(MP_QSTR_vt, vt_cmodule);
