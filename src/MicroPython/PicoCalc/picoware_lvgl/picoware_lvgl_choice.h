/*
 * Picoware LVGL Choice Header
 * Copyright © 2026 JBlanked
 */

#include "picoware_lvgl.h"

typedef struct
{
    mp_obj_base_t base;
    int state;
    uint16_t foreground_color_565;
    uint16_t background_color_565;
    int16_t pos_x;
    int16_t pos_y;
    int16_t width;
    int16_t height;
    size_t num_options;
    lv_obj_t *screen;
    lv_obj_t *title_label;
    lv_obj_t *dropdown;
} picoware_lvgl_choice_obj_t;

const mp_obj_type_t picoware_lvgl_choice_type;

// Choice constructor
STATIC mp_obj_t picoware_lvgl_choice_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 5, 8, false);

    picoware_lvgl_choice_obj_t *self = mp_obj_malloc_with_finaliser(picoware_lvgl_choice_obj_t, &picoware_lvgl_choice_type);
    self->base.type = type;

    // Required: position (args[1] - Vector object)
    mp_obj_t *position_items;
    mp_obj_get_array_fixed_n(args[1], 2, &position_items);
    self->pos_x = mp_obj_get_int(position_items[0]);
    self->pos_y = mp_obj_get_int(position_items[1]);

    // Required: size (args[2] - Vector object)
    mp_obj_t *size_items;
    mp_obj_get_array_fixed_n(args[2], 2, &size_items);
    self->width = mp_obj_get_int(size_items[0]);
    self->height = mp_obj_get_int(size_items[1]);

    // Required: title
    const char *title_str = mp_obj_str_get_str(args[3]);

    // Required: options (list of strings)
    mp_obj_t options_list = args[4];
    size_t len;
    mp_obj_t *items;
    mp_obj_get_array(options_list, &len, &items);
    self->num_options = len;

    // Optional: initial_state (default: 0)
    if (n_args > 5)
    {
        self->state = mp_obj_get_int(args[5]);
    }
    else
    {
        self->state = 0;
    }

    // Optional: foreground_color (default: white 0xFFFF)
    if (n_args > 6)
    {
        self->foreground_color_565 = mp_obj_get_int(args[6]);
    }
    else
    {
        self->foreground_color_565 = 0xFFFF;
    }

    // Optional: background_color (default: black 0x0000)
    if (n_args > 7)
    {
        self->background_color_565 = mp_obj_get_int(args[7]);
    }
    else
    {
        self->background_color_565 = 0x0000;
    }

    // Initialize LVGL objects
    self->title_label = NULL;
    self->dropdown = NULL;

    // Clear screen (removing objects here)
    lv_clear_screen(true);

    // Create LVGL objects immediately if display is available
    if (lvgl_display)
    {
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);

        // Create title label
        self->title_label = lv_label_create(screen);
        lv_label_set_text(self->title_label, title_str);
        lv_obj_set_pos(self->title_label, self->pos_x + (self->width - strlen(title_str) * 6) / 2, self->pos_y + 5);
        lv_obj_set_style_text_color(self->title_label, lv_color_from_rgb565(self->foreground_color_565), LV_PART_MAIN);
        lv_obj_add_flag(self->title_label, LV_OBJ_FLAG_HIDDEN);

        // Create dropdown
        self->dropdown = lv_dropdown_create(screen);
        lv_obj_set_pos(self->dropdown, self->pos_x + 10, self->pos_y + 30);
        lv_obj_set_width(self->dropdown, self->width - 20);
        lv_dropdown_set_dir(self->dropdown, LV_DIR_BOTTOM);

        // Build options string for dropdown (newline-separated)
        // Calculate total length needed
        size_t total_len = 0;
        for (size_t i = 0; i < len; i++)
        {
            const char *opt = mp_obj_str_get_str(items[i]);
            total_len += strlen(opt) + 1; // +1 for newline or null
        }

        char *options_str = lv_malloc(total_len);
        if (options_str)
        {
            char *ptr = options_str;
            for (size_t i = 0; i < len; i++)
            {
                const char *opt = mp_obj_str_get_str(items[i]);
                size_t opt_len = strlen(opt);
                memcpy(ptr, opt, opt_len);
                ptr += opt_len;
                if (i < len - 1)
                {
                    *ptr++ = '\n';
                }
            }
            *ptr = '\0';

            lv_dropdown_set_options(self->dropdown, options_str);
            lv_free(options_str);
        }

        // Set initial state
        lv_dropdown_set_selected(self->dropdown, self->state, LV_ANIM_OFF);
        lv_dropdown_set_selected_highlight(self->dropdown, true);

        // Style the dropdown
        lv_obj_set_style_bg_color(self->dropdown, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
        lv_obj_set_style_text_color(self->dropdown, lv_color_from_rgb565(self->foreground_color_565), LV_PART_MAIN);
        lv_obj_set_style_border_color(self->dropdown, lv_color_from_rgb565(self->foreground_color_565), LV_PART_MAIN);
        lv_obj_add_flag(self->dropdown, LV_OBJ_FLAG_HIDDEN);
    }

    return MP_OBJ_FROM_PTR(self);
}

