/*
 * Picoware LCD Header
 * Copyright © 2026 JBlanked
 */

#pragma once

#include <stdint.h>
#include "../picoware_psram/psram_qspi.h"

// Display constants
#define DISPLAY_WIDTH 320
#define DISPLAY_HEIGHT 320
#define PALETTE_SIZE 256
#define FONT_WIDTH 5
#define FONT_HEIGHT 8
#define CHAR_WIDTH 6 // Including spacing
#define CHAR_HEIGHT 8

// External PSRAM instance access
extern psram_qspi_inst_t *picoware_get_psram_instance(void);

// Inline helper to write pixel to PSRAM framebuffer
extern void picoware_write_pixel_fb(psram_qspi_inst_t *psram, int x, int y, uint8_t color_index);

// Batch write buffer to framebuffer
extern void picoware_write_buffer_fb(psram_qspi_inst_t *psram, int x, int y, int width, int height, const uint8_t *buffer);

// Batch write 16-bit RGB565 buffer to framebuffer (for LVGL) - converts to RGB332
extern void picoware_write_buffer_fb_16(psram_qspi_inst_t *psram, int x, int y, int width, int height, const uint16_t *buffer);

extern void picoware_lcd_swap_region(uint16_t x, uint16_t y, uint16_t width, uint16_t height);
