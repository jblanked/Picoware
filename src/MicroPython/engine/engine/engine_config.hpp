#pragma once

// memory
#if defined(PICOCALC)
#define ENGINE_MEM_INCLUDE "../../engine/memory.h"
#else
#define ENGINE_MEM_INCLUDE "../../../engine/memory.h"
#endif
#define ENGINE_MEM_NEW new
#define ENGINE_MEM_DELETE delete
#define ENGINE_MEM_MALLOC m_malloc
#define ENGINE_MEM_FREE m_free

// delay
#define ENGINE_DELAY_INCLUDE "py/mphal.h"
#define ENGINE_DELAY_MS(ms) mp_hal_delay_ms(ms)

// font
#if defined(PICOCALC)
#define ENGINE_FONT_INCLUDE "../../font/font.h"
#else
#define ENGINE_FONT_INCLUDE "../../../font/font.h"
#endif
#define ENGINE_FONT_SIZE FontSize
#define ENGINE_FONT_DEFAULT FONT_SMALL

// LCD
#if defined(PICOCALC)
#define ENGINE_LCD_INCLUDE "../PicoCalc/picoware_lcd/picoware_lcd.h"
#define ENGINE_LCD_INIT picocalc_lcd_init
#define ENGINE_LCD_DEINIT lcd_deinit
#define ENGINE_LCD_WIDTH DISPLAY_WIDTH
#define ENGINE_LCD_HEIGHT DISPLAY_HEIGHT
#define ENGINE_LCD_CHAR lcd_draw_char
#define ENGINE_LCD_CIRCLE lcd_draw_circle
#define ENGINE_LCD_CLEAR lcd_fill
#define ENGINE_LCD_FILL_CIRCLE lcd_fill_circle
#define ENGINE_LCD_FILL_RECTANGLE lcd_fill_rect
#define ENGINE_LCD_FILL_ROUND_RECTANGLE lcd_fill_round_rectangle
#define ENGINE_LCD_FILL_TRIANGLE lcd_fill_triangle
#define ENGINE_LCD_BLIT picocalc_lcd_blit
#define ENGINE_LCD_BLIT_16BIT lcd_blit_16bit
#define ENGINE_LCD_LINE lcd_draw_line
#define ENGINE_LCD_PIXEL lcd_draw_pixel
#define ENGINE_LCD_PSRAM lcd_psram
#define ENGINE_LCD_PSRAM_READ_ROW lcd_psram_read_row
#define ENGINE_LCD_RECTANGLE lcd_draw_rect
#define ENGINE_LCD_SET_MODE lcd_set_mode
#define ENGINE_LCD_SWAP lcd_swap
#define ENGINE_LCD_TEXT lcd_draw_text
#define ENGINE_LCD_TRIANGLE lcd_draw_triangle
#elif defined(WAVESHARE_1_28)
#define ENGINE_LCD_INCLUDE "../Waveshare/RP2350-Touch-LCD-1.28/waveshare_lcd/lcd.h"
#define ENGINE_LCD_INIT lcd_init
#define ENGINE_LCD_DEINIT lcd_reset
#define ENGINE_LCD_WIDTH LCD_WIDTH
#define ENGINE_LCD_HEIGHT LCD_HEIGHT
#define ENGINE_LCD_CHAR lcd_draw_char
#define ENGINE_LCD_CIRCLE lcd_draw_circle
#define ENGINE_LCD_CLEAR lcd_fill
#define ENGINE_LCD_FILL_CIRCLE lcd_fill_circle
#define ENGINE_LCD_FILL_RECTANGLE lcd_fill_rect
#define ENGINE_LCD_FILL_ROUND_RECTANGLE lcd_fill_round_rectangle
#define ENGINE_LCD_FILL_TRIANGLE lcd_fill_triangle
#define ENGINE_LCD_BLIT lcd_blit
#define ENGINE_LCD_BLIT_16BIT lcd_blit_16bit
#define ENGINE_LCD_LINE lcd_draw_line
#define ENGINE_LCD_PIXEL lcd_draw_pixel
#define ENGINE_LCD_RECTANGLE lcd_draw_rect
#define ENGINE_LCD_SWAP lcd_swap
#define ENGINE_LCD_TEXT lcd_draw_text
#define ENGINE_LCD_TRIANGLE lcd_draw_triangle
#elif defined(WAVESHARE_1_43)
#define ENGINE_LCD_INCLUDE "../Waveshare/RP2350-Touch-LCD-1.43/waveshare_lcd/lcd.h"
#define ENGINE_LCD_INIT lcd_init
#define ENGINE_LCD_DEINIT lcd_reset
#define ENGINE_LCD_WIDTH LCD_WIDTH
#define ENGINE_LCD_HEIGHT LCD_HEIGHT
#define ENGINE_LCD_CHAR lcd_draw_char
#define ENGINE_LCD_CIRCLE lcd_draw_circle
#define ENGINE_LCD_CLEAR lcd_fill
#define ENGINE_LCD_FILL_CIRCLE lcd_fill_circle
#define ENGINE_LCD_FILL_RECTANGLE lcd_fill_rect
#define ENGINE_LCD_FILL_ROUND_RECTANGLE lcd_fill_round_rectangle
#define ENGINE_LCD_FILL_TRIANGLE lcd_fill_triangle
#define ENGINE_LCD_BLIT lcd_blit
#define ENGINE_LCD_BLIT_16BIT lcd_blit_16bit
#define ENGINE_LCD_LINE lcd_draw_line
#define ENGINE_LCD_PIXEL lcd_draw_pixel
#define ENGINE_LCD_RECTANGLE lcd_draw_rect
#define ENGINE_LCD_SWAP lcd_swap
#define ENGINE_LCD_TEXT lcd_draw_text
#define ENGINE_LCD_TRIANGLE lcd_draw_triangle
#elif defined(WAVESHARE_3_49)
#define ENGINE_LCD_INCLUDE "../Waveshare/RP2350-Touch-LCD-3.49/waveshare_lcd/lcd.h"
#define ENGINE_LCD_INIT lcd_init
// #define ENGINE_LCD_DEINIT
#define ENGINE_LCD_WIDTH LCD_WIDTH
#define ENGINE_LCD_HEIGHT LCD_HEIGHT
#define ENGINE_LCD_CHAR lcd_draw_char
#define ENGINE_LCD_CIRCLE lcd_draw_circle
#define ENGINE_LCD_CLEAR lcd_fill
#define ENGINE_LCD_FILL_CIRCLE lcd_fill_circle
#define ENGINE_LCD_FILL_RECTANGLE lcd_fill_rect
#define ENGINE_LCD_FILL_ROUND_RECTANGLE lcd_fill_round_rectangle
#define ENGINE_LCD_FILL_TRIANGLE lcd_fill_triangle
#define ENGINE_LCD_BLIT lcd_blit
#define ENGINE_LCD_BLIT_16BIT lcd_blit_16bit
#define ENGINE_LCD_LINE lcd_draw_line
#define ENGINE_LCD_PIXEL lcd_draw_pixel
#define ENGINE_LCD_RECTANGLE lcd_draw_rect
#define ENGINE_LCD_SWAP lcd_swap
#define ENGINE_LCD_TEXT lcd_draw_text
#define ENGINE_LCD_TRIANGLE lcd_draw_triangle
#endif

// storage
#if defined(PICOCALC)
#define ENGINE_STORAGE_INCLUDE "../../engine/storage.h"
#elif !defined(WAVESHARE_1_28)
#define ENGINE_STORAGE_INCLUDE "../../../engine/storage.h"
#endif
#ifdef ENGINE_STORAGE_INCLUDE
#define ENGINE_STORAGE_READ storage_read // (const char *file_path, void *buffer, size_t buffer_size)
#endif