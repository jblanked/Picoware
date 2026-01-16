/*
 * Picoware LCD Header for external module access
 * PSRAM framebuffer access functions
 */

#ifndef PICOWARE_LCD_SHARED_H
#define PICOWARE_LCD_SHARED_H

#include <stdint.h>
#include "../picoware_psram/psram_qspi.h"

// Display constants
#define DISPLAY_WIDTH 320
#define DISPLAY_HEIGHT 320

// PSRAM framebuffer configuration
#define PSRAM_FRAMEBUFFER_ADDR 0x400000 // 4MB offset in PSRAM
#define PSRAM_ROW_SIZE (DISPLAY_WIDTH)  // 320 bytes per row

// External PSRAM instance access
extern psram_qspi_inst_t *picoware_get_psram_instance(void);

// Inline helper to write pixel to PSRAM framebuffer
void picoware_write_pixel_fb(psram_qspi_inst_t *psram, int x, int y, uint8_t color_index);

#endif // PICOWARE_LCD_SHARED_H
