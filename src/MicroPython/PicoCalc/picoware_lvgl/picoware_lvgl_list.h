/*
 * Picoware LVGL List Header
 * Copyright © 2026 JBlanked
 */

#include "picoware_lvgl.h"

typedef struct
{
    mp_obj_base_t base;
    int y;
    int height;
    uint16_t text_color_565;
    uint16_t background_color_565;
    uint16_t selected_color_565;
    uint16_t border_color_565;
    int border_width;
    int selected_index;
    mp_obj_t *items;
    size_t item_count;
    size_t item_capacity;
    bool is_circular;
    lv_obj_t *screen;
    lv_obj_t *container;
    lv_obj_t *title_label;
    lv_obj_t *list_widget;
    lv_obj_t **list_buttons; // Array of button pointers
} picoware_lvgl_list_obj_t;

const mp_obj_type_t picoware_lvgl_list_type;

// List constructor
STATIC mp_obj_t picoware_lvgl_list_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 7, false);

    picoware_lvgl_list_obj_t *self = mp_obj_malloc_with_finaliser(picoware_lvgl_list_obj_t, &picoware_lvgl_list_type);
    self->base.type = type;

    // Required: y, height
    self->y = mp_obj_get_int(args[0]);
    self->height = mp_obj_get_int(args[1]);

    // Optional: text_color (default: white 0xFFFF)
    self->text_color_565 = (n_args > 2) ? mp_obj_get_int(args[2]) : 0xFFFF;

    // Optional: background_color (default: black 0x0000)
    self->background_color_565 = (n_args > 3) ? mp_obj_get_int(args[3]) : 0x0000;

    // Optional: selected_color (default: blue 0x001F)
    self->selected_color_565 = (n_args > 4) ? mp_obj_get_int(args[4]) : 0x001F;

    // Optional: border_color (default: white 0xFFFF)
    self->border_color_565 = (n_args > 5) ? mp_obj_get_int(args[5]) : 0xFFFF;

    // Optional: border_width (default: 2)
    self->border_width = (n_args > 6) ? mp_obj_get_int(args[6]) : 2;

    // Initialize state
    self->selected_index = 0;
    self->item_capacity = 8;
    self->item_count = 0;
    self->items = m_new(mp_obj_t, self->item_capacity);
    self->is_circular = false;

    // Initialize LVGL objects
    self->screen = NULL;
    self->container = NULL;
    self->title_label = NULL;
    self->list_widget = NULL;
    self->list_buttons = NULL;

    // Create title label immediately if display is available
    if (lvgl_display)
    {
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);
        self->screen = screen;

        // Create title label
        self->title_label = lv_label_create(screen);
        lv_label_set_text(self->title_label, "");
        lv_obj_set_style_text_color(self->title_label, lv_color_from_rgb565(self->text_color_565), LV_PART_MAIN);
        lv_obj_set_style_text_font(self->title_label, &lv_font_montserrat_12, LV_PART_MAIN);
        lv_obj_add_flag(self->title_label, LV_OBJ_FLAG_HIDDEN);
    }

    return MP_OBJ_FROM_PTR(self);
}

// List destructor
STATIC mp_obj_t picoware_lvgl_list_del(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Clean up LVGL objects
    if (lvgl_display)
    {
        if (self->list_widget)
        {
            lv_obj_delete(self->list_widget);
            self->list_widget = NULL;
        }
        if (self->container)
        {
            lv_obj_delete(self->container);
            self->container = NULL;
        }
        if (self->title_label)
        {
            lv_obj_delete(self->title_label);
            self->title_label = NULL;
        }
    }

    // Free list buttons array
    if (self->list_buttons)
    {
        lv_free(self->list_buttons);
        self->list_buttons = NULL;
    }

    // Free items array
    if (self->items)
    {
        m_del(mp_obj_t, self->items, self->item_capacity);
        self->items = NULL;
    }

    // Clear screen
    lv_clear_screen(true);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_del_obj, picoware_lvgl_list_del);

// List.clear() - Clear the list
STATIC mp_obj_t picoware_lvgl_list_clear(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        return mp_const_none;
    }

    // Reset items
    self->item_count = 0;
    self->selected_index = 0;

    // Clear screen
    lv_clear_screen(false);

    // Delete list widget and container
    if (self->list_widget)
    {
        lv_obj_delete(self->list_widget);
        self->list_widget = NULL;
    }
    if (self->container)
    {
        lv_obj_delete(self->container);
        self->container = NULL;
    }

    // Hide title
    if (self->title_label)
    {
        lv_obj_add_flag(self->title_label, LV_OBJ_FLAG_HIDDEN);
    }

    // Free list buttons
    if (self->list_buttons)
    {
        lv_free(self->list_buttons);
        self->list_buttons = NULL;
    }

    lv_refr_now(lvgl_display);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_clear_obj, picoware_lvgl_list_clear);

