#include "picoware_lvgl_list.h"

const mp_obj_type_t picoware_lvgl_list_type;

void picoware_lvgl_list_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "List(y=");
    mp_obj_print_helper(print, mp_obj_new_int(self->y), PRINT_REPR);
    mp_print_str(print, ", height=");
    mp_obj_print_helper(print, mp_obj_new_int(self->height), PRINT_REPR);
    mp_print_str(print, ", text_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->text_color_565), PRINT_REPR);
    mp_print_str(print, ", background_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->background_color_565), PRINT_REPR);
    mp_print_str(print, ", selected_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->selected_color_565), PRINT_REPR);
    mp_print_str(print, ", border_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->border_color_565), PRINT_REPR);
    mp_print_str(print, ", border_width=");
    mp_obj_print_helper(print, mp_obj_new_int(self->border_width), PRINT_REPR);
    mp_print_str(print, ", selected_index=");
    mp_obj_print_helper(print, mp_obj_new_int(self->selected_index), PRINT_REPR);
    mp_print_str(print, ", item_count=");
    mp_obj_print_helper(print, mp_obj_new_int(self->item_count), PRINT_REPR);
    mp_print_str(print, ", is_circular=");
    mp_print_str(print, self->is_circular ? "True" : "False");
    mp_print_str(print, ")");
}

// List constructor
mp_obj_t picoware_lvgl_list_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
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
    self->title_label = NULL;
    self->list_widget = NULL;
    self->list_buttons = NULL;

    // lv_clear_screen(true); // i bet the issue is here?

    // Create title label immediately if display is available
    if (lvgl_display)
    {
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);

        // Create title label
        self->title_label = lv_label_create(screen);
        lv_label_set_text(self->title_label, "");
        lv_obj_set_style_text_color(self->title_label, lv_color_from_rgb565(self->text_color_565), LV_PART_MAIN);
        lv_obj_set_style_text_font(self->title_label, &lv_font_montserrat_12, LV_PART_MAIN);
        lv_obj_add_flag(self->title_label, LV_OBJ_FLAG_HIDDEN);
    }
    self->freed = false;
    self->items_changed = false;
    return MP_OBJ_FROM_PTR(self);
}

// List destructor
mp_obj_t picoware_lvgl_list_del(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }

    // Clean up LVGL objects
    if (lvgl_display)
    {
        if (self->list_widget)
        {
            lv_obj_delete(self->list_widget);
            self->list_widget = NULL;
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

    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_del_obj, picoware_lvgl_list_del);

void picoware_lvgl_list_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        switch (attribute)
        {
        case MP_QSTR_y:
            destination[0] = mp_obj_new_int(self->y);
            break;
        case MP_QSTR_height:
            destination[0] = mp_obj_new_int(self->height);
            break;
        case MP_QSTR_text_color:
            destination[0] = mp_obj_new_int(self->text_color_565);
            break;
        case MP_QSTR_background_color:
            destination[0] = mp_obj_new_int(self->background_color_565);
            break;
        case MP_QSTR_selected_color:
            destination[0] = mp_obj_new_int(self->selected_color_565);
            break;
        case MP_QSTR_border_color:
            destination[0] = mp_obj_new_int(self->border_color_565);
            break;
        case MP_QSTR_border_width:
            destination[0] = mp_obj_new_int(self->border_width);
            break;
        case MP_QSTR_selected_index:
            destination[0] = mp_obj_new_int(self->selected_index);
            break;
        case MP_QSTR_item_count:
            destination[0] = mp_obj_new_int(self->item_count);
            break;
        case MP_QSTR_is_circular:
            destination[0] = mp_obj_new_bool(self->is_circular);
            break;
        case MP_QSTR__del__:
            destination[0] = MP_OBJ_FROM_PTR(&picoware_lvgl_list_del_obj);
            break;
        default:
            return; // Fail
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    { // Store attributes
        switch (attribute)
        {
        case MP_QSTR_y:
            self->y = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_height:
            self->height = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_text_color:
            self->text_color_565 = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_background_color:
            self->background_color_565 = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_selected_color:
            self->selected_color_565 = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_border_color:
            self->border_color_565 = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_border_width:
            self->border_width = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_selected_index:
            self->selected_index = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_is_circular:
            self->is_circular = mp_obj_is_true(destination[1]);
            break;
        default:
            return; // Fail
        };
        destination[0] = MP_OBJ_NULL;
    }
}

// List.clear() - Clear the list
mp_obj_t picoware_lvgl_list_clear(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        return mp_const_none;
    }

    // Reset items
    self->item_count = 0;
    self->selected_index = 0;
    self->items_changed = true;

    // Clear screen
    lv_clear_screen(false);

    // Delete list widget
    if (self->list_widget)
    {
        lv_obj_delete(self->list_widget);
        self->list_widget = NULL;
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
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_clear_obj, picoware_lvgl_list_clear);

// List.add_item(item) - Add an item to the list
mp_obj_t picoware_lvgl_list_add_item(mp_obj_t self_in, mp_obj_t item_in)
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
    self->items_changed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_add_item_obj, picoware_lvgl_list_add_item);

// List.remove_item(index) - Remove an item from the list
mp_obj_t picoware_lvgl_list_remove_item(mp_obj_t self_in, mp_obj_t index_in)
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
    self->items_changed = true;

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_remove_item_obj, picoware_lvgl_list_remove_item);

