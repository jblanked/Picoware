/*
 * Picoware LVGL Alert Header
 * Copyright © 2026 JBlanked
 */

#include "picoware_lvgl.h"

typedef struct
{
    mp_obj_base_t base;
    uint16_t text_color_565;
    uint16_t background_color_565;
    bool is_circular;
    lv_obj_t *msgbox;
} picoware_lvgl_alert_obj_t;

const mp_obj_type_t picoware_lvgl_alert_type;

// Alert constructor
STATIC mp_obj_t picoware_lvgl_alert_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
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
STATIC mp_obj_t picoware_lvgl_alert_del(mp_obj_t self_in)
{
    picoware_lvgl_alert_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Clean up LVGL objects
    if (self->msgbox)
    {
        lv_obj_delete(self->msgbox);
        self->msgbox = NULL;
    }

    lv_clear_screen(true);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_alert_del_obj, picoware_lvgl_alert_del);

// Alert.clear() - Clear display with background color
STATIC mp_obj_t picoware_lvgl_alert_clear(mp_obj_t self_in)
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
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_alert_clear_obj, picoware_lvgl_alert_clear);

// Alert.draw(title) - Draw the alert with title
STATIC mp_obj_t picoware_lvgl_alert_draw(mp_obj_t self_in, mp_obj_t title_in)
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
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_alert_draw_obj, picoware_lvgl_alert_draw);

// Alert class method table
STATIC const mp_rom_map_elem_t picoware_lvgl_alert_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_clear), MP_ROM_PTR(&picoware_lvgl_alert_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw), MP_ROM_PTR(&picoware_lvgl_alert_draw_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&picoware_lvgl_alert_del_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_lvgl_alert_del_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lvgl_alert_locals_dict, picoware_lvgl_alert_locals_dict_table);

// Alert class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_alert_type,
    MP_QSTR_Alert,
    MP_TYPE_FLAG_NONE,
    make_new, picoware_lvgl_alert_make_new,
    locals_dict, &picoware_lvgl_alert_locals_dict);
