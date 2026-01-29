/*
 * Picoware LVGL TextBox Header
 * Copyright © 2026 JBlanked
 */

#include "picoware_lvgl.h"

#define CHARACTERS_PER_LINE (DISPLAY_WIDTH / LVGL_FONT_WIDTH)
#define LINES_PER_SCREEN (DISPLAY_HEIGHT / LVGL_LINE_HEIGHT)

typedef struct
{
    mp_obj_base_t base;
    uint16_t foreground_color_565;
    uint16_t background_color_565;
    bool show_scrollbar;
    int16_t y;
    int16_t height;
    uint16_t characters_per_line;
    uint16_t lines_per_screen;
    uint16_t total_lines;
    int16_t current_line;
    lv_obj_t *textarea;
} picoware_lvgl_textbox_obj_t;

const mp_obj_type_t picoware_lvgl_textbox_type;

// TextBox constructor
STATIC mp_obj_t picoware_lvgl_textbox_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 5, false);

    picoware_lvgl_textbox_obj_t *self = mp_obj_malloc_with_finaliser(picoware_lvgl_textbox_obj_t, &picoware_lvgl_textbox_type);
    self->base.type = type;

    // Required: y position
    self->y = mp_obj_get_int(args[0]);

    // Required: height
    self->height = mp_obj_get_int(args[1]);

    // Optional: foreground_color (default: white 0xFFFF)
    if (n_args > 2)
    {
        self->foreground_color_565 = mp_obj_get_int(args[2]);
    }
    else
    {
        self->foreground_color_565 = 0xFFFF;
    }

    // Optional: background_color (default: black 0x0000)
    if (n_args > 3)
    {
        self->background_color_565 = mp_obj_get_int(args[3]);
    }
    else
    {
        self->background_color_565 = 0x0000;
    }

    // Optional: show_scrollbar (default: true)
    if (n_args > 4)
    {
        self->show_scrollbar = mp_obj_is_true(args[4]);
    }
    else
    {
        self->show_scrollbar = true;
    }

    // Initialize state
    self->characters_per_line = CHARACTERS_PER_LINE;
    self->lines_per_screen = LINES_PER_SCREEN;
    self->total_lines = 0;
    self->current_line = -1;

    // Initialize LVGL objects
    self->textarea = NULL;

    // Create LVGL objects immediately if display is available
    if (lvgl_display)
    {
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);

        // Create modern textarea with scrollbar
        self->textarea = lv_textarea_create(screen);

        // Set position and size
        lv_obj_set_pos(self->textarea, 0, self->y);
        lv_obj_set_size(self->textarea, lv_obj_get_width(screen), self->height);

        // Style the textarea
        lv_obj_set_style_bg_color(self->textarea, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
        lv_obj_set_style_text_color(self->textarea, lv_color_from_rgb565(self->foreground_color_565), LV_PART_MAIN);
        lv_obj_set_style_text_font(self->textarea, &lv_font_montserrat_12, LV_PART_MAIN);
        lv_obj_set_style_border_width(self->textarea, 0, LV_PART_MAIN);
        lv_obj_set_style_pad_all(self->textarea, 5, LV_PART_MAIN);

        // Configure scrollbar
        if (self->show_scrollbar)
        {
            lv_obj_set_scrollbar_mode(self->textarea, LV_SCROLLBAR_MODE_AUTO);
            lv_obj_set_style_bg_color(self->textarea, lv_color_from_rgb565(self->background_color_565), LV_PART_SCROLLBAR);
            lv_obj_set_style_bg_opa(self->textarea, LV_OPA_70, LV_PART_SCROLLBAR);
        }
        else
        {
            lv_obj_set_scrollbar_mode(self->textarea, LV_SCROLLBAR_MODE_OFF);
        }

        // Make textarea read-only
        lv_obj_clear_flag(self->textarea, LV_OBJ_FLAG_CLICKABLE);
    }

    return MP_OBJ_FROM_PTR(self);
}

// TextBox destructor
STATIC mp_obj_t picoware_lvgl_textbox_del(mp_obj_t self_in)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Clean up LVGL objects
    if (self->textarea && lvgl_display)
    {
        lv_obj_delete(self->textarea);
        self->textarea = NULL;
    }

    // Clear screen
    lv_clear_screen(true);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_textbox_del_obj, picoware_lvgl_textbox_del);

// TextBox.text property getter
STATIC mp_obj_t picoware_lvgl_textbox_get_text(mp_obj_t self_in)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->textarea)
    {
        const char *text = lv_textarea_get_text(self->textarea);
        return mp_obj_new_str(text, strlen(text));
    }
    return mp_obj_new_str("", 0);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_textbox_get_text_obj, picoware_lvgl_textbox_get_text);

// TextBox.text_height property getter
STATIC mp_obj_t picoware_lvgl_textbox_get_text_height(mp_obj_t self_in)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->total_lines == 0)
    {
        return mp_obj_new_int(0);
    }

    // Approximate height based on font size
    int height = (self->total_lines - 1) * LVGL_LINE_HEIGHT + 2;
    return mp_obj_new_int(height);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_textbox_get_text_height_obj, picoware_lvgl_textbox_get_text_height);