// Choice destructor
STATIC mp_obj_t picoware_lvgl_choice_del(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Clean up LVGL objects
    if (lvgl_display)
    {
        if (self->dropdown)
        {
            lv_obj_delete(self->dropdown);
            self->dropdown = NULL;
        }
        if (self->title_label)
        {
            lv_obj_delete(self->title_label);
            self->title_label = NULL;
        }
    }

    // Clear screen
    lv_clear_screen(true);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_del_obj, picoware_lvgl_choice_del);

// Choice.state property getter
STATIC mp_obj_t picoware_lvgl_choice_get_state(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Sync state from dropdown if it exists
    if (self->dropdown)
    {
        self->state = lv_dropdown_get_selected(self->dropdown);
    }

    return mp_obj_new_int(self->state);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_get_state_obj, picoware_lvgl_choice_get_state);

// Choice.state property setter
STATIC mp_obj_t picoware_lvgl_choice_set_state(mp_obj_t self_in, mp_obj_t value)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->state = mp_obj_get_int(value);

    if (self->dropdown)
    {
        lv_dropdown_set_selected(self->dropdown, self->state, LV_ANIM_OFF);
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_choice_set_state_obj, picoware_lvgl_choice_set_state);

// Choice.clear() - Clear the choice (hide it)
STATIC mp_obj_t picoware_lvgl_choice_clear(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->dropdown)
    {
        lv_obj_add_flag(self->dropdown, LV_OBJ_FLAG_HIDDEN);
    }
    if (self->title_label)
    {
        lv_obj_add_flag(self->title_label, LV_OBJ_FLAG_HIDDEN);
    }

    if (lvgl_display)
    {
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_clear_obj, picoware_lvgl_choice_clear);

// Choice.draw() - Draw the choice
STATIC mp_obj_t picoware_lvgl_choice_draw(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    // Show the choice elements
    if (self->title_label)
    {
        lv_obj_clear_flag(self->title_label, LV_OBJ_FLAG_HIDDEN);
    }
    if (self->dropdown)
    {
        lv_obj_clear_flag(self->dropdown, LV_OBJ_FLAG_HIDDEN);
    }

    lv_refr_now(lvgl_display);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_draw_obj, picoware_lvgl_choice_draw);

// Choice.reset() - Reset to initial state
STATIC mp_obj_t picoware_lvgl_choice_reset(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    self->state = 0;

    if (self->dropdown)
    {
        lv_dropdown_set_selected(self->dropdown, 0, LV_ANIM_OFF);
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_reset_obj, picoware_lvgl_choice_reset);

// Choice.scroll_down() - Scroll to next option
STATIC mp_obj_t picoware_lvgl_choice_scroll_down(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->dropdown && self->num_options > 0)
    {
        self->state++;
        if (self->state >= (int)self->num_options)
        {
            self->state = 0;
        }
        lv_clear_screen(false);
        lv_dropdown_set_selected(self->dropdown, self->state, LV_ANIM_OFF);
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_scroll_down_obj, picoware_lvgl_choice_scroll_down);

// Choice.scroll_up() - Scroll to previous option
STATIC mp_obj_t picoware_lvgl_choice_scroll_up(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->dropdown && self->num_options > 0)
    {
        self->state--;
        if (self->state < 0)
        {
            self->state = self->num_options - 1;
        }
        lv_clear_screen(false);
        lv_dropdown_set_selected(self->dropdown, self->state, LV_ANIM_OFF);
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_scroll_up_obj, picoware_lvgl_choice_scroll_up);

// Choice.close() - Close the dropdown
STATIC mp_obj_t picoware_lvgl_choice_close(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->dropdown)
    {
        lv_dropdown_close(self->dropdown);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_close_obj, picoware_lvgl_choice_close);

// Choice.is_open() - Check if dropdown is open
STATIC mp_obj_t picoware_lvgl_choice_is_open(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->dropdown)
    {
        return mp_obj_new_bool(lv_dropdown_is_open(self->dropdown));
    }
    return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_is_open_obj, picoware_lvgl_choice_is_open);

// Choice.open() - Open the dropdown
STATIC mp_obj_t picoware_lvgl_choice_open(mp_obj_t self_in)
{
    picoware_lvgl_choice_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->dropdown)
    {
        lv_dropdown_open(self->dropdown);
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_choice_open_obj, picoware_lvgl_choice_open);

// Choice class method table
STATIC const mp_rom_map_elem_t picoware_lvgl_choice_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&picoware_lvgl_choice_close_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&picoware_lvgl_choice_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw), MP_ROM_PTR(&picoware_lvgl_choice_draw_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_state), MP_ROM_PTR(&picoware_lvgl_choice_get_state_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_open), MP_ROM_PTR(&picoware_lvgl_choice_is_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_open), MP_ROM_PTR(&picoware_lvgl_choice_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&picoware_lvgl_choice_reset_obj)},
    {MP_ROM_QSTR(MP_QSTR_scroll_down), MP_ROM_PTR(&picoware_lvgl_choice_scroll_down_obj)},
    {MP_ROM_QSTR(MP_QSTR_scroll_up), MP_ROM_PTR(&picoware_lvgl_choice_scroll_up_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_state), MP_ROM_PTR(&picoware_lvgl_choice_set_state_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&picoware_lvgl_choice_del_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_lvgl_choice_del_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lvgl_choice_locals_dict, picoware_lvgl_choice_locals_dict_table);

// Choice class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_choice_type,
    MP_QSTR_Choice,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    make_new, picoware_lvgl_choice_make_new,
    locals_dict, &picoware_lvgl_choice_locals_dict);
