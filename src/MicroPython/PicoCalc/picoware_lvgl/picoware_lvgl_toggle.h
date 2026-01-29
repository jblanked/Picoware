/*
 * Picoware LVGL Toggle Header
 * Copyright © 2026 JBlanked
 */

#include "picoware_lvgl.h"

typedef struct
{
    mp_obj_base_t base;
    bool state;
    uint16_t foreground_color_565;
    uint16_t background_color_565;
    uint16_t on_color_565;
    uint16_t border_color_565;
    int16_t pos_x;
    int16_t pos_y;
    int16_t width;
    int16_t height;
    lv_obj_t *screen;
    lv_obj_t *switch_obj;
    lv_obj_t *label;
} picoware_lvgl_toggle_obj_t;

const mp_obj_type_t picoware_lvgl_toggle_type;

// Toggle constructor
STATIC mp_obj_t picoware_lvgl_toggle_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 3, 10, false);

    picoware_lvgl_toggle_obj_t *self = mp_obj_malloc_with_finaliser(picoware_lvgl_toggle_obj_t, &picoware_lvgl_toggle_type);
    self->base.type = type;

    // Required: position (args[0] - Vector object)
    mp_obj_t *position_items;
    mp_obj_get_array_fixed_n(args[0], 2, &position_items);
    self->pos_x = mp_obj_get_int(position_items[0]);
    self->pos_y = mp_obj_get_int(position_items[1]);

    // Required: size (args[1] - Vector object)
    mp_obj_t *size_items;
    mp_obj_get_array_fixed_n(args[1], 2, &size_items);
    self->width = mp_obj_get_int(size_items[0]);
    self->height = mp_obj_get_int(size_items[1]);

    // Required: text
    const char *text_str = mp_obj_str_get_str(args[2]);

    // Optional: initial_state (default: false)
    if (n_args > 3)
    {
        self->state = mp_obj_is_true(args[3]);
    }
    else
    {
        self->state = false;
    }

    // Optional: foreground_color (default: white 0xFFFF)
    if (n_args > 4)
    {
        self->foreground_color_565 = mp_obj_get_int(args[4]);
    }
    else
    {
        self->foreground_color_565 = 0xFFFF;
    }

    // Optional: background_color (default: black 0x0000)
    if (n_args > 5)
    {
        self->background_color_565 = mp_obj_get_int(args[5]);
    }
    else
    {
        self->background_color_565 = 0x0000;
    }

    // Optional: on_color (default: blue 0x001F)
    if (n_args > 6)
    {
        self->on_color_565 = mp_obj_get_int(args[6]);
    }
    else
    {
        self->on_color_565 = 0x001F;
    }

    // Optional: border_color (default: white 0xFFFF)
    if (n_args > 7)
    {
        self->border_color_565 = mp_obj_get_int(args[7]);
    }
    else
    {
        self->border_color_565 = 0xFFFF;
    }

    // Initialize LVGL objects
    self->screen = NULL;
    self->switch_obj = NULL;
    self->label = NULL;

    // Create LVGL objects immediately if display is available
    if (lvgl_display)
    {
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);
        self->screen = screen;

        // Create label
        self->label = lv_label_create(screen);
        lv_label_set_text(self->label, text_str);
        lv_obj_set_pos(self->label, self->pos_x + 5, self->pos_y + self->height / 2 - 8);
        lv_obj_set_style_text_color(self->label, lv_color_from_rgb565(self->foreground_color_565), LV_PART_MAIN);
        lv_obj_add_flag(self->label, LV_OBJ_FLAG_HIDDEN);

        // Create switch
        self->switch_obj = lv_switch_create(screen);
        lv_obj_set_pos(self->switch_obj, self->pos_x + self->width - 60, self->pos_y + (self->height - 30) / 2);
        lv_obj_set_size(self->switch_obj, 50, 25);

        // Style the switch
        lv_obj_set_style_bg_color(self->switch_obj, lv_color_from_rgb565(self->border_color_565), LV_PART_MAIN);
        lv_obj_set_style_bg_color(self->switch_obj, lv_color_from_rgb565(self->on_color_565), LV_PART_INDICATOR);

        // Set initial state
        if (self->state)
        {
            lv_obj_add_state(self->switch_obj, LV_STATE_CHECKED);
        }
        else
        {
            lv_obj_clear_state(self->switch_obj, LV_STATE_CHECKED);
        }
        lv_obj_add_flag(self->switch_obj, LV_OBJ_FLAG_HIDDEN);
    }

    return MP_OBJ_FROM_PTR(self);
}

// Toggle destructor
STATIC mp_obj_t picoware_lvgl_toggle_del(mp_obj_t self_in)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Clean up LVGL objects
    if (lvgl_display)
    {
        if (self->switch_obj)
        {
            lv_obj_delete(self->switch_obj);
            self->switch_obj = NULL;
        }
        if (self->label)
        {
            lv_obj_delete(self->label);
            self->label = NULL;
        }
    }

    // Clear screen
    lv_clear_screen(true);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_toggle_del_obj, picoware_lvgl_toggle_del);

// Toggle.state property getter
STATIC mp_obj_t picoware_lvgl_toggle_get_state(mp_obj_t self_in)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(self->state);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_toggle_get_state_obj, picoware_lvgl_toggle_get_state);