// List.add_item(item) - Add an item to the list
STATIC mp_obj_t picoware_lvgl_list_add_item(mp_obj_t self_in, mp_obj_t item_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Resize array if needed
    if (self->item_count >= self->item_capacity)
    {
        size_t new_capacity = self->item_capacity * 2;
        self->items = m_renew(mp_obj_t, self->items, self->item_capacity, new_capacity);
        self->item_capacity = new_capacity;
    }

    // Add item
    self->items[self->item_count++] = item_in;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_add_item_obj, picoware_lvgl_list_add_item);

// List.remove_item(index) - Remove an item from the list
STATIC mp_obj_t picoware_lvgl_list_remove_item(mp_obj_t self_in, mp_obj_t index_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int index = mp_obj_get_int(index_in);

    if (index < 0 || (size_t)index >= self->item_count)
    {
        return mp_const_none;
    }

    // Shift items down
    for (size_t i = index; i < self->item_count - 1; i++)
    {
        self->items[i] = self->items[i + 1];
    }
    self->item_count--;

    // Adjust selected index if needed
    if (self->selected_index >= (int)self->item_count && self->item_count > 0)
    {
        self->selected_index = self->item_count - 1;
    }
    if (self->item_count == 0)
    {
        self->selected_index = 0;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_remove_item_obj, picoware_lvgl_list_remove_item);

// List.get_item(index) - Get an item from the list
STATIC mp_obj_t picoware_lvgl_list_get_item(mp_obj_t self_in, mp_obj_t index_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int index = mp_obj_get_int(index_in);

    if (index < 0 || (size_t)index >= self->item_count)
    {
        return mp_const_none;
    }

    return self->items[index];
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_get_item_obj, picoware_lvgl_list_get_item);

// List.item_exists(item) - Check if an item exists in the list
STATIC mp_obj_t picoware_lvgl_list_item_exists(mp_obj_t self_in, mp_obj_t item_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *search_str = mp_obj_str_get_str(item_in);

    for (size_t i = 0; i < self->item_count; i++)
    {
        const char *item_str = mp_obj_str_get_str(self->items[i]);
        if (strcmp(item_str, search_str) == 0)
        {
            return mp_const_true;
        }
    }

    return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_item_exists_obj, picoware_lvgl_list_item_exists);

// List.set_selected(index) - Set the selected item
STATIC mp_obj_t picoware_lvgl_list_set_selected(mp_obj_t self_in, mp_obj_t index_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int index = mp_obj_get_int(index_in);

    if (index >= 0 && (size_t)index < self->item_count)
    {
        self->selected_index = index;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_set_selected_obj, picoware_lvgl_list_set_selected);

// List.scroll_up() - Scroll up
STATIC mp_obj_t picoware_lvgl_list_scroll_up(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->item_count == 0 || !self->list_buttons)
    {
        return mp_const_none;
    }

    self->selected_index--;
    if (self->selected_index < 0)
    {
        self->selected_index = self->item_count - 1;
    }

    // Update button states
    for (size_t i = 0; i < self->item_count; i++)
    {
        if ((int)i == self->selected_index)
        {
            lv_obj_add_state(self->list_buttons[i], LV_STATE_CHECKED);
        }
        else
        {
            lv_obj_remove_state(self->list_buttons[i], LV_STATE_CHECKED);
        }
    }

    // Scroll to make selected item visible
    lv_obj_update_layout(self->list_widget);
    lv_obj_scroll_to_view(self->list_buttons[self->selected_index], LV_ANIM_OFF);

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_scroll_up_obj, picoware_lvgl_list_scroll_up);

// List.set_title(title) - Set the title
STATIC mp_obj_t picoware_lvgl_list_set_title(mp_obj_t self_in, mp_obj_t title_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *new_title = mp_obj_str_get_str(title_in);

    // Update title label
    if (self->title_label)
    {
        lv_label_set_text(self->title_label, new_title);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_set_title_obj, picoware_lvgl_list_set_title);

// List.scroll_down() - Scroll down
STATIC mp_obj_t picoware_lvgl_list_scroll_down(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->item_count == 0 || !self->list_buttons)
    {
        return mp_const_none;
    }

    self->selected_index++;
    if (self->selected_index >= (int)self->item_count)
    {
        self->selected_index = 0;
    }

    // Update button states
    for (size_t i = 0; i < self->item_count; i++)
    {
        if ((int)i == self->selected_index)
        {
            lv_obj_add_state(self->list_buttons[i], LV_STATE_CHECKED);
        }
        else
        {
            lv_obj_remove_state(self->list_buttons[i], LV_STATE_CHECKED);
        }
    }

    // Scroll to make selected item visible
    lv_obj_update_layout(self->list_widget);
    lv_obj_scroll_to_view(self->list_buttons[self->selected_index], LV_ANIM_OFF);

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_scroll_down_obj, picoware_lvgl_list_scroll_down);

// List.draw() - Draw the list
STATIC mp_obj_t picoware_lvgl_list_draw(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);
    self->screen = screen;

    // Clear screen
    lv_clear_screen(false);

    // Clear previous list widget and container
    if (self->list_widget)
    {
        lv_obj_delete(self->list_widget);
        self->list_widget = NULL;
    }
    if (self->container)
    {
        lv_obj_delete(self->container);
        self->container = NULL;
    }

    // Free previous list buttons
    if (self->list_buttons)
    {
        lv_free(self->list_buttons);
        self->list_buttons = NULL;
    }

    if (self->item_count == 0)
    {
        lv_refr_now(lvgl_display);
        return mp_const_none;
    }

    int title_offset = 0;

    // Draw title if set
    if (self->title_label)
    {
        const char *title_text = lv_label_get_text(self->title_label);
        if (title_text && strlen(title_text) > 0)
        {
            title_offset = 40;
            lv_obj_clear_flag(self->title_label, LV_OBJ_FLAG_HIDDEN);
            lv_obj_align(self->title_label, LV_ALIGN_TOP_MID, 0, self->y + 10);
        }
    }

    // Create container for the list
    self->container = lv_obj_create(screen);
    lv_obj_set_size(self->container, DISPLAY_WIDTH, self->height - title_offset);
    lv_obj_set_pos(self->container, 0, self->y + title_offset);
    lv_obj_set_style_bg_color(self->container, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
    lv_obj_set_style_border_width(self->container, self->border_width, LV_PART_MAIN);
    lv_obj_set_style_border_color(self->container, lv_color_from_rgb565(self->border_color_565), LV_PART_MAIN);
    lv_obj_set_style_radius(self->container, 8, LV_PART_MAIN);
    lv_obj_set_style_pad_all(self->container, 0, LV_PART_MAIN);

    // Create LVGL list widget
    self->list_widget = lv_list_create(self->container);
    lv_obj_set_size(self->list_widget, DISPLAY_WIDTH, self->height - title_offset);
    lv_obj_align(self->list_widget, LV_ALIGN_CENTER, 0, 0);

    // Enable vertical scrolling
    lv_obj_set_scroll_dir(self->list_widget, LV_DIR_VER);

    // Style the list background
    lv_obj_set_style_bg_color(self->list_widget, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
    lv_obj_set_style_border_width(self->list_widget, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(self->list_widget, 8, LV_PART_MAIN);
    lv_obj_set_style_pad_row(self->list_widget, 4, LV_PART_MAIN);

    // Style the scrollbar
    lv_obj_set_style_bg_color(self->list_widget, lv_color_from_rgb565(self->border_color_565), LV_PART_SCROLLBAR);
    lv_obj_set_style_bg_opa(self->list_widget, LV_OPA_70, LV_PART_SCROLLBAR);
    lv_obj_set_style_width(self->list_widget, 6, LV_PART_SCROLLBAR);

    // Allocate memory for button array
    self->list_buttons = lv_malloc(self->item_count * sizeof(lv_obj_t *));

    // Add all items to the list
    for (size_t i = 0; i < self->item_count; i++)
    {
        // Get the C string from the MicroPython string object
        const char *item_text = mp_obj_str_get_str(self->items[i]);

        // Create button with proper text
        self->list_buttons[i] = lv_list_add_button(self->list_widget, NULL, item_text);

        // Style the button for normal state
        lv_obj_set_style_bg_color(self->list_buttons[i], lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_bg_opa(self->list_buttons[i], LV_OPA_20, LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_text_color(self->list_buttons[i], lv_color_from_rgb565(self->text_color_565), LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_text_font(self->list_buttons[i], &lv_font_montserrat_12, LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_radius(self->list_buttons[i], 6, LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_pad_all(self->list_buttons[i], 12, LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_border_width(self->list_buttons[i], 1, LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_border_color(self->list_buttons[i], lv_color_from_rgb565(self->border_color_565), LV_PART_MAIN | LV_STATE_DEFAULT);
        lv_obj_set_style_border_opa(self->list_buttons[i], LV_OPA_30, LV_PART_MAIN | LV_STATE_DEFAULT);

        // Style the button for checked (selected) state
        lv_obj_set_style_bg_color(self->list_buttons[i], lv_color_from_rgb565(self->selected_color_565), LV_PART_MAIN | LV_STATE_CHECKED);
        lv_obj_set_style_bg_opa(self->list_buttons[i], LV_OPA_COVER, LV_PART_MAIN | LV_STATE_CHECKED);
        lv_obj_set_style_border_width(self->list_buttons[i], 2, LV_PART_MAIN | LV_STATE_CHECKED);
        lv_obj_set_style_border_color(self->list_buttons[i], lv_color_from_rgb565(self->border_color_565), LV_PART_MAIN | LV_STATE_CHECKED);
        lv_obj_set_style_border_opa(self->list_buttons[i], LV_OPA_COVER, LV_PART_MAIN | LV_STATE_CHECKED);

        // Set initial state
        if ((int)i == self->selected_index)
        {
            lv_obj_add_state(self->list_buttons[i], LV_STATE_CHECKED);
            // Scroll to selected item
            lv_obj_update_layout(self->list_widget);
            lv_obj_scroll_to_view(self->list_buttons[i], LV_ANIM_OFF);
        }
    }

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_draw_obj, picoware_lvgl_list_draw);

// Properties
STATIC mp_obj_t picoware_lvgl_list_current_item(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->selected_index >= 0 && (size_t)self->selected_index < self->item_count)
    {
        return self->items[self->selected_index];
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_current_item_obj, picoware_lvgl_list_current_item);

STATIC mp_obj_t picoware_lvgl_list_item_count_prop(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->item_count);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_item_count_obj, picoware_lvgl_list_item_count_prop);

STATIC mp_obj_t picoware_lvgl_list_selected_index_prop(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->selected_index);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_selected_index_obj, picoware_lvgl_list_selected_index_prop);

STATIC mp_obj_t picoware_lvgl_list_list_height_prop(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->item_count * 40); // approximate item_height with padding
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_list_height_obj, picoware_lvgl_list_list_height_prop);

// List class method table
STATIC const mp_rom_map_elem_t picoware_lvgl_list_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&picoware_lvgl_list_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw), MP_ROM_PTR(&picoware_lvgl_list_draw_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_title), MP_ROM_PTR(&picoware_lvgl_list_set_title_obj)},
    {MP_ROM_QSTR(MP_QSTR_add_item), MP_ROM_PTR(&picoware_lvgl_list_add_item_obj)},
    {MP_ROM_QSTR(MP_QSTR_remove_item), MP_ROM_PTR(&picoware_lvgl_list_remove_item_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_item), MP_ROM_PTR(&picoware_lvgl_list_get_item_obj)},
    {MP_ROM_QSTR(MP_QSTR_item_exists), MP_ROM_PTR(&picoware_lvgl_list_item_exists_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_selected), MP_ROM_PTR(&picoware_lvgl_list_set_selected_obj)},
    {MP_ROM_QSTR(MP_QSTR_scroll_up), MP_ROM_PTR(&picoware_lvgl_list_scroll_up_obj)},
    {MP_ROM_QSTR(MP_QSTR_scroll_down), MP_ROM_PTR(&picoware_lvgl_list_scroll_down_obj)},
    {MP_ROM_QSTR(MP_QSTR_current_item), MP_ROM_PTR(&picoware_lvgl_list_current_item_obj)},
    {MP_ROM_QSTR(MP_QSTR_item_count), MP_ROM_PTR(&picoware_lvgl_list_item_count_obj)},
    {MP_ROM_QSTR(MP_QSTR_selected_index), MP_ROM_PTR(&picoware_lvgl_list_selected_index_obj)},
    {MP_ROM_QSTR(MP_QSTR_list_height), MP_ROM_PTR(&picoware_lvgl_list_list_height_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&picoware_lvgl_list_del_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_lvgl_list_del_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lvgl_list_locals_dict, picoware_lvgl_list_locals_dict_table);

// List class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_list_type,
    MP_QSTR_List,
    MP_TYPE_FLAG_NONE,
    make_new, picoware_lvgl_list_make_new,
    locals_dict, &picoware_lvgl_list_locals_dict);
