#pragma once

// general
#define ENGINE_MAX_TRIANGLES_PER_SPRITE 2048

// logging
#define ENGINE_LOG_INCLUDE "../log/log_mp.h"
#define ENGINE_LOG_INFO(...) LOG_MESSAGE(__VA_ARGS__)

// memory
#if defined(PICOCALC)
#define ENGINE_MEM_INCLUDE "../../engine/memory.h"
#elif defined(CARDPUTER) || defined(WAVESHARE_2_06)
#define ENGINE_MEM_INCLUDE "../engine/memory.h"
#else
#define ENGINE_MEM_INCLUDE "../../../engine/memory.h"
#endif
#include ENGINE_MEM_INCLUDE
#define ENGINE_MEM_NEW new
#define ENGINE_MEM_DELETE delete
#define ENGINE_MEM_MALLOC m_malloc
#define ENGINE_MEM_FREE m_free

// delay
#if defined(CARDPUTER) || defined(ESP32) || defined(CROWPANEL_10_1) || defined(WAVESHARE_2_06)
#define ENGINE_DELAY_INCLUDE "freertos/FreeRTOS.h"
#define ENGINE_DELAY_MS(ms) vTaskDelay(pdMS_TO_TICKS(ms))
#else
#define ENGINE_DELAY_INCLUDE "py/runtime.h"
#define ENGINE_DELAY_MS(ms) sleep_ms(ms)
#endif

// font
#if defined(PICOCALC)
#define ENGINE_FONT_INCLUDE "../../font/font.h"
#elif defined(CARDPUTER)
#define ENGINE_FONT_INCLUDE "../font/font.h"
#else
#define ENGINE_FONT_INCLUDE "../../../font/font.h"
#endif
#define ENGINE_FONT_SIZE FontSize
#define ENGINE_FONT_DEFAULT FONT_SIZE_SMALL

// LCD
#include "../lcd/lcd_config.h"
#define ENGINE_LCD_INCLUDE LCD_INCLUDE
#define ENGINE_LCD_WIDTH LCD_MP_WIDTH
#define ENGINE_LCD_HEIGHT LCD_MP_HEIGHT
#define ENGINE_LCD_CHAR LCD_MP_CHAR
#define ENGINE_LCD_CIRCLE LCD_MP_CIRCLE
#define ENGINE_LCD_CLEAR LCD_MP_CLEAR
#define ENGINE_LCD_FILL_CIRCLE LCD_MP_FILL_CIRCLE
#define ENGINE_LCD_FILL_RECTANGLE LCD_MP_FILL_RECTANGLE
#define ENGINE_LCD_FILL_ROUND_RECTANGLE LCD_MP_FILL_ROUND_RECTANGLE
#define ENGINE_LCD_FILL_TRIANGLE LCD_MP_FILL_TRIANGLE
#define ENGINE_LCD_FILL_TRIANGLE_ALPHA LCD_MP_FILL_TRIANGLE_ALPHA
#define ENGINE_LCD_BLIT LCD_MP_BLIT
#define ENGINE_LCD_BLIT_16BIT LCD_MP_BLIT_16BIT
#define ENGINE_LCD_LINE LCD_MP_LINE
#define ENGINE_LCD_PIXEL LCD_MP_PIXEL
#define ENGINE_LCD_PSRAM LCD_MP_PSRAM
#define ENGINE_LCD_PSRAM_READ_ROW LCD_MP_PSRAM_READ_ROW
#define ENGINE_LCD_RECTANGLE LCD_MP_RECTANGLE
#define ENGINE_LCD_SET_MODE LCD_MP_SET_MODE
#define ENGINE_LCD_SWAP LCD_MP_SWAP
#define ENGINE_LCD_TEXT LCD_MP_TEXT
#define ENGINE_LCD_TRIANGLE LCD_MP_TRIANGLE

// storage
#if defined(PICOCALC)
#define ENGINE_STORAGE_INCLUDE "../../sd/storage.h"
#elif defined(CARDPUTER) || defined(WAVESHARE_2_06)
#define ENGINE_STORAGE_INCLUDE "../sd/storage.h"
#elif !defined(WAVESHARE_1_28)
#define ENGINE_STORAGE_INCLUDE "../../../sd/storage.h"
#endif
#ifdef ENGINE_STORAGE_INCLUDE
#define ENGINE_STORAGE_READ storage_file_read      // (const char *file_path, void *buffer, size_t buffer_size) -> size_t
#define ENGINE_STORAGE_WRITE storage_file_write    // (const char *file_path, const void *data, size_t data_size) -> bool
#define ENGINE_STORAGE_FILE_LIST storage_file_list // (const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count) -> uint16_t
#define ENGINE_STORAGE_SIZE storage_file_size      // (const char *file_path) -> size_t
#endif
