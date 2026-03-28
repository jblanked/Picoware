/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "py/objstr.h"
#include "py/objtype.h"
#include "stdio.h"
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

// LVGL includes
#include "lv_conf.h"
#include "lvgl/lvgl.h"

#if defined(PICOCALC)
#include "../../lcd/lcd_config.h"
#else
#include "../../../lcd/lcd_config.h"
#endif

#include LCD_INCLUDE

#ifndef DISPLAY_WIDTH
#define DISPLAY_WIDTH 320
#endif
#ifndef DISPLAY_HEIGHT
#define DISPLAY_HEIGHT 320
#endif

#ifndef LVGL_FONT_WIDTH
#define LVGL_FONT_WIDTH 12
#endif
#ifndef LVGL_FONT_HEIGHT
#define LVGL_FONT_HEIGHT 12
#endif

#ifndef LVGL_SPACING
#define LVGL_SPACING 3
#endif

#ifndef LVGL_LINE_HEIGHT
#define LVGL_LINE_HEIGHT (LVGL_FONT_HEIGHT + LVGL_SPACING)
#endif

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

// convert uint16_t color to lv_color_t
#define lv_color_from_rgb565(c) lv_color_make(((c) >> 8) & 0xF8, ((c) >> 3) & 0xFC, ((c) << 3) & 0xF8)

#define LVGL_BACKGROUND_COLOR 0x0000

    // LVGL Display buffer - 16-bit RGB565
    extern lv_display_t *lvgl_display;

    // clear the screen with specified color
    void lv_clear_screen(bool use_object);
    mp_obj_t picoware_lvgl_clear_screen(mp_obj_t use_object);

    // deinit
    mp_obj_t picoware_lvgl_deinit(void);

    // Module init function
    mp_obj_t picoware_lvgl_init(void);

    // Module tick function
    mp_obj_t picoware_lvgl_tick(mp_obj_t ms_in);

    // Module task handler
    mp_obj_t picoware_lvgl_task_handler(void);

#ifdef __cplusplus
}
#endif