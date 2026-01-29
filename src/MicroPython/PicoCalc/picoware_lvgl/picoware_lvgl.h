/*
 * Picoware LVGL Header
 * Copyright © 2026 JBlanked
 */

#pragma once
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

#ifndef STATIC
#define STATIC static
#endif

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

// LVGL Display buffer - 16-bit RGB565
extern lv_display_t *lvgl_display;

#define LVGL_BACKGROUND_COLOR 0x0000

// clear the screen with specified color
extern void lv_clear_screen(bool use_object);
extern mp_obj_t picoware_lvgl_clear_screen(mp_obj_t use_object);