// List.get_item(index) - Get an item from the list
mp_obj_t picoware_lvgl_list_get_item(mp_obj_t self_in, mp_obj_t index_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int index = mp_obj_get_int(index_in);

    if (index < 0 || (size_t)index >= self->item_count)
    {
        return mp_const_none;
    }

    return self->items[index];
}
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_get_item_obj, picoware_lvgl_list_get_item);

// List.item_exists(item) - Check if an item exists in the list
mp_obj_t picoware_lvgl_list_item_exists(mp_obj_t self_in, mp_obj_t item_in)
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
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_item_exists_obj, picoware_lvgl_list_item_exists);

// List.set_selected(index) - Set the selected item
mp_obj_t picoware_lvgl_list_set_selected(mp_obj_t self_in, mp_obj_t index_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int index = mp_obj_get_int(index_in);

    if (index >= 0 && (size_t)index < self->item_count)
    {
        self->selected_index = index;
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_set_selected_obj, picoware_lvgl_list_set_selected);

// List.scroll_up() - Scroll up
mp_obj_t picoware_lvgl_list_scroll_up(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->item_count == 0 || !self->list_buttons)
    {
        return mp_const_none;
    }

    int old_index = self->selected_index;
    self->selected_index--;
    if (self->selected_index < 0)
    {
        self->selected_index = self->item_count - 1;
    }

    // Update only the two changed buttons
    lv_obj_remove_state(self->list_buttons[old_index], LV_STATE_CHECKED);
    lv_obj_add_state(self->list_buttons[self->selected_index], LV_STATE_CHECKED);

    // Scroll to make selected item visible
    lv_obj_update_layout(self->list_widget);
    lv_obj_scroll_to_view(self->list_buttons[self->selected_index], LV_ANIM_OFF);

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_scroll_up_obj, picoware_lvgl_list_scroll_up);

// List.set_title(title) - Set the title
mp_obj_t picoware_lvgl_list_set_title(mp_obj_t self_in, mp_obj_t title_in)
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
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_list_set_title_obj, picoware_lvgl_list_set_title);

// List.scroll_down() - Scroll down
mp_obj_t picoware_lvgl_list_scroll_down(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (self->item_count == 0 || !self->list_buttons)
    {
        return mp_const_none;
    }

    int old_index = self->selected_index;
    self->selected_index++;
    if (self->selected_index >= (int)self->item_count)
    {
        self->selected_index = 0;
    }

    // Update only the two changed buttons
    lv_obj_remove_state(self->list_buttons[old_index], LV_STATE_CHECKED);
    lv_obj_add_state(self->list_buttons[self->selected_index], LV_STATE_CHECKED);

    // Scroll to make selected item visible
    lv_obj_update_layout(self->list_widget);
    lv_obj_scroll_to_view(self->list_buttons[self->selected_index], LV_ANIM_OFF);

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_scroll_down_obj, picoware_lvgl_list_scroll_down);