// Toggle.state property setter
STATIC mp_obj_t picoware_lvgl_toggle_set_state(mp_obj_t self_in, mp_obj_t value)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->state = mp_obj_is_true(value);

    // Update switch if it exists
    if (self->switch_obj)
    {
        if (self->state)
        {
            lv_obj_add_state(self->switch_obj, LV_STATE_CHECKED);
        }
        else
        {
            lv_obj_clear_state(self->switch_obj, LV_STATE_CHECKED);
        }
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_toggle_set_state_obj, picoware_lvgl_toggle_set_state);

// Toggle.text property getter
STATIC mp_obj_t picoware_lvgl_toggle_get_text(mp_obj_t self_in)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->label)
    {
        const char *text = lv_label_get_text(self->label);
        return mp_obj_new_str(text, strlen(text));
    }
    return mp_obj_new_str("", 0);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_toggle_get_text_obj, picoware_lvgl_toggle_get_text);

// Toggle.text property setter
STATIC mp_obj_t picoware_lvgl_toggle_set_text(mp_obj_t self_in, mp_obj_t value)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *new_text = mp_obj_str_get_str(value);

    // Update label if it exists
    if (self->label)
    {
        lv_label_set_text(self->label, new_text);
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_toggle_set_text_obj, picoware_lvgl_toggle_set_text);

// Toggle.clear() - Clear the toggle (hide it)
STATIC mp_obj_t picoware_lvgl_toggle_clear(mp_obj_t self_in)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);

    lv_clear_screen(false);

    if (self->switch_obj)
    {
        lv_obj_add_flag(self->switch_obj, LV_OBJ_FLAG_HIDDEN);
    }
    if (self->label)
    {
        lv_obj_add_flag(self->label, LV_OBJ_FLAG_HIDDEN);
    }

    if (lvgl_display)
    {
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_toggle_clear_obj, picoware_lvgl_toggle_clear);

// Toggle.draw(swap=True, clear=True, selected=False) - Draw the toggle
STATIC mp_obj_t picoware_lvgl_toggle_draw(size_t n_args, const mp_obj_t *args)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(args[0]);

    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    // Get optional parameters
    bool swap = (n_args > 1) ? mp_obj_is_true(args[1]) : true;

    // Show the toggle elements
    if (self->label)
    {
        lv_obj_clear_flag(self->label, LV_OBJ_FLAG_HIDDEN);
    }
    if (self->switch_obj)
    {
        lv_obj_clear_flag(self->switch_obj, LV_OBJ_FLAG_HIDDEN);
    }

    // Refresh display if swap is requested
    if (swap)
    {
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lvgl_toggle_draw_obj, 1, 4, picoware_lvgl_toggle_draw);

// Toggle.toggle() - Toggle the state
STATIC mp_obj_t picoware_lvgl_toggle_toggle(mp_obj_t self_in)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);

    self->state = !self->state;

    if (self->switch_obj)
    {
        if (self->state)
        {
            lv_obj_add_state(self->switch_obj, LV_STATE_CHECKED);
        }
        else
        {
            lv_obj_clear_state(self->switch_obj, LV_STATE_CHECKED);
        }
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_toggle_toggle_obj, picoware_lvgl_toggle_toggle);

// Toggle.update(text, state) - Update text and state
STATIC mp_obj_t picoware_lvgl_toggle_update(mp_obj_t self_in, mp_obj_t text_obj, mp_obj_t state_obj)
{
    picoware_lvgl_toggle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *new_text = mp_obj_str_get_str(text_obj);
    bool new_state = mp_obj_is_true(state_obj);

    self->state = new_state;

    // Update UI
    if (self->label)
    {
        lv_label_set_text(self->label, new_text);
    }
    if (self->switch_obj)
    {
        if (self->state)
        {
            lv_obj_add_state(self->switch_obj, LV_STATE_CHECKED);
        }
        else
        {
            lv_obj_clear_state(self->switch_obj, LV_STATE_CHECKED);
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(picoware_lvgl_toggle_update_obj, picoware_lvgl_toggle_update);

// Toggle class method table
STATIC const mp_rom_map_elem_t picoware_lvgl_toggle_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&picoware_lvgl_toggle_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw), MP_ROM_PTR(&picoware_lvgl_toggle_draw_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_state), MP_ROM_PTR(&picoware_lvgl_toggle_get_state_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_state), MP_ROM_PTR(&picoware_lvgl_toggle_set_state_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_text), MP_ROM_PTR(&picoware_lvgl_toggle_get_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_text), MP_ROM_PTR(&picoware_lvgl_toggle_set_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_toggle), MP_ROM_PTR(&picoware_lvgl_toggle_toggle_obj)},
    {MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&picoware_lvgl_toggle_update_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&picoware_lvgl_toggle_del_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_lvgl_toggle_del_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lvgl_toggle_locals_dict, picoware_lvgl_toggle_locals_dict_table);

// Toggle class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_toggle_type,
    MP_QSTR_Toggle,
    MP_TYPE_FLAG_NONE,
    make_new, picoware_lvgl_toggle_make_new,
    locals_dict, &picoware_lvgl_toggle_locals_dict);
