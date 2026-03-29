#include "picoware_lvgl_alert.h"

const mp_obj_type_t picoware_lvgl_alert_type;

void picoware_lvgl_alert_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Alert(text_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->text_color_565), PRINT_REPR);
    mp_print_str(print, ", background_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->background_color_565), PRINT_REPR);
    mp_print_str(print, ", is_circular=");
    mp_print_str(print, self->is_circular ? "True" : "False");
    mp_print_str(print, ")");
}

// Alert constructor
mp_obj_t picoware_lvgl_alert_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 1, 3, false);

    picoware_lvgl_alert_obj_t *self = mp_obj_malloc_with_finaliser(picoware_lvgl_alert_obj_t, &picoware_lvgl_alert_type);
    self->base.type = type;

    // Get text argument (required)
    const char *text = mp_obj_str_get_str(args[0]);

    // Get optional text_color (default: white 0xFFFF)
    if (n_args > 1)
    {
        self->text_color_565 = mp_obj_get_int(args[1]);
    }
    else
    {
        self->text_color_565 = 0xFFFF;
    }

    // Get optional background_color (default: black 0x0000)
    if (n_args > 2)
    {
        self->background_color_565 = mp_obj_get_int(args[2]);
    }
    else
    {
        self->background_color_565 = 0x0000;
    }

    // Detect circular display (always false for now...)
    self->is_circular = false;

    // Create message box immediately if display is available
    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    lv_clear_screen(true);

    // Create message box with text
    self->msgbox = lv_msgbox_create(lv_screen_active());
    lv_obj_set_style_bg_color(self->msgbox, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
    lv_obj_set_style_text_color(self->msgbox, lv_color_from_rgb565(self->text_color_565), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(self->msgbox, LV_OPA_100, LV_PART_MAIN);

    lv_obj_set_style_clip_corner(self->msgbox, true, 0);

    lv_obj_set_size(self->msgbox, DISPLAY_HEIGHT - 32, DISPLAY_WIDTH - 32);

    // Align to center
    lv_obj_align(self->msgbox, LV_ALIGN_CENTER, 0, 0);

    // Add empty title (will be set in draw())
    lv_msgbox_add_title(self->msgbox, "");

    // Add text directly to the message box
    lv_msgbox_add_text(self->msgbox, text);

    lv_obj_t *content = lv_msgbox_get_content(self->msgbox);
    lv_obj_set_flex_flow(content, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_flex_align(content, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_right(content, -1, LV_PART_SCROLLBAR);

    // Add Back button
    lv_obj_t *apply_button = lv_msgbox_add_footer_button(self->msgbox, "Back");

    // Style the footer before styling the button
    lv_obj_t *footer = lv_msgbox_get_footer(self->msgbox);
    lv_obj_set_style_bg_color(footer, lv_color_from_rgb565(self->text_color_565), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(footer, LV_OPA_100, LV_PART_MAIN);
    lv_obj_set_style_pad_all(footer, 0, LV_PART_MAIN);

    // Style the button to have proper padding/margins
    lv_obj_set_style_pad_all(apply_button, 10, LV_PART_MAIN);
    lv_obj_set_style_margin_all(apply_button, 8, LV_PART_MAIN);
    lv_obj_set_style_bg_color(apply_button, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
    lv_obj_set_style_text_color(apply_button, lv_color_from_rgb565(self->text_color_565), LV_PART_MAIN);

    // Hide the msgbox initially (will be shown in draw())
    lv_obj_add_flag(self->msgbox, LV_OBJ_FLAG_HIDDEN);

    return MP_OBJ_FROM_PTR(self);
}

// Alert destructor
mp_obj_t picoware_lvgl_alert_del(mp_obj_t self_in)
{
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }

    // Clean up LVGL objects
    if (self->msgbox)
    {
        lv_obj_delete(self->msgbox);
        self->msgbox = NULL;
    }

    lv_clear_screen(true);
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_alert_del_obj, picoware_lvgl_alert_del);

void picoware_lvgl_alert_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        switch (attribute)
        {
        case MP_QSTR_text:
            destination[0] = picoware_lvgl_alert_get_text(self_in);
            break;
        case MP_QSTR_text_color:
            destination[0] = mp_obj_new_int(self->text_color_565);
            break;
        case MP_QSTR_background_color:
            destination[0] = mp_obj_new_int(self->background_color_565);
            break;
        case MP_QSTR_is_circular:
            destination[0] = mp_obj_new_bool(self->is_circular);
            break;
        case MP_QSTR__del__:
            destination[0] = MP_OBJ_FROM_PTR(&picoware_lvgl_alert_del_obj);
            break;
        default:
            return; // Fail
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    { // Store attributes
        switch (attribute)
        {
        case MP_QSTR_text:
            picoware_lvgl_alert_set_text(self_in, destination[1]);
            break;
        case MP_QSTR_text_color:
            self->text_color_565 = mp_obj_get_int(destination[1]);
            break;
        case MP_QSTR_background_color:
            self->background_color_565 = mp_obj_get_int(destination[1]);
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

// Alert.clear() - Clear display with background color
mp_obj_t picoware_lvgl_alert_clear(mp_obj_t self_in)
{
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        return mp_const_none;
    }

    // Delete msgbox if exists
    if (self->msgbox)
    {
        lv_obj_delete(self->msgbox);
        self->msgbox = NULL;
    }

    lv_clear_screen(true);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_alert_clear_obj, picoware_lvgl_alert_clear);

// Alert.draw(title) - Draw the alert with title
mp_obj_t picoware_lvgl_alert_draw(mp_obj_t self_in, mp_obj_t title_in)
{
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *title = mp_obj_str_get_str(title_in);

    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    if (!self->msgbox)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Message box not initialized"));
    }

    // Clear screen
    lv_clear_screen(false);

    // Update the title in the existing msgbox
    lv_msgbox_add_title(self->msgbox, title);

    // Show the message box
    lv_obj_clear_flag(self->msgbox, LV_OBJ_FLAG_HIDDEN);

    lv_obj_update_layout(self->msgbox);

    // Scroll the content area to the bottom
    lv_obj_t *content = lv_msgbox_get_content(self->msgbox);
    if (content)
    {
        lv_obj_scroll_to_y(content, LV_COORD_MAX, LV_ANIM_OFF);
    }

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_alert_draw_obj, picoware_lvgl_alert_draw);

mp_obj_t picoware_lvgl_alert_get_text(mp_obj_t self_in)
{
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->msgbox)
    {
        lv_obj_t *content = lv_msgbox_get_content(self->msgbox);
        if (content)
        {
            // Assuming the first child of content is the label with the text
            lv_obj_t *text_label = lv_obj_get_child(content, 0);
            if (text_label)
            {
                const char *text = lv_label_get_text(text_label);
                return mp_obj_new_str(text, strlen(text));
            }
        }
    }
    return mp_obj_new_str("", 0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_alert_get_text_obj, picoware_lvgl_alert_get_text);

mp_obj_t picoware_lvgl_alert_set_text(mp_obj_t self_in, mp_obj_t text_in)
{
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *new_text = mp_obj_str_get_str(text_in);

    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    if (!self->msgbox)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Message box not initialized"));
    }

    // Update the text in the existing msgbox
    lv_obj_t *content = lv_msgbox_get_content(self->msgbox);
    if (content)
    {
        // Assuming the first child of content is the label with the text
        lv_obj_t *text_label = lv_obj_get_child(content, 0);
        if (text_label)
        {
            lv_label_set_text(text_label, new_text);
        }
    }

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_alert_set_text_obj, picoware_lvgl_alert_set_text);

// Alert class method table
static const mp_rom_map_elem_t picoware_lvgl_alert_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&picoware_lvgl_alert_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw), MP_ROM_PTR(&picoware_lvgl_alert_draw_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_text), MP_ROM_PTR(&picoware_lvgl_alert_get_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_text), MP_ROM_PTR(&picoware_lvgl_alert_set_text_obj)},
};
static MP_DEFINE_CONST_DICT(picoware_lvgl_alert_locals_dict, picoware_lvgl_alert_locals_dict_table);

// Alert class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_alert_type,
    MP_QSTR_Alert,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, picoware_lvgl_alert_print,
    make_new, picoware_lvgl_alert_make_new,
    attr, picoware_lvgl_alert_attr,
    locals_dict, &picoware_lvgl_alert_locals_dict);
