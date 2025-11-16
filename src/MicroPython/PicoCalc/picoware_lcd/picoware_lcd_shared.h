/*
 * Picoware LCD Header for external module access
 */

#ifndef PICOWARE_LCD_SHARED_H
#define PICOWARE_LCD_SHARED_H

#include <stdint.h>

// Display constants
#define DISPLAY_WIDTH 320
#define DISPLAY_HEIGHT 320

// External framebuffer access
extern uint8_t static_framebuffer[DISPLAY_WIDTH * DISPLAY_HEIGHT];

#endif // PICOWARE_LCD_SHARED_H
