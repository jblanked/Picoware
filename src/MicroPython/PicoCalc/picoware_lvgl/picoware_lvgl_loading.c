#include "picoware_lvgl_loading.h"

const mp_obj_type_t picoware_lvgl_loading_type;

void picoware_lvgl_loading_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    picoware_lvgl_loading_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Loading(spinner_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->spinner_color_565), PRINT_REPR);
    mp_print_str(print, ", background_color=");
    mp_obj_print_helper(print, mp_obj_new_int(self->background_color_565), PRINT_REPR);
    mp_print_str(print, ", animating=");
    mp_print_str(print, self->animating ? "True" : "False");
    mp_print_str(print, ")");
}

// Loading constructor
mp_obj_t picoware_lvgl_loading_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 2, false);

    picoware_lvgl_loading_obj_t *self = mp_obj_malloc_with_finaliser(picoware_lvgl_loading_obj_t, &picoware_lvgl_loading_type);
    self->base.type = type;

    // Get optional spinner_color (default: white 0xFFFF)
    if (n_args > 0)
    {
        self->spinner_color_565 = mp_obj_get_int(args[0]);
    }
    else
    {
        self->spinner_color_565 = 0xFFFF;
    }

    // Get optional background_color (default: black 0x0000)
    if (n_args > 1)
    {
        self->background_color_565 = mp_obj_get_int(args[1]);
    }
    else
    {
        self->background_color_565 = 0x0000;
    }

    // Initialize state
    self->animating = false;
    self->time_start = 0;
    self->time_elapsed = 0;

    // Initialize LVGL objects
    self->spinner = NULL;
    self->text_label = NULL;
    self->time_label = NULL;

    lv_clear_screen(true);

    // Create LVGL objects immediately if display is available
    if (lvgl_display)
    {
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);

        // Create text label (hidden initially)
        self->text_label = lv_label_create(screen);
        lv_label_set_text(self->text_label, "Loading...");
        lv_obj_set_style_text_color(self->text_label, lv_color_from_rgb565(self->spinner_color_565), LV_PART_MAIN);
        lv_obj_set_style_text_font(self->text_label, &lv_font_montserrat_12, LV_PART_MAIN);
        lv_obj_add_flag(self->text_label, LV_OBJ_FLAG_HIDDEN);

        // Create time label (hidden initially)
        self->time_label = lv_label_create(screen);
        lv_label_set_text(self->time_label, "0 second");
        lv_obj_set_style_text_color(self->time_label, lv_color_from_rgb565(self->spinner_color_565), LV_PART_MAIN);
        lv_obj_set_style_text_font(self->time_label, &lv_font_montserrat_12, LV_PART_MAIN);
        lv_obj_add_flag(self->time_label, LV_OBJ_FLAG_HIDDEN);

        // Create spinner (hidden initially)
        self->spinner = lv_spinner_create(screen);
        lv_obj_set_size(self->spinner, 80, 80);
        lv_obj_center(self->spinner);

        // Style the spinner
        lv_obj_set_style_arc_color(self->spinner, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
        lv_obj_set_style_arc_opa(self->spinner, LV_OPA_30, LV_PART_MAIN);
        lv_obj_set_style_arc_width(self->spinner, 8, LV_PART_MAIN);
        lv_obj_set_style_arc_color(self->spinner, lv_color_from_rgb565(self->spinner_color_565), LV_PART_INDICATOR);
        lv_obj_set_style_arc_width(self->spinner, 8, LV_PART_INDICATOR);
        lv_obj_set_style_arc_rounded(self->spinner, true, LV_PART_INDICATOR);
        lv_obj_add_flag(self->spinner, LV_OBJ_FLAG_HIDDEN);
    }
    self->freed = false;
    return MP_OBJ_FROM_PTR(self);
}

// Loading destructor
mp_obj_t picoware_lvgl_loading_del(mp_obj_t self_in)
{
    picoware_lvgl_loading_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none;
    }
    // Clean up LVGL objects
    if (lvgl_display)
    {
        if (self->spinner)
        {
            lv_obj_delete(self->spinner);
            self->spinner = NULL;
        }
        if (self->text_label)
        {
            lv_obj_delete(self->text_label);
            self->text_label = NULL;
        }
        if (self->time_label)
        {
            lv_obj_delete(self->time_label);
            self->time_label = NULL;
        }
    }

    self->animating = false;

    // Clear screen
    lv_clear_screen(true);
    self->freed = true;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_loading_del_obj, picoware_lvgl_loading_del);

void picoware_lvgl_loading_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    if (destination[0] == MP_OBJ_NULL)
    {
        // Load attributes
        switch (attribute)
        {
        case MP_QSTR_text:
            destination[0] = picoware_lvgl_loading_get_text(self_in);
            break;
        case MP_QSTR__del__:
            destination[0] = MP_OBJ_FROM_PTR(&picoware_lvgl_loading_del_obj);
            break;
        default:
            return; // Fail
        };
    }
    else
    {
        // Store attributes
        switch (attribute)
        {
        case MP_QSTR_text:
            picoware_lvgl_loading_set_text(self_in, destination[1]);
            break;
        default:
            return; // Fail
        };
        destination[0] = MP_OBJ_NULL;
    }
}