// List.draw() - Draw the list
mp_obj_t picoware_lvgl_list_draw(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    if (self->items_changed)
    {
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);

        // Clear screen
        lv_clear_screen(false);

        // Clear previous list widget
        if (self->list_widget)
        {
            lv_obj_delete(self->list_widget);
            self->list_widget = NULL;
        }

        // Free previous list buttons
        if (self->list_buttons)
        {
            lv_free(self->list_buttons);
            self->list_buttons = NULL;
        }

        if (self->item_count == 0)
        {
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

        // Create LVGL list widget directly on screen (no container wrapper to reduce widget tree depth)
        self->list_widget = lv_list_create(screen);
        lv_obj_set_size(self->list_widget, DISPLAY_WIDTH, self->height - title_offset);
        lv_obj_set_pos(self->list_widget, 0, self->y + title_offset);

        // Enable vertical scrolling
        lv_obj_set_scroll_dir(self->list_widget, LV_DIR_VER);

        // Style the list widget (includes border previously on container)
        lv_obj_set_style_bg_color(self->list_widget, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
        lv_obj_set_style_border_width(self->list_widget, self->border_width, LV_PART_MAIN);
        lv_obj_set_style_border_color(self->list_widget, lv_color_from_rgb565(self->border_color_565), LV_PART_MAIN);
        lv_obj_set_style_radius(self->list_widget, 0, LV_PART_MAIN);
        lv_obj_set_style_pad_all(self->list_widget, 8, LV_PART_MAIN);
        lv_obj_set_style_pad_row(self->list_widget, 4, LV_PART_MAIN);

        // Style the scrollbar
        lv_obj_set_style_bg_color(self->list_widget, lv_color_from_rgb565(self->border_color_565), LV_PART_SCROLLBAR);
        lv_obj_set_style_bg_opa(self->list_widget, LV_OPA_COVER, LV_PART_SCROLLBAR);
        lv_obj_set_style_width(self->list_widget, 6, LV_PART_SCROLLBAR);

        // Allocate memory for button array
        self->list_buttons = lv_malloc(self->item_count * sizeof(lv_obj_t *));
        if (!self->list_buttons)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("Failed to allocate memory for list buttons"));
        }

        // Add all items to the list
        for (size_t i = 0; i < self->item_count; i++)
        {
            const char *item_text = mp_obj_str_get_str(self->items[i]);
            self->list_buttons[i] = lv_list_add_button(self->list_widget, NULL, item_text);
            if (!self->list_buttons[i])
            {
                mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("list button alloc failed"));
            }

            // Style the button for normal state
            lv_obj_set_style_bg_color(self->list_buttons[i], lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN | LV_STATE_DEFAULT);
            lv_obj_set_style_bg_opa(self->list_buttons[i], LV_OPA_COVER, LV_PART_MAIN | LV_STATE_DEFAULT);
            lv_obj_set_style_text_color(self->list_buttons[i], lv_color_from_rgb565(self->text_color_565), LV_PART_MAIN | LV_STATE_DEFAULT);
            lv_obj_set_style_text_font(self->list_buttons[i], &lv_font_montserrat_12, LV_PART_MAIN | LV_STATE_DEFAULT);
            lv_obj_set_style_radius(self->list_buttons[i], 0, LV_PART_MAIN | LV_STATE_DEFAULT);
            lv_obj_set_style_pad_all(self->list_buttons[i], 12, LV_PART_MAIN | LV_STATE_DEFAULT);
            lv_obj_set_style_border_width(self->list_buttons[i], 1, LV_PART_MAIN | LV_STATE_DEFAULT);
            lv_obj_set_style_border_color(self->list_buttons[i], lv_color_from_rgb565(self->border_color_565), LV_PART_MAIN | LV_STATE_DEFAULT);

            // Style the button for checked (selected) state
            lv_obj_set_style_bg_color(self->list_buttons[i], lv_color_from_rgb565(self->selected_color_565), LV_PART_MAIN | LV_STATE_CHECKED);
            lv_obj_set_style_bg_opa(self->list_buttons[i], LV_OPA_COVER, LV_PART_MAIN | LV_STATE_CHECKED);
            lv_obj_set_style_radius(self->list_buttons[i], 0, LV_PART_MAIN | LV_STATE_CHECKED);
            lv_obj_set_style_border_width(self->list_buttons[i], 2, LV_PART_MAIN | LV_STATE_CHECKED);
            lv_obj_set_style_border_color(self->list_buttons[i], lv_color_from_rgb565(self->border_color_565), LV_PART_MAIN | LV_STATE_CHECKED);
        }

        // Set initial state
        if (self->selected_index >= 0 && (size_t)self->selected_index < self->item_count)
        {
            lv_obj_add_state(self->list_buttons[self->selected_index], LV_STATE_CHECKED);
            lv_obj_update_layout(self->list_widget);
            lv_obj_scroll_to_view(self->list_buttons[self->selected_index], LV_ANIM_OFF);
        }

        lv_refr_now(lvgl_display);

        self->items_changed = false;
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_draw_obj, picoware_lvgl_list_draw);

// Properties
mp_obj_t picoware_lvgl_list_current_item(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->selected_index >= 0 && (size_t)self->selected_index < self->item_count)
    {
        return self->items[self->selected_index];
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_current_item_obj, picoware_lvgl_list_current_item);

mp_obj_t picoware_lvgl_list_item_count_prop(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->item_count);
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_item_count_obj, picoware_lvgl_list_item_count_prop);

mp_obj_t picoware_lvgl_list_selected_index_prop(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->selected_index);
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_selected_index_obj, picoware_lvgl_list_selected_index_prop);

mp_obj_t picoware_lvgl_list_list_height_prop(mp_obj_t self_in)
{
    picoware_lvgl_list_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(self->item_count * 40); // approximate item_height with padding
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_list_list_height_obj, picoware_lvgl_list_list_height_prop);

// List class method table
static const mp_rom_map_elem_t picoware_lvgl_list_locals_dict_table[] = {
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
static MP_DEFINE_CONST_DICT(picoware_lvgl_list_locals_dict, picoware_lvgl_list_locals_dict_table);

// List class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_list_type,
    MP_QSTR_List,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, picoware_lvgl_list_print,
    make_new, picoware_lvgl_list_make_new,
    attr, picoware_lvgl_list_attr,
    locals_dict, &picoware_lvgl_list_locals_dict);
