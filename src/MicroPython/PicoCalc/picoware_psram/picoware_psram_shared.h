#pragma once
#if defined(PICOCALC_ESP32_P4)
#include "psram_qspi_esp32.h"
#define PICOWARE_PSRAM_INIT() psram_qspi_init(NULL, -1, 1.0f)
#else
#include "psram_qspi.h"
#define PICOWARE_PSRAM_INIT() psram_qspi_init(pio1, -1, 1.0f)
#endif
#include "picoware_psram.h"

#define PSRAM_SIZE (8 * 1024 * 1024) // PicoCalc's external 8 MiB PSRAM

#ifndef DISPLAY_WIDTH
#define DISPLAY_WIDTH 320
#endif
#ifndef DISPLAY_HEIGHT
#define DISPLAY_HEIGHT 320
#endif

// PSRAM framebuffer configuration
#define PSRAM_FRAMEBUFFER_ADDR 0x000000 // PSRAM start address
#if defined(PICOCALC_ESP32_P4)
#define PICOWARE_FRAMEBUFFER_PIXEL_BYTES 2
#else
#define PICOWARE_FRAMEBUFFER_PIXEL_BYTES 1
#endif
#define PSRAM_ROW_SIZE (DISPLAY_WIDTH * PICOWARE_FRAMEBUFFER_PIXEL_BYTES)
#define PSRAM_BUFFER_SIZE (DISPLAY_WIDTH * DISPLAY_HEIGHT * PICOWARE_FRAMEBUFFER_PIXEL_BYTES)
#define PSRAM_HEAP_START_ADDR (PSRAM_FRAMEBUFFER_ADDR + PSRAM_BUFFER_SIZE + 1024)

#if defined(PICOCALC_ESP32_P4)
#define PSRAM_CHUNK_SIZE 4092
#else
// Keep transfers below the RP PIO driver's 8-bit nibble-count limit.
#define PSRAM_CHUNK_SIZE 120
#endif

extern bool psram_initialized;
extern psram_qspi_inst_t psram_instance;
extern uint32_t psram_next_free_addr;
