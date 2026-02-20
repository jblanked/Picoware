#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "stdio.h"
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

#include "picoware_psram_shared.h"
#include "picoware_lvgl.h"
#include "../picoware_lcd/picoware_lcd.h"

// GUIs
#include "picoware_lvgl_alert.h"
#include "picoware_lvgl_choice.h"
#include "picoware_lvgl_list.h"
#include "picoware_lvgl_loading.h"
#include "picoware_lvgl_textbox.h"
#include "picoware_lvgl_toggle.h"

// LVGL Display buffer - 16-bit RGB565
lv_display_t *lvgl_display = NULL;
static lv_color_t draw_buf[DISPLAY_WIDTH * 10] __attribute__((aligned(64)));

// Module state
static bool lvgl_initialized = false;
static psram_qspi_inst_t *psram_inst = NULL;

void lv_clear_screen(bool use_object)
{
    if (lvgl_display)
    {
        if (use_object)
        {
            lv_obj_t *black_screen = lv_obj_create(NULL);
            lv_screen_load(black_screen);
        }
        lv_obj_set_style_bg_color(lv_screen_active(), lv_color_from_rgb565(LVGL_BACKGROUND_COLOR), LV_PART_MAIN);
    }
}

mp_obj_t picoware_lvgl_clear_screen(mp_obj_t use_object)
{
    bool use_obj = mp_obj_is_true(use_object);
    lv_clear_screen(use_obj);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_clear_screen_obj, picoware_lvgl_clear_screen);

// flush callback
static void lvgl_flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    if (!psram_inst)
    {
        lv_display_flush_ready(disp);
        return;
    }

    int32_t width = area->x2 - area->x1 + 1;
    int32_t height = area->y2 - area->y1 + 1;
    uint16_t *color_p = (uint16_t *)px_map;

    // batch write
    picoware_write_buffer_fb_16(psram_inst, area->x1, area->y1, width, height, color_p);

    // send to display
    picoware_lcd_swap_region(area->x1, area->y1, width, height);

    // inform LVGL that flushing is done
    lv_display_flush_ready(disp);
}

// deinit
STATIC mp_obj_t picoware_lvgl_deinit(void)
{
    if (lvgl_initialized)
    {
        lv_clear_screen(false);

        if (lvgl_display)
        {
            lv_display_delete(lvgl_display);
            lvgl_display = NULL;
        }

        lv_deinit();

        lvgl_initialized = false;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lvgl_deinit_obj, picoware_lvgl_deinit);

// Module init function
STATIC mp_obj_t picoware_lvgl_init(void)
{
    if (lvgl_initialized)
    {
        return mp_const_none;
    }

    // Get PSRAM instance
    psram_inst = picoware_get_psram_instance();
    if (!psram_inst)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to get PSRAM instance"));
    }

    // Initialize LVGL
    lv_init();

    // Create display
    lvgl_display = lv_display_create(DISPLAY_WIDTH, DISPLAY_HEIGHT);
    if (!lvgl_display)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to create LVGL display"));
    }
    lv_display_set_color_format(lvgl_display, LV_COLOR_FORMAT_RGB565);
    lv_display_set_flush_cb(lvgl_display, lvgl_flush_cb);
    lv_display_set_buffers(lvgl_display, draw_buf, NULL, sizeof(draw_buf), LV_DISPLAY_RENDER_MODE_PARTIAL);

    lvgl_initialized = true;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lvgl_init_obj, picoware_lvgl_init);

// Module tick function
STATIC mp_obj_t picoware_lvgl_tick(mp_obj_t ms_in)
{
    uint32_t ms = mp_obj_get_int(ms_in);
    lv_tick_inc(ms);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lvgl_tick_obj, picoware_lvgl_tick);

// Module task handler
STATIC mp_obj_t picoware_lvgl_task_handler(void)
{
    if (lvgl_initialized)
    {
        lv_task_handler();
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lvgl_task_handler_obj, picoware_lvgl_task_handler);

STATIC const mp_rom_map_elem_t picoware_lvgl_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_lvgl)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_lvgl_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_lvgl_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_tick), MP_ROM_PTR(&picoware_lvgl_tick_obj)},
    {MP_ROM_QSTR(MP_QSTR_task_handler), MP_ROM_PTR(&picoware_lvgl_task_handler_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_screen), MP_ROM_PTR(&picoware_lvgl_clear_screen_obj)},
    {MP_ROM_QSTR(MP_QSTR_Alert), MP_ROM_PTR(&picoware_lvgl_alert_type)},
    {MP_ROM_QSTR(MP_QSTR_Choice), MP_ROM_PTR(&picoware_lvgl_choice_type)},
    {MP_ROM_QSTR(MP_QSTR_List), MP_ROM_PTR(&picoware_lvgl_list_type)},
    {MP_ROM_QSTR(MP_QSTR_Loading), MP_ROM_PTR(&picoware_lvgl_loading_type)},
    {MP_ROM_QSTR(MP_QSTR_TextBox), MP_ROM_PTR(&picoware_lvgl_textbox_type)},
    {MP_ROM_QSTR(MP_QSTR_Toggle), MP_ROM_PTR(&picoware_lvgl_toggle_type)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lvgl_module_globals, picoware_lvgl_module_globals_table);

const mp_obj_module_t picoware_lvgl_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_lvgl_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_picoware_lvgl, picoware_lvgl_user_cmodule);
