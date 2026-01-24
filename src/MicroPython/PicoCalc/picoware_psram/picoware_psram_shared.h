#pragma once
#include "psram_qspi.h"

#define PSRAM_SIZE (8 * 1024 * 1024) // 8MB PSRAM

#ifndef DISPLAY_WIDTH
#define DISPLAY_WIDTH 320
#endif
#ifndef DISPLAY_HEIGHT
#define DISPLAY_HEIGHT 320
#endif

// PSRAM framebuffer configuration
#define PSRAM_FRAMEBUFFER_ADDR 0x100000                                           // 1MB offset in PSRAM
#define PSRAM_ROW_SIZE (DISPLAY_WIDTH)                                            // 320 bytes per row (RGB332)
#define PSRAM_BUFFER_SIZE (DISPLAY_WIDTH * DISPLAY_HEIGHT)                        // 102,400 bytes
#define PSRAM_HEAP_START_ADDR (PSRAM_FRAMEBUFFER_ADDR + PSRAM_BUFFER_SIZE + 1024) // Start of heap area after framebuffer

// Chunk size must be <= 123 bytes to avoid uint8_t nibble count overflow
// Write: (4 + count) * 2 must fit in uint8_t -> count <= (255/2) - 4 = 123
// Read: count * 2 must fit in uint8_t -> count <= 127
// Use 64 for safety and efficiency (power of 2)
#define PSRAM_CHUNK_SIZE 64

extern bool psram_initialized;
extern psram_qspi_inst_t psram_instance;