// TextBox.clear() - Clear the textbox
STATIC mp_obj_t picoware_lvgl_textbox_clear(mp_obj_t self_in)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Reset state
    self->current_line = -1;
    self->total_lines = 0;

    // Update textarea if it exists - set empty text
    if (self->textarea)
    {
        lv_textarea_set_text(self->textarea, "");
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_textbox_clear_obj, picoware_lvgl_textbox_clear);

// TextBox.refresh() - Refresh the display
STATIC mp_obj_t picoware_lvgl_textbox_refresh(mp_obj_t self_in)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        return mp_const_none;
    }

    // Show the textarea
    if (self->textarea)
    {
        // Get current text to calculate line count
        const char *text = lv_textarea_get_text(self->textarea);

        // Count lines
        self->total_lines = 1;
        for (const char *p = text; *p; p++)
        {
            if (*p == '\n')
            {
                self->total_lines++;
            }
        }

        // Update current line if not set
        if (self->current_line < 0)
        {
            self->current_line = 0;
        }

        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_textbox_refresh_obj, picoware_lvgl_textbox_refresh);

// TextBox.scroll_down() - Scroll down by one line
STATIC mp_obj_t picoware_lvgl_textbox_scroll_down(mp_obj_t self_in)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->textarea && self->current_line < self->total_lines - 1)
    {
        self->current_line++;

        // Scroll the textarea
        lv_coord_t scroll_y = self->current_line * LVGL_LINE_HEIGHT;
        lv_obj_scroll_to_y(self->textarea, scroll_y, LV_ANIM_ON);

        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_textbox_scroll_down_obj, picoware_lvgl_textbox_scroll_down);

// TextBox.scroll_up() - Scroll up by one line
STATIC mp_obj_t picoware_lvgl_textbox_scroll_up(mp_obj_t self_in)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->textarea && self->current_line > 0)
    {
        self->current_line--;

        // Scroll the textarea
        lv_coord_t scroll_y = self->current_line * LVGL_LINE_HEIGHT;
        lv_obj_scroll_to_y(self->textarea, scroll_y, LV_ANIM_ON);

        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_textbox_scroll_up_obj, picoware_lvgl_textbox_scroll_up);

// TextBox.set_current_line(line) - Scroll to specific line
STATIC mp_obj_t picoware_lvgl_textbox_set_current_line(mp_obj_t self_in, mp_obj_t line_obj)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int line = mp_obj_get_int(line_obj);

    if (self->total_lines == 0 || line < 0 || line >= self->total_lines)
    {
        return mp_const_none;
    }

    self->current_line = line;

    if (self->textarea)
    {
        lv_coord_t scroll_y = self->current_line * LVGL_LINE_HEIGHT;
        lv_obj_scroll_to_y(self->textarea, scroll_y, LV_ANIM_OFF);
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_textbox_set_current_line_obj, picoware_lvgl_textbox_set_current_line);

// TextBox.set_text(text) - Set text content
STATIC mp_obj_t picoware_lvgl_textbox_set_text(mp_obj_t self_in, mp_obj_t text_obj)
{
    picoware_lvgl_textbox_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *new_text = mp_obj_str_get_str(text_obj);

    // Check if text is unchanged
    if (self->textarea)
    {
        const char *current_text = lv_textarea_get_text(self->textarea);
        if (strcmp(current_text, new_text) == 0)
        {
            return mp_const_none;
        }

        // Set text - LVGL handles storage internally
        lv_textarea_set_text(self->textarea, new_text);

        // Count lines
        self->total_lines = 1;
        for (const char *p = new_text; *p; p++)
        {
            if (*p == '\n')
            {
                self->total_lines++;
            }
        }

        // show
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_textbox_set_text_obj, picoware_lvgl_textbox_set_text);

// TextBox class method table
STATIC const mp_rom_map_elem_t picoware_lvgl_textbox_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&picoware_lvgl_textbox_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&picoware_lvgl_textbox_get_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_text_height), MP_ROM_PTR(&picoware_lvgl_textbox_get_text_height_obj)},
    {MP_ROM_QSTR(MP_QSTR_refresh), MP_ROM_PTR(&picoware_lvgl_textbox_refresh_obj)},
    {MP_ROM_QSTR(MP_QSTR_scroll_down), MP_ROM_PTR(&picoware_lvgl_textbox_scroll_down_obj)},
    {MP_ROM_QSTR(MP_QSTR_scroll_up), MP_ROM_PTR(&picoware_lvgl_textbox_scroll_up_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_current_line), MP_ROM_PTR(&picoware_lvgl_textbox_set_current_line_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_text), MP_ROM_PTR(&picoware_lvgl_textbox_set_text_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&picoware_lvgl_textbox_del_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_lvgl_textbox_del_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lvgl_textbox_locals_dict, picoware_lvgl_textbox_locals_dict_table);

// TextBox class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_textbox_type,
    MP_QSTR_TextBox,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    make_new, picoware_lvgl_textbox_make_new,
    locals_dict, &picoware_lvgl_textbox_locals_dict);
