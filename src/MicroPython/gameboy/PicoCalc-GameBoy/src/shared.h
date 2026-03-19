#pragma once
#include "config.h"
#include <stdint.h>
#include "debug.h"

#ifndef PALETTE_T_DEFINED
#define PALETTE_T_DEFINED
typedef uint16_t palette_t[3][4];
#endif

#if ENABLE_SOUND
#include "minigb_apu.h"
extern struct minigb_apu_ctx apu_ctx;
#undef audio_read
#undef audio_write
#define audio_read(a) audio_read(&apu_ctx, (a))
#define audio_write(a, v) audio_write(&apu_ctx, (a), (v));
#endif

/**
 * ROM Storage Configuration
 *
 * Defines a region in flash memory to store the Game Boy ROM.
 * We erase and reprogram a region 1MB from the start of flash memory.
 * Once done, we access this at XIP_BASE + 1MB.
 * Game Boy DMG ROM sizes range from 32KB (e.g. Tetris) to 1MB (e.g. Pokemod Red)
 */
#define FLASH_TARGET_OFFSET ROM_STORAGE_OFFSET  // legacy alias; prefer ROM_STORAGE_OFFSET
extern uint8_t pixels_buffer[FRAME_BUFF_WIDTH]; // Line buffer for LCD rendering
extern palette_t palette;                       // Current color palette
extern uint8_t manual_palette_selected;         // Index of manually selected palette
extern int lcd_line_busy;                       // Flag for LCD line rendering status