// Loading.text property getter
mp_obj_t picoware_lvgl_loading_get_text(mp_obj_t self_in)
{
    picoware_lvgl_loading_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->text_label)
    {
        const char *text = lv_label_get_text(self->text_label);
        return mp_obj_new_str(text, strlen(text));
    }
    return mp_obj_new_str("Loading...", 10);
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_loading_get_text_obj, picoware_lvgl_loading_get_text);

// Loading.text property setter
mp_obj_t picoware_lvgl_loading_set_text(mp_obj_t self_in, mp_obj_t value)
{
    picoware_lvgl_loading_obj_t *self = MP_OBJ_TO_PTR(self_in);
    const char *new_text = mp_obj_str_get_str(value);

    // Update label if it exists
    if (self->text_label)
    {
        lv_label_set_text(self->text_label, new_text);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(picoware_lvgl_loading_set_text_obj, picoware_lvgl_loading_set_text);

// Loading.animate(swap=True) - Animate the loading spinner
mp_obj_t picoware_lvgl_loading_animate(size_t n_args, const mp_obj_t *args)
{
    picoware_lvgl_loading_obj_t *self = MP_OBJ_TO_PTR(args[0]);

    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("LVGL display not available"));
    }

    lv_clear_screen(false);

    // Get swap parameter (default: True)
    bool swap = (n_args > 1) ? mp_obj_is_true(args[1]) : true;

    // Start timing if not already animating
    if (!self->animating)
    {
        self->animating = true;
        self->time_start = mp_hal_ticks_ms();

        // Clear screen before showing loading elements
        lv_obj_t *screen = lv_disp_get_scr_act(lvgl_display);
        lv_obj_set_style_bg_color(screen, lv_color_from_rgb565(self->background_color_565), LV_PART_MAIN);
        lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, LV_PART_MAIN);
    }

    // Calculate elapsed time
    self->time_elapsed = mp_hal_ticks_ms() - self->time_start;

    // Show and position UI elements
    if (self->spinner)
    {
        lv_obj_clear_flag(self->spinner, LV_OBJ_FLAG_HIDDEN);
        lv_obj_center(self->spinner);
    }

    if (self->text_label)
    {
        lv_obj_clear_flag(self->text_label, LV_OBJ_FLAG_HIDDEN);
        if (self->spinner)
        {
            lv_obj_align_to(self->text_label, self->spinner, LV_ALIGN_OUT_TOP_MID, 0, -20);
        }
    }

    if (self->time_label)
    {
        lv_obj_clear_flag(self->time_label, LV_OBJ_FLAG_HIDDEN);
        if (self->spinner)
        {
            lv_obj_align_to(self->time_label, self->spinner, LV_ALIGN_OUT_BOTTOM_MID, 0, 20);
        }
    }

    // Update time label
    if (self->time_label)
    {
        uint32_t seconds = self->time_elapsed / 1000;
        char time_str[32];

        if (seconds < 60)
        {
            if (seconds <= 1)
            {
                snprintf(time_str, sizeof(time_str), "%lu second", (unsigned long)seconds);
            }
            else
            {
                snprintf(time_str, sizeof(time_str), "%lu seconds", (unsigned long)seconds);
            }
        }
        else
        {
            uint32_t minutes = seconds / 60;
            uint32_t remaining_seconds = seconds % 60;
            snprintf(time_str, sizeof(time_str), "%lu:%02lu minutes", (unsigned long)minutes, (unsigned long)remaining_seconds);
        }

        lv_label_set_text(self->time_label, time_str);
    }

    // Refresh display if swap is requested
    if (swap)
    {
        lv_refr_now(lvgl_display);
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lvgl_loading_animate_obj, 1, 2, picoware_lvgl_loading_animate);

// Loading.stop() - Stop the loading animation
mp_obj_t picoware_lvgl_loading_stop(mp_obj_t self_in)
{
    picoware_lvgl_loading_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (!lvgl_display)
    {
        return mp_const_none;
    }

    // Hide LVGL objects
    if (self->spinner)
    {
        lv_obj_add_flag(self->spinner, LV_OBJ_FLAG_HIDDEN);
    }
    if (self->text_label)
    {
        lv_obj_add_flag(self->text_label, LV_OBJ_FLAG_HIDDEN);
    }
    if (self->time_label)
    {
        lv_obj_add_flag(self->time_label, LV_OBJ_FLAG_HIDDEN);
    }

    // Reset state
    self->animating = false;
    self->time_elapsed = 0;
    self->time_start = 0;

    // Refresh display
    lv_refr_now(lvgl_display);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_loading_stop_obj, picoware_lvgl_loading_stop);

// Loading class method table
static const mp_rom_map_elem_t picoware_lvgl_loading_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_animate), MP_ROM_PTR(&picoware_lvgl_loading_animate_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_text), MP_ROM_PTR(&picoware_lvgl_loading_get_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_text), MP_ROM_PTR(&picoware_lvgl_loading_set_text_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&picoware_lvgl_loading_stop_obj)},
};
static MP_DEFINE_CONST_DICT(picoware_lvgl_loading_locals_dict, picoware_lvgl_loading_locals_dict_table);

// Loading class type definition
MP_DEFINE_CONST_OBJ_TYPE(
    picoware_lvgl_loading_type,
    MP_QSTR_Loading,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, picoware_lvgl_loading_print,
    make_new, picoware_lvgl_loading_make_new,
    attr, picoware_lvgl_loading_attr,
    locals_dict, &picoware_lvgl_loading_locals_dict);
