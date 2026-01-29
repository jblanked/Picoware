/*
 * Picoware LCD Native C Extension for MicroPython
 * Copyright © 2025 JBlanked
 *
 * Uses PSRAM for framebuffer storage instead of static RAM
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "lcd.h"
#include "picoware_lcd_shared.h"
#include "../picoware_psram/psram_qspi.h"
#include "../picoware_psram/picoware_psram_shared.h"
#include <stdlib.h>
#include <string.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

#define LCD_CHUNK_LINES 16

// Module state
static bool module_initialized = false;

// Line buffer for batch operations (reusable)
static uint8_t line_buffer[DISPLAY_WIDTH];

#define LCD_MODE_PSRAM 0 // PSRAM framebuffer with RGB332 palette
#define LCD_MODE_HEAP 1  // Heap RAM framebuffer with RGB332 (converted to RGB565 on swap)

static uint8_t lcd_mode = LCD_MODE_PSRAM;

// Heap mode state
static uint8_t *heap_framebuffer = NULL; // RGB332 framebuffer in heap RAM
static bool heap_framebuffer_allocated = false;
#define HEAP_BUFFER_SIZE (DISPLAY_WIDTH * DISPLAY_HEIGHT) // 102,400 bytes for RGB332

static uint16_t palette[256]; // 256-color palette for RGB332

// Convert RGB565 to RGB332 index
STATIC uint8_t color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

void picoware_write_pixel_fb(psram_qspi_inst_t *psram, int x, int y, uint8_t color_index)
{
    if (lcd_mode == LCD_MODE_PSRAM)
    {
        if (x >= 0 && x < DISPLAY_WIDTH && y >= 0 && y < DISPLAY_HEIGHT)
        {
            uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (y * PSRAM_ROW_SIZE) + x;
            psram_qspi_write8(psram, addr, color_index);
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP)
    {
        if (heap_framebuffer != NULL && x >= 0 && x < DISPLAY_WIDTH && y >= 0 && y < DISPLAY_HEIGHT)
        {
            heap_framebuffer[y * DISPLAY_WIDTH + x] = color_index;
        }
    }
}

// Batch write buffer to framebuffer (optimized batch write)
void picoware_write_buffer_fb(psram_qspi_inst_t *psram, int x, int y, int width, int height, const uint8_t *buffer)
{
    if (!buffer)
        return;

    for (int row = 0; row < height; row++)
    {
        int fb_y = y + row;
        if (fb_y < 0 || fb_y >= DISPLAY_HEIGHT)
            continue;

        for (int col = 0; col < width; col++)
        {
            int fb_x = x + col;
            if (fb_x < 0 || fb_x >= DISPLAY_WIDTH)
                continue;

            uint8_t color_index = buffer[row * width + col];
            picoware_write_pixel_fb(psram, fb_x, fb_y, color_index);
        }
    }
}

// Batch write 16-bit RGB565 buffer to framebuffer (for LVGL)
// Converts RGB565 to RGB332 on the fly
void picoware_write_buffer_fb_16(psram_qspi_inst_t *psram, int x, int y, int width, int height, const uint16_t *buffer)
{
    if (!buffer)
        return;

    for (int row = 0; row < height; row++)
    {
        int fb_y = y + row;
        if (fb_y < 0 || fb_y >= DISPLAY_HEIGHT)
            continue;

        for (int col = 0; col < width; col++)
        {
            int fb_x = x + col;
            if (fb_x < 0 || fb_x >= DISPLAY_WIDTH)
                continue;

            // Convert RGB565 to RGB332 using palette conversion
            uint16_t rgb565 = buffer[row * width + col];
            uint8_t rgb332 = color565_to_332(rgb565);
            picoware_write_pixel_fb(psram, fb_x, fb_y, rgb332);
        }
    }
}

// Get palette pointer for external access
uint16_t *picoware_get_palette(void)
{
    return palette;
}

static const uint8_t *get_font_data(void)
{
    static const uint8_t font_data[] = {
        0x00,
        0x00,
        0x00,
        0x00,
        0x00, // char 0
        0x3e,
        0x5b,
        0x4f,
        0x5b,
        0x3e, // char 1
        0x3e,
        0x6b,
        0x4f,
        0x6b,
        0x3e, // char 2
        0x1c,
        0x3e,
        0x7c,
        0x3e,
        0x1c, // char 3
        0x18,
        0x3c,
        0x7e,
        0x3c,
        0x18, // char 4
        0x1c,
        0x57,
        0x7d,
        0x57,
        0x1c, // char 5
        0x1c,
        0x5e,
        0x7f,
        0x5e,
        0x1c, // char 6
        0x00,
        0x18,
        0x3c,
        0x18,
        0x00, // char 7
        0xff,
        0xe7,
        0xc3,
        0xe7,
        0xff, // char 8
        0x00,
        0x18,
        0x24,
        0x18,
        0x00, // char 9
        0xff,
        0xe7,
        0xdb,
        0xe7,
        0xff, // char 10
        0x30,
        0x48,
        0x3a,
        0x06,
        0x0e, // char 11
        0x26,
        0x29,
        0x79,
        0x29,
        0x26, // char 12
        0x40,
        0x7f,
        0x05,
        0x05,
        0x07, // char 13
        0x40,
        0x7f,
        0x05,
        0x25,
        0x3f, // char 14
        0x5a,
        0x3c,
        0xe7,
        0x3c,
        0x5a, // char 15
        0x7f,
        0x3e,
        0x1c,
        0x1c,
        0x08, // char 16
        0x08,
        0x1c,
        0x1c,
        0x3e,
        0x7f, // char 17
        0x14,
        0x22,
        0x7f,
        0x22,
        0x14, // char 18
        0x5f,
        0x5f,
        0x00,
        0x5f,
        0x5f, // char 19
        0x06,
        0x09,
        0x7f,
        0x01,
        0x7f, // char 20
        0x00,
        0x66,
        0x89,
        0x95,
        0x6a, // char 21
        0x60,
        0x60,
        0x60,
        0x60,
        0x60, // char 22
        0x94,
        0xa2,
        0xff,
        0xa2,
        0x94, // char 23
        0x08,
        0x04,
        0x7e,
        0x04,
        0x08, // char 24
        0x10,
        0x20,
        0x7e,
        0x20,
        0x10, // char 25
        0x08,
        0x08,
        0x2a,
        0x1c,
        0x08, // char 26
        0x08,
        0x1c,
        0x2a,
        0x08,
        0x08, // char 27
        0x1e,
        0x10,
        0x10,
        0x10,
        0x10, // char 28
        0x0c,
        0x1e,
        0x0c,
        0x1e,
        0x0c, // char 29
        0x30,
        0x38,
        0x3e,
        0x38,
        0x30, // char 30
        0x06,
        0x0e,
        0x3e,
        0x0e,
        0x06, // char 31
        0x00,
        0x00,
        0x00,
        0x00,
        0x00, // ' ' (space)
        0x00,
        0x00,
        0x5f,
        0x00,
        0x00, // '!'
        0x00,
        0x07,
        0x00,
        0x07,
        0x00, // '"'
        0x14,
        0x7f,
        0x14,
        0x7f,
        0x14, // '#'
        0x24,
        0x2a,
        0x7f,
        0x2a,
        0x12, // '$'
        0x23,
        0x13,
        0x08,
        0x64,
        0x62, // '%'
        0x36,
        0x49,
        0x56,
        0x20,
        0x50, // '&'
        0x00,
        0x08,
        0x07,
        0x03,
        0x00, // '\''
        0x00,
        0x1c,
        0x22,
        0x41,
        0x00, // '('
        0x00,
        0x41,
        0x22,
        0x1c,
        0x00, // ')'
        0x2a,
        0x1c,
        0x7f,
        0x1c,
        0x2a, // '*'
        0x08,
        0x08,
        0x3e,
        0x08,
        0x08, // '+'
        0x00,
        0x80,
        0x70,
        0x30,
        0x00, // ','
        0x08,
        0x08,
        0x08,
        0x08,
        0x08, // '-'
        0x00,
        0x00,
        0x60,
        0x60,
        0x00, // '.'
        0x20,
        0x10,
        0x08,
        0x04,
        0x02, // '/'
        0x3e,
        0x51,
        0x49,
        0x45,
        0x3e, // '0'
        0x00,
        0x42,
        0x7f,
        0x40,
        0x00, // '1'
        0x72,
        0x49,
        0x49,
        0x49,
        0x46, // '2'
        0x21,
        0x41,
        0x49,
        0x4d,
        0x33, // '3'
        0x18,
        0x14,
        0x12,
        0x7f,
        0x10, // '4'
        0x27,
        0x45,
        0x45,
        0x45,
        0x39, // '5'
        0x3c,
        0x4a,
        0x49,
        0x49,
        0x31, // '6'
        0x41,
        0x21,
        0x11,
        0x09,
        0x07, // '7'
        0x36,
        0x49,
        0x49,
        0x49,
        0x36, // '8'
        0x46,
        0x49,
        0x49,
        0x29,
        0x1e, // '9'
        0x00,
        0x00,
        0x14,
        0x00,
        0x00, // ':'
        0x00,
        0x40,
        0x34,
        0x00,
        0x00, // ';'
        0x00,
        0x08,
        0x14,
        0x22,
        0x41, // '<'
        0x14,
        0x14,
        0x14,
        0x14,
        0x14, // '='
        0x00,
        0x41,
        0x22,
        0x14,
        0x08, // '>'
        0x02,
        0x01,
        0x59,
        0x09,
        0x06, // '?'
        0x3e,
        0x41,
        0x5d,
        0x59,
        0x4e, // '@'
        0x7c,
        0x12,
        0x11,
        0x12,
        0x7c, // 'A'
        0x7f,
        0x49,
        0x49,
        0x49,
        0x36, // 'B'
        0x3e,
        0x41,
        0x41,
        0x41,
        0x22, // 'C'
        0x7f,
        0x41,
        0x41,
        0x41,
        0x3e, // 'D'
        0x7f,
        0x49,
        0x49,
        0x49,
        0x41, // 'E'
        0x7f,
        0x09,
        0x09,
        0x09,
        0x01, // 'F'
        0x3e,
        0x41,
        0x41,
        0x51,
        0x73, // 'G'
        0x7f,
        0x08,
        0x08,
        0x08,
        0x7f, // 'H'
        0x00,
        0x41,
        0x7f,
        0x41,
        0x00, // 'I'
        0x20,
        0x40,
        0x41,
        0x3f,
        0x01, // 'J'
        0x7f,
        0x08,
        0x14,
        0x22,
        0x41, // 'K'
        0x7f,
        0x40,
        0x40,
        0x40,
        0x40, // 'L'
        0x7f,
        0x02,
        0x1c,
        0x02,
        0x7f, // 'M'
        0x7f,
        0x04,
        0x08,
        0x10,
        0x7f, // 'N'
        0x3e,
        0x41,
        0x41,
        0x41,
        0x3e, // 'O'
        0x7f,
        0x09,
        0x09,
        0x09,
        0x06, // 'P'
        0x3e,
        0x41,
        0x51,
        0x21,
        0x5e, // 'Q'
        0x7f,
        0x09,
        0x19,
        0x29,
        0x46, // 'R'
        0x26,
        0x49,
        0x49,
        0x49,
        0x32, // 'S'
        0x03,
        0x01,
        0x7f,
        0x01,
        0x03, // 'T'
        0x3f,
        0x40,
        0x40,
        0x40,
        0x3f, // 'U'
        0x1f,
        0x20,
        0x40,
        0x20,
        0x1f, // 'V'
        0x3f,
        0x40,
        0x38,
        0x40,
        0x3f, // 'W'
        0x63,
        0x14,
        0x08,
        0x14,
        0x63, // 'X'
        0x03,
        0x04,
        0x78,
        0x04,
        0x03, // 'Y'
        0x61,
        0x59,
        0x49,
        0x4d,
        0x43, // 'Z'
        0x00,
        0x7f,
        0x41,
        0x41,
        0x41, // '['
        0x02,
        0x04,
        0x08,
        0x10,
        0x20, // '\'
        0x00,
        0x41,
        0x41,
        0x41,
        0x7f, // ']'
        0x04,
        0x02,
        0x01,
        0x02,
        0x04, // '^'
        0x40,
        0x40,
        0x40,
        0x40,
        0x40, // '_'
        0x00,
        0x03,
        0x07,
        0x08,
        0x00, // '`'
        0x20,
        0x54,
        0x54,
        0x78,
        0x40, // 'a'
        0x7f,
        0x28,
        0x44,
        0x44,
        0x38, // 'b'
        0x38,
        0x44,
        0x44,
        0x44,
        0x28, // 'c'
        0x38,
        0x44,
        0x44,
        0x28,
        0x7f, // 'd'
        0x38,
        0x54,
        0x54,
        0x54,
        0x18, // 'e'
        0x00,
        0x08,
        0x7e,
        0x09,
        0x02, // 'f'
        0x18,
        0xa4,
        0xa4,
        0x9c,
        0x78, // 'g'
        0x7f,
        0x08,
        0x04,
        0x04,
        0x78, // 'h'
        0x00,
        0x44,
        0x7d,
        0x40,
        0x00, // 'i'
        0x20,
        0x40,
        0x40,
        0x3d,
        0x00, // 'j'
        0x7f,
        0x10,
        0x28,
        0x44,
        0x00, // 'k'
        0x00,
        0x41,
        0x7f,
        0x40,
        0x00, // 'l'
        0x7c,
        0x04,
        0x78,
        0x04,
        0x78, // 'm'
        0x7c,
        0x08,
        0x04,
        0x04,
        0x78, // 'n'
        0x38,
        0x44,
        0x44,
        0x44,
        0x38, // 'o'
        0xfc,
        0x18,
        0x24,
        0x24,
        0x18, // 'p'
        0x18,
        0x24,
        0x24,
        0x18,
        0xfc, // 'q'
        0x7c,
        0x08,
        0x04,
        0x04,
        0x08, // 'r'
        0x48,
        0x54,
        0x54,
        0x54,
        0x24, // 's'
        0x04,
        0x04,
        0x3f,
        0x44,
        0x24, // 't'
        0x3c,
        0x40,
        0x40,
        0x20,
        0x7c, // 'u'
        0x1c,
        0x20,
        0x40,
        0x20,
        0x1c, // 'v'
        0x3c,
        0x40,
        0x30,
        0x40,
        0x3c, // 'w'
        0x44,
        0x28,
        0x10,
        0x28,
        0x44, // 'x'
        0x4c,
        0x90,
        0x90,
        0x90,
        0x7c, // 'y'
        0x44,
        0x64,
        0x54,
        0x4c,
        0x44, // 'z'
        0x00,
        0x08,
        0x36,
        0x41,
        0x00, // '{'
        0x00,
        0x00,
        0x77,
        0x00,
        0x00, // '|'
        0x00,
        0x41,
        0x36,
        0x08,
        0x00, // '}'
        0x02,
        0x01,
        0x02,
        0x04,
        0x02, // '~'
        0x3c,
        0x26,
        0x23,
        0x26,
        0x3c, // char 127
    };
    return font_data;
}
static uint16_t lcd_color332_to_565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

// Helper to write a single pixel to PSRAM framebuffer
__force_inline static void psram_write_pixel(int x, int y, uint8_t color_index)
{
    if (x >= 0 && x < DISPLAY_WIDTH && y >= 0 && y < DISPLAY_HEIGHT)
    {
        uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (y * PSRAM_ROW_SIZE) + x;
        psram_qspi_write8(&psram_instance, addr, color_index);
    }
}

// Helper to write a horizontal line to PSRAM (optimized batch write)
__force_inline static void psram_write_hline(int x, int y, int length, uint8_t color_index)
{
    if (y < 0 || y >= DISPLAY_HEIGHT || length <= 0)
        return;

    // Clip to screen bounds
    if (x < 0)
    {
        length += x;
        x = 0;
    }
    if (x + length > DISPLAY_WIDTH)
    {
        length = DISPLAY_WIDTH - x;
    }
    if (length <= 0)
        return;

    uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (y * PSRAM_ROW_SIZE) + x;

    // Fill line buffer with color
    memset(line_buffer, color_index, length);

    // Write in chunks to PSRAM
    uint32_t remaining = length;
    uint32_t offset = 0;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, addr + offset, line_buffer + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

// Helper to allocate heap framebuffer
static bool allocate_heap_framebuffer(void)
{
    if (heap_framebuffer == NULL)
    {
        heap_framebuffer = (uint8_t *)m_malloc(HEAP_BUFFER_SIZE);
        if (heap_framebuffer == NULL)
        {
            return false;
        }
        memset(heap_framebuffer, 0, HEAP_BUFFER_SIZE);
        heap_framebuffer_allocated = true;
    }
    return true;
}

// Helper to free heap framebuffer
static void free_heap_framebuffer(void)
{
    if (heap_framebuffer != NULL && heap_framebuffer_allocated)
    {
        m_free(heap_framebuffer);
        heap_framebuffer = NULL;
        heap_framebuffer_allocated = false;
    }
}

static void clear_psram_framebuffer(uint8_t color_index)
{
    // Pack four pixels into a 32-bit value for DMA burst fill
    uint32_t fill_value = (color_index << 24) | (color_index << 16) | (color_index << 8) | color_index;

    // Calculate number of 32-bit words (BUFFER_SIZE / 4)
    uint32_t word_count = PSRAM_BUFFER_SIZE / 4;

    // Use 32-bit fill with chunked writes for optimal DMA performance
    static uint32_t fill32_buffer[PSRAM_CHUNK_SIZE / 4];

    // Fill the buffer with the 32-bit value
    for (size_t i = 0; i < PSRAM_CHUNK_SIZE / 4; i++)
    {
        fill32_buffer[i] = fill_value;
    }

    uint32_t current_addr = PSRAM_FRAMEBUFFER_ADDR;
    uint32_t remaining = word_count;

    while (remaining > 0)
    {
        uint32_t words_in_chunk = (remaining > (PSRAM_CHUNK_SIZE / 4)) ? (PSRAM_CHUNK_SIZE / 4) : remaining;
        psram_qspi_write(&psram_instance, current_addr, (const uint8_t *)fill32_buffer, words_in_chunk * 4);
        current_addr += words_in_chunk * 4;
        remaining -= words_in_chunk;
    }
}

// deinit function
STATIC mp_obj_t picoware_lcd_deinit(void)
{
    if (module_initialized)
    {
        // Free resources
        free_heap_framebuffer();

        if (psram_initialized)
        {
            psram_qspi_deinit(&psram_instance);
            psram_initialized = false;
        }

        module_initialized = false;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_deinit_obj, picoware_lcd_deinit);

// Function to initialize the LCD and framebuffer (PSRAM or HEAP mode)
// Arguments: background_color, [mode] (optional, 0=PSRAM, 1=HEAP)
STATIC mp_obj_t picoware_lcd_init(size_t n_args, const mp_obj_t *args)
{
    if (n_args < 1 || n_args > 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("init requires 1-2 arguments: background_color, [mode]"));
    }

    uint8_t requested_mode = LCD_MODE_PSRAM;
    if (n_args == 2)
    {
        requested_mode = mp_obj_get_int(args[1]);
        if (requested_mode > LCD_MODE_HEAP)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("Invalid mode: 0=PSRAM, 1=HEAP"));
        }
    }

    if (!module_initialized)
    {
        lcd_init();
        lcd_set_background(mp_obj_get_int(args[0]));
        lcd_set_underscore(false);
        lcd_enable_cursor(false);

        // Init palette (used for both modes)
        for (int i = 0; i < 256; i++)
        {
            // Extract RGB332 components
            uint8_t r3 = (i >> 5) & 0x07; // 3 bits for red
            uint8_t g3 = (i >> 2) & 0x07; // 3 bits for green
            uint8_t b2 = i & 0x03;        // 2 bits for blue

            // Convert to 8-bit RGB
            uint8_t r8 = (r3 * 255) / 7; // Scale 3-bit to 8-bit
            uint8_t g8 = (g3 * 255) / 7; // Scale 3-bit to 8-bit
            uint8_t b8 = (b2 * 255) / 3; // Scale 2-bit to 8-bit

            // Convert to RGB565 for the palette
            palette[i] = lcd_color332_to_565(r8, g8, b8);
        }

        module_initialized = true;
    }

    // Initialize mode-specific resources
    lcd_mode = requested_mode;

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        // Initialize PSRAM for framebuffer
        if (!psram_initialized)
        {
            psram_instance = psram_qspi_init(pio1, -1, 1.0f);
            psram_initialized = true;
        }
        // Free heap buffer if it was allocated
        free_heap_framebuffer();
    }
    else if (lcd_mode == LCD_MODE_HEAP)
    {
        // Allocate RGB332 framebuffer in heap RAM
        if (!allocate_heap_framebuffer())
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("Failed to allocate heap framebuffer"));
        }
        // Clear the framebuffer to black
        memset(heap_framebuffer, 0, HEAP_BUFFER_SIZE);

        if (psram_initialized)
        {
            clear_psram_framebuffer(0);
            psram_qspi_deinit(&psram_instance);
            psram_initialized = false;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_init_obj, 1, 2, picoware_lcd_init);

void picoware_lcd_swap_region(uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    uint16_t lcd_line_buffer[DISPLAY_WIDTH * LCD_CHUNK_LINES];

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        uint8_t psram_row_buffer[DISPLAY_WIDTH];

        // Send data line by line in chunks
        for (uint16_t row = 0; row < height; row += LCD_CHUNK_LINES)
        {
            uint16_t lines_to_send = (row + LCD_CHUNK_LINES > height) ? (height - row) : LCD_CHUNK_LINES;

            // Convert this chunk from RGB332 to RGB565 with byte swapping
            for (uint16_t line = 0; line < lines_to_send; line++)
            {
                // Read row from PSRAM
                uint32_t psram_addr = PSRAM_FRAMEBUFFER_ADDR + ((y + row + line) * PSRAM_ROW_SIZE) + x;
                uint32_t remaining = width;
                uint32_t offset = 0;

                while (remaining > 0)
                {
                    uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
                    psram_qspi_read(&psram_instance, psram_addr + offset, psram_row_buffer + offset, chunk_size);
                    offset += chunk_size;
                    remaining -= chunk_size;
                }

                // Convert to RGB565
                for (uint16_t col = 0; col < width; col++)
                {
                    size_t buf_index = line * width + col;
                    uint8_t palette_index = psram_row_buffer[col];
                    lcd_line_buffer[buf_index] = palette[palette_index];
                }
            }

            // Send to LCD
            lcd_blit(lcd_line_buffer, x, y + row, width, lines_to_send);
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP)
    {
        // Convert RGB332 heap buffer to RGB565 on the fly, just like PSRAM mode
        if (heap_framebuffer != NULL)
        {
            // Send data line by line in chunks
            for (uint16_t row = 0; row < height; row += LCD_CHUNK_LINES)
            {
                uint16_t lines_to_send = (row + LCD_CHUNK_LINES > height) ? (height - row) : LCD_CHUNK_LINES;

                // Convert this chunk from RGB332 to RGB565
                for (uint16_t line = 0; line < lines_to_send; line++)
                {
                    uint8_t *heap_row = &heap_framebuffer[(y + row + line) * DISPLAY_WIDTH + x];
                    // Convert to RGB565
                    for (uint16_t col = 0; col < width; col++)
                    {
                        size_t buf_index = line * width + col;
                        uint8_t palette_index = heap_row[col];
                        lcd_line_buffer[buf_index] = palette[palette_index];
                    }
                }
                // Send to LCD
                lcd_blit(lcd_line_buffer, x, y + row, width, lines_to_send);
            }
        }
    }
}

STATIC mp_obj_t picoware_lcd_swap(void)
{
    picoware_lcd_swap_region(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_swap_obj, picoware_lcd_swap);

STATIC mp_obj_t picoware_lcd_clear_screen(void)
{
    lcd_clear_screen();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_clear_screen_obj, picoware_lcd_clear_screen);

STATIC mp_obj_t picoware_lcd_display_on(void)
{
    lcd_display_on();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_display_on_obj, picoware_lcd_display_on);

STATIC mp_obj_t picoware_lcd_display_off(void)
{
    lcd_display_off();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_display_off_obj, picoware_lcd_display_off);

// Draw pixel in framebuffer (PSRAM or HEAP mode)
STATIC mp_obj_t picoware_lcd_draw_pixel(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, color565
    if (n_args != 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_pixel requires 3 arguments"));
    }

    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);
    uint16_t color = mp_obj_get_int(args[2]);

    // Bounds check
    if (x < 0 || x >= DISPLAY_WIDTH || y < 0 || y >= DISPLAY_HEIGHT)
    {
        return mp_const_none;
    }

    uint8_t color_index = color565_to_332(color);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        // Write to PSRAM
        uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (y * PSRAM_ROW_SIZE) + x;
        psram_qspi_write8(&psram_instance, addr, color_index);
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        // Write RGB332 to heap framebuffer
        heap_framebuffer[y * DISPLAY_WIDTH + x] = color_index;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_pixel_obj, 3, 3, picoware_lcd_draw_pixel);

// Fill rectangle in framebuffer (PSRAM or HEAP mode)
STATIC mp_obj_t picoware_lcd_fill_rect(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, width, height, color565
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_rect requires 5 arguments"));
    }

    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);
    int width = mp_obj_get_int(args[2]);
    int height = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    // Bounds clipping
    if (x < 0)
    {
        width += x;
        x = 0;
    }
    if (y < 0)
    {
        height += y;
        y = 0;
    }
    if (x + width > DISPLAY_WIDTH)
    {
        width = DISPLAY_WIDTH - x;
    }
    if (y + height > DISPLAY_HEIGHT)
    {
        height = DISPLAY_HEIGHT - y;
    }

    if (width <= 0 || height <= 0)
        return mp_const_none;

    uint8_t color_index = color565_to_332(color);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        // Fill line buffer with color once
        memset(line_buffer, color_index, width);

        // Write each row using optimized PSRAM writes
        for (int py = y; py < y + height; py++)
        {
            uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + x;
            uint32_t remaining = width;
            uint32_t offset = 0;

            while (remaining > 0)
            {
                uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
                psram_qspi_write(&psram_instance, addr + offset, line_buffer + offset, chunk_size);
                offset += chunk_size;
                remaining -= chunk_size;
            }
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        // Fill directly in RGB332 heap framebuffer
        for (int py = y; py < y + height; py++)
        {
            memset(&heap_framebuffer[py * DISPLAY_WIDTH + x], color_index, width);
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_fill_rect_obj, 5, 5, picoware_lcd_fill_rect);

// Draw horizontal line (supports both modes)
STATIC mp_obj_t picoware_lcd_draw_line(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, length, color565
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_line requires 4 arguments"));
    }

    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);
    int length = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    // Bounds check
    if (y < 0 || y >= DISPLAY_HEIGHT)
        return mp_const_none;

    uint8_t color_index = color565_to_332(color);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        // Use optimized horizontal line write
        psram_write_hline(x, y, length, color_index);
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        // Clip to screen bounds
        if (x < 0)
        {
            length += x;
            x = 0;
        }
        if (x + length > DISPLAY_WIDTH)
        {
            length = DISPLAY_WIDTH - x;
        }
        if (length <= 0)
            return mp_const_none;

        // Write RGB332 to heap framebuffer
        memset(&heap_framebuffer[y * DISPLAY_WIDTH + x], color_index, length);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_line_obj, 4, 4, picoware_lcd_draw_line);

// Clear framebuffer (supports both modes)
// Takes RGB332 color index for both modes
STATIC mp_obj_t picoware_lcd_clear_framebuffer(mp_obj_t color_obj)
{
    uint8_t color_index = mp_obj_get_int(color_obj);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        clear_psram_framebuffer(color_index);
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        // Fill entire heap framebuffer with RGB332 color
        memset(heap_framebuffer, color_index, HEAP_BUFFER_SIZE);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lcd_clear_framebuffer_obj, picoware_lcd_clear_framebuffer);

STATIC mp_obj_t picoware_lcd_draw_char(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, char, color565
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_char requires 4 arguments"));
    }

    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);
    int char_code = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    // Bounds check
    if (x < 0 || x + CHAR_WIDTH > DISPLAY_WIDTH ||
        y < 0 || y + FONT_HEIGHT > DISPLAY_HEIGHT)
    {
        return mp_const_none; // Character would be out of bounds
    }

    // Validate character code
    if (char_code < 0 || char_code > 127)
    {
        char_code = 127; // Use default character for out of range
    }

    uint8_t color_index = color565_to_332(color);
    const uint8_t *font_data = get_font_data();
    const uint8_t *char_data = &font_data[char_code * FONT_WIDTH];

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        // Render character bitmap using PSRAM writes
        for (int col = 0; col < FONT_WIDTH; col++)
        {
            uint8_t column_data = char_data[col];
            for (int row = 0; row < FONT_HEIGHT; row++)
            {
                if (column_data & (1 << row))
                {
                    uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + ((y + row) * PSRAM_ROW_SIZE) + (x + col);
                    psram_qspi_write8(&psram_instance, addr, color_index);
                }
            }
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        // Render character bitmap to RGB332 heap framebuffer
        for (int col = 0; col < FONT_WIDTH; col++)
        {
            uint8_t column_data = char_data[col];
            for (int row = 0; row < FONT_HEIGHT; row++)
            {
                if (column_data & (1 << row))
                {
                    heap_framebuffer[(y + row) * DISPLAY_WIDTH + (x + col)] = color_index;
                }
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_char_obj, 4, 4, picoware_lcd_draw_char);

STATIC mp_obj_t picoware_lcd_draw_text(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, text_string, color565
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_text requires 4 arguments"));
    }

    int start_x = mp_obj_get_int(args[0]);
    int start_y = mp_obj_get_int(args[1]);
    const char *text = mp_obj_str_get_str(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    uint8_t color_index = color565_to_332(color);
    const uint8_t *font_data = get_font_data();

    int current_x = start_x;
    int current_y = start_y;

    // Process each character in the string
    for (const char *p = text; *p != '\0'; p++)
    {
        char ch = *p;

        if (ch == '\n')
        {
            // Handle newline
            current_x = start_x;
            current_y += FONT_HEIGHT;
            continue;
        }
        else if (ch == ' ')
        {
            // Handle space - just advance position
            current_x += CHAR_WIDTH;
            continue;
        }

        // Check bounds
        if (current_y + FONT_HEIGHT > DISPLAY_HEIGHT)
        {
            break; // Text goes below screen
        }
        if (current_x + CHAR_WIDTH > DISPLAY_WIDTH)
        {
            // Wrap to next line
            current_x = start_x;
            current_y += FONT_HEIGHT;
            if (current_y + FONT_HEIGHT > DISPLAY_HEIGHT)
            {
                break;
            }
        }

        // Validate character
        int char_code = (int)ch;
        if (char_code < 0 || char_code > 127)
        {
            char_code = 127; // Default character
        }

        const uint8_t *char_data = &font_data[char_code * FONT_WIDTH];

        if (lcd_mode == LCD_MODE_PSRAM)
        {
            // Render character bitmap using PSRAM writes
            for (int col = 0; col < FONT_WIDTH; col++)
            {
                uint8_t column_data = char_data[col];
                for (int row = 0; row < FONT_HEIGHT; row++)
                {
                    if (column_data & (1 << row))
                    {
                        int px = current_x + col;
                        int py = current_y + row;
                        if (px < DISPLAY_WIDTH && py < DISPLAY_HEIGHT)
                        {
                            uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px;
                            psram_qspi_write8(&psram_instance, addr, color_index);
                        }
                    }
                }
            }
        }
        else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        {
            // Render character bitmap to RGB332 heap framebuffer
            for (int col = 0; col < FONT_WIDTH; col++)
            {
                uint8_t column_data = char_data[col];
                for (int row = 0; row < FONT_HEIGHT; row++)
                {
                    if (column_data & (1 << row))
                    {
                        int px = current_x + col;
                        int py = current_y + row;
                        if (px < DISPLAY_WIDTH && py < DISPLAY_HEIGHT)
                        {
                            heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;
                        }
                    }
                }
            }
        }

        current_x += CHAR_WIDTH;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_text_obj, 4, 4, picoware_lcd_draw_text);

// Bresenham line algorithm (supports both modes)
STATIC mp_obj_t picoware_lcd_draw_line_custom(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x1, y1, x2, y2, color565
    if (n_args != 5)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_line_custom requires 5 arguments"));
    }

    int x1 = mp_obj_get_int(args[0]);
    int y1 = mp_obj_get_int(args[1]);
    int x2 = mp_obj_get_int(args[2]);
    int y2 = mp_obj_get_int(args[3]);
    uint16_t color = mp_obj_get_int(args[4]);

    uint8_t color_index = color565_to_332(color);

    // Fast path for horizontal lines
    if (y1 == y2)
    {
        if (x1 > x2)
        {
            int temp = x1;
            x1 = x2;
            x2 = temp;
        }
        if (lcd_mode == LCD_MODE_PSRAM)
        {
            psram_write_hline(x1, y1, x2 - x1 + 1, color_index);
        }
        else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        {
            // Clip to screen bounds
            if (y1 < 0 || y1 >= DISPLAY_HEIGHT)
                return mp_const_none;
            if (x1 < 0)
                x1 = 0;
            if (x2 >= DISPLAY_WIDTH)
                x2 = DISPLAY_WIDTH - 1;
            if (x1 > x2)
                return mp_const_none;
            memset(&heap_framebuffer[y1 * DISPLAY_WIDTH + x1], color_index, x2 - x1 + 1);
        }
        return mp_const_none;
    }

    // Bresenham's line algorithm
    int dx = abs(x2 - x1);
    int dy = abs(y2 - y1);
    int sx = (x1 < x2) ? 1 : -1;
    int sy = (y1 < y2) ? 1 : -1;
    int err = dx - dy;

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        while (true)
        {
            // Draw pixel if within bounds using PSRAM write
            if (x1 >= 0 && x1 < DISPLAY_WIDTH && y1 >= 0 && y1 < DISPLAY_HEIGHT)
            {
                uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (y1 * PSRAM_ROW_SIZE) + x1;
                psram_qspi_write8(&psram_instance, addr, color_index);
            }

            if (x1 == x2 && y1 == y2)
                break;

            int e2 = 2 * err;
            if (e2 > -dy)
            {
                err -= dy;
                x1 += sx;
            }
            if (e2 < dx)
            {
                err += dx;
                y1 += sy;
            }
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        while (true)
        {
            // Draw pixel if within bounds using RGB332 heap framebuffer
            if (x1 >= 0 && x1 < DISPLAY_WIDTH && y1 >= 0 && y1 < DISPLAY_HEIGHT)
            {
                heap_framebuffer[y1 * DISPLAY_WIDTH + x1] = color_index;
            }

            if (x1 == x2 && y1 == y2)
                break;

            int e2 = 2 * err;
            if (e2 > -dy)
            {
                err -= dy;
                x1 += sx;
            }
            if (e2 < dx)
            {
                err += dx;
                y1 += sy;
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_line_custom_obj, 5, 5, picoware_lcd_draw_line_custom);

// Draw circle outline using midpoint algorithm (supports both modes)
STATIC mp_obj_t picoware_lcd_draw_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: center_x, center_y, radius, color565
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("draw_circle requires 4 arguments"));
    }

    int center_x = mp_obj_get_int(args[0]);
    int center_y = mp_obj_get_int(args[1]);
    int radius = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    if (radius <= 0 || radius > 100) // Limit radius to prevent issues
        return mp_const_none;

    // Midpoint circle algorithm
    int x = 0;
    int y = radius;
    int d = 3 - 2 * radius;

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        uint8_t color_index = color565_to_332(color);
        while (x <= y)
        {
            // Write all 8 octant pixels using PSRAM write8
            int px, py;

            px = center_x + x;
            py = center_y + y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            px = center_x - x;
            py = center_y + y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            px = center_x + x;
            py = center_y - y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            px = center_x - x;
            py = center_y - y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            px = center_x + y;
            py = center_y + x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            px = center_x - y;
            py = center_y + x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            px = center_x + y;
            py = center_y - x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            px = center_x - y;
            py = center_y - x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                psram_qspi_write8(&psram_instance, PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);

            if (d < 0)
                d += 4 * x + 6;
            else
            {
                d += 4 * (x - y) + 10;
                y--;
            }
            x++;
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        uint8_t color_index = color565_to_332(color);
        while (x <= y)
        {
            // Write all 8 octant pixels to RGB332 heap framebuffer
            int px, py;

            px = center_x + x;
            py = center_y + y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            px = center_x - x;
            py = center_y + y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            px = center_x + x;
            py = center_y - y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            px = center_x - x;
            py = center_y - y;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            px = center_x + y;
            py = center_y + x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            px = center_x - y;
            py = center_y + x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            px = center_x + y;
            py = center_y - x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            px = center_x - y;
            py = center_y - x;
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
                heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;

            if (d < 0)
                d += 4 * x + 6;
            else
            {
                d += 4 * (x - y) + 10;
                y--;
            }
            x++;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_circle_obj, 4, 4, picoware_lcd_draw_circle);

// Helper to write a horizontal line for HEAP mode
static void heap_write_hline(int x, int y, int length, uint8_t color_index)
{
    if (y < 0 || y >= DISPLAY_HEIGHT || length <= 0 || heap_framebuffer == NULL)
        return;

    // Clip to screen bounds
    if (x < 0)
    {
        length += x;
        x = 0;
    }
    if (x + length > DISPLAY_WIDTH)
    {
        length = DISPLAY_WIDTH - x;
    }
    if (length <= 0)
        return;

    uint8_t *row = &heap_framebuffer[y * DISPLAY_WIDTH + x];
    memset(row, color_index, length);
}

// Fill circle using horizontal line spans (supports both modes)
STATIC mp_obj_t picoware_lcd_fill_circle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: center_x, center_y, radius, color565
    if (n_args != 4)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_circle requires 4 arguments"));
    }

    int center_x = mp_obj_get_int(args[0]);
    int center_y = mp_obj_get_int(args[1]);
    int radius = mp_obj_get_int(args[2]);
    uint16_t color = mp_obj_get_int(args[3]);

    if (radius <= 0 || radius > 100)
        return mp_const_none;

    // Midpoint algorithm with horizontal line fills
    int x = 0;
    int y = radius;
    int d = 3 - 2 * radius;

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        uint8_t color_index = color565_to_332(color);
        while (x <= y)
        {
            // Draw horizontal lines for each row of the circle
            psram_write_hline(center_x - x, center_y + y, 2 * x + 1, color_index);
            psram_write_hline(center_x - x, center_y - y, 2 * x + 1, color_index);
            psram_write_hline(center_x - y, center_y + x, 2 * y + 1, color_index);
            psram_write_hline(center_x - y, center_y - x, 2 * y + 1, color_index);

            if (d < 0)
            {
                d += 4 * x + 6;
            }
            else
            {
                d += 4 * (x - y) + 10;
                y--;
            }
            x++;
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        uint8_t color_index = color565_to_332(color);
        while (x <= y)
        {
            // Draw horizontal lines for each row of the circle
            heap_write_hline(center_x - x, center_y + y, 2 * x + 1, color_index);
            heap_write_hline(center_x - x, center_y - y, 2 * x + 1, color_index);
            heap_write_hline(center_x - y, center_y + x, 2 * y + 1, color_index);
            heap_write_hline(center_x - y, center_y - x, 2 * y + 1, color_index);

            if (d < 0)
            {
                d += 4 * x + 6;
            }
            else
            {
                d += 4 * (x - y) + 10;
                y--;
            }
            x++;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_fill_circle_obj, 4, 4, picoware_lcd_fill_circle);

// Fill rounded rectangle
STATIC mp_obj_t picoware_lcd_fill_round_rectangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: x, y, width, height, radius, color565
    if (n_args != 6)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_round_rectangle requires 6 arguments"));
    }

    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);
    int width = mp_obj_get_int(args[2]);
    int height = mp_obj_get_int(args[3]);
    int radius = mp_obj_get_int(args[4]);
    uint16_t color = mp_obj_get_int(args[5]);

    if (width <= 0 || height <= 0 || radius <= 0)
        return mp_const_none;

    // Clip to screen bounds
    if (x < 0)
    {
        width += x;
        x = 0;
    }
    if (y < 0)
    {
        height += y;
        y = 0;
    }
    if (x + width > DISPLAY_WIDTH)
    {
        width = DISPLAY_WIDTH - x;
    }
    if (y + height > DISPLAY_HEIGHT)
    {
        height = DISPLAY_HEIGHT - y;
    }

    if (width <= 0 || height <= 0)
        return mp_const_none;

    // Calculate effective radius considering clipping
    int effective_radius = radius;
    if (effective_radius > width / 2)
        effective_radius = width / 2;
    if (effective_radius > height / 2)
        effective_radius = height / 2;

    uint8_t color_index = color565_to_332(color);

    // Pre-calculate corner centers
    int tl_cx = x + effective_radius;
    int tl_cy = y + effective_radius;
    int tr_cx = x + width - effective_radius;
    int tr_cy = y + effective_radius;
    int bl_cx = x + effective_radius;
    int bl_cy = y + height - effective_radius;
    int br_cx = x + width - effective_radius;
    int br_cy = y + height - effective_radius;

    int radius_sq = effective_radius * effective_radius;

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        for (int py = y; py < y + height; py++)
        {
            for (int px = x; px < x + width; px++)
            {
                bool in_corner = false;

                // Check if pixel is in one of the corner exclusion zones
                if (px < tl_cx && py < tl_cy)
                {
                    // Top-left corner
                    int dx = px - tl_cx;
                    int dy = py - tl_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }
                else if (px >= tr_cx && py < tr_cy)
                {
                    // Top-right corner
                    int dx = px - tr_cx;
                    int dy = py - tr_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }
                else if (px < bl_cx && py >= bl_cy)
                {
                    // Bottom-left corner
                    int dx = px - bl_cx;
                    int dy = py - bl_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }
                else if (px >= br_cx && py >= br_cy)
                {
                    // Bottom-right corner
                    int dx = px - br_cx;
                    int dy = py - br_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }

                if (!in_corner)
                {
                    uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px;
                    psram_qspi_write8(&psram_instance, addr, color_index);
                }
            }
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        for (int py = y; py < y + height; py++)
        {
            for (int px = x; px < x + width; px++)
            {
                bool in_corner = false;

                // Check if pixel is in one of the corner exclusion zones
                if (px < tl_cx && py < tl_cy)
                {
                    // Top-left corner
                    int dx = px - tl_cx;
                    int dy = py - tl_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }
                else if (px >= tr_cx && py < tr_cy)
                {
                    // Top-right corner
                    int dx = px - tr_cx;
                    int dy = py - tr_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }
                else if (px < bl_cx && py >= bl_cy)
                {
                    // Bottom-left corner
                    int dx = px - bl_cx;
                    int dy = py - bl_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }
                else if (px >= br_cx && py >= br_cy)
                {
                    // Bottom-right corner
                    int dx = px - br_cx;
                    int dy = py - br_cy;
                    if (dx * dx + dy * dy > radius_sq)
                        in_corner = true;
                }

                if (!in_corner)
                {
                    heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;
                }
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_fill_round_rectangle_obj, 6, 6, picoware_lcd_fill_round_rectangle);

// Helper function to swap two floats
STATIC void swap_float(float *a, float *b)
{
    float temp = *a;
    *a = *b;
    *b = temp;
}

STATIC mp_obj_t picoware_lcd_fill_triangle(size_t n_args, const mp_obj_t *args)
{
    // Arguments: p1_x, p1_y, p2_x, p2_y, p3_x, p3_y, color565
    if (n_args != 7)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("fill_triangle requires 7 arguments"));
    }

    // Get triangle vertices
    float p1_x = (float)mp_obj_get_float(args[0]);
    float p1_y = (float)mp_obj_get_float(args[1]);
    float p2_x = (float)mp_obj_get_float(args[2]);
    float p2_y = (float)mp_obj_get_float(args[3]);
    float p3_x = (float)mp_obj_get_float(args[4]);
    float p3_y = (float)mp_obj_get_float(args[5]);
    uint16_t color = mp_obj_get_int(args[6]);

    uint8_t color_index = color565_to_332(color);

    // Sort vertices by Y coordinate (p1.y <= p2.y <= p3.y)
    if (p1_y > p2_y)
    {
        swap_float(&p1_x, &p2_x);
        swap_float(&p1_y, &p2_y);
    }
    if (p2_y > p3_y)
    {
        swap_float(&p2_x, &p3_x);
        swap_float(&p2_y, &p3_y);
    }
    if (p1_y > p2_y)
    {
        swap_float(&p1_x, &p2_x);
        swap_float(&p1_y, &p2_y);
    }

    int y1 = (int)p1_y;
    int y2 = (int)p2_y;
    int y3 = (int)p3_y;

    // Handle degenerate case (all points on same line)
    if (y1 == y3)
        return mp_const_none;

    // Fill the triangle using horizontal scanlines
    for (int y = y1; y <= y3; y++)
    {
        if (y < 0 || y >= DISPLAY_HEIGHT)
            continue; // Skip lines outside screen bounds

        float x_left = 0, x_right = 0;
        bool has_left = false, has_right = false;

        // Find left edge intersection
        if (y3 != y1)
        {
            x_left = p1_x + (p3_x - p1_x) * (y - y1) / (y3 - y1);
            has_left = true;
        }

        // Find right edge intersection
        if (y <= y2)
        {
            // Upper part of triangle (from p1 to p2)
            if (y2 != y1)
            {
                float x_temp = p1_x + (p2_x - p1_x) * (y - y1) / (y2 - y1);
                if (!has_right)
                {
                    x_right = x_temp;
                    has_right = true;
                }
                else
                {
                    // We have both intersections, determine which is left/right
                    if (x_temp < x_left)
                    {
                        x_right = x_left;
                        x_left = x_temp;
                    }
                    else
                    {
                        x_right = x_temp;
                    }
                }
            }
        }
        else
        {
            // Lower part of triangle (from p2 to p3)
            if (y3 != y2)
            {
                float x_temp = p2_x + (p3_x - p2_x) * (y - y2) / (y3 - y2);
                if (!has_right)
                {
                    x_right = x_temp;
                    has_right = true;
                }
                else
                {
                    // We have both intersections, determine which is left/right
                    if (x_temp < x_left)
                    {
                        x_right = x_left;
                        x_left = x_temp;
                    }
                    else
                    {
                        x_right = x_temp;
                    }
                }
            }
        }

        // Draw horizontal line from x_left to x_right
        if (has_left && has_right)
        {
            int start_x = (int)(x_left < x_right ? x_left : x_right);
            int end_x = (int)(x_left > x_right ? x_left : x_right);

            if (lcd_mode == LCD_MODE_PSRAM)
            {
                // Use optimized horizontal line write for PSRAM
                psram_write_hline(start_x, y, end_x - start_x + 1, color_index);
            }
            else if (lcd_mode == LCD_MODE_HEAP)
            {
                // Use HEAP horizontal line write
                heap_write_hline(start_x, y, end_x - start_x + 1, color_index);
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_fill_triangle_obj, 7, 7, picoware_lcd_fill_triangle);

// Draw an 8-bit byte array image to framebuffer (supports both modes)
// Args: x (int), y (int), width (int), height (int), byte_data (bytes/bytearray), invert (bool)
STATIC mp_obj_t picoware_lcd_draw_image_bytearray(size_t n_args, const mp_obj_t *args)
{
    // Get position and size
    int x = mp_obj_get_int(args[0]);
    int y = mp_obj_get_int(args[1]);
    int width = mp_obj_get_int(args[2]);
    int height = mp_obj_get_int(args[3]);

    // Get byte data
    mp_buffer_info_t data_info;
    mp_get_buffer_raise(args[4], &data_info, MP_BUFFER_READ);
    uint8_t *byte_data = (uint8_t *)data_info.buf;

    // Get invert flag (optional, default false)
    bool invert = false;
    if (n_args > 5)
    {
        invert = mp_obj_is_true(args[5]);
    }

    // Clip to screen bounds
    int src_x = (x < 0) ? -x : 0;
    int src_y = (y < 0) ? -y : 0;
    int dst_x = (x < 0) ? 0 : x;
    int dst_y = (y < 0) ? 0 : y;
    int copy_width = width - src_x;
    int copy_height = height - src_y;

    // Adjust for right and bottom boundaries
    if (dst_x + copy_width > DISPLAY_WIDTH)
    {
        copy_width = DISPLAY_WIDTH - dst_x;
    }
    if (dst_y + copy_height > DISPLAY_HEIGHT)
    {
        copy_height = DISPLAY_HEIGHT - dst_y;
    }

    // Early exit if nothing to draw
    if (copy_width <= 0 || copy_height <= 0)
    {
        return mp_const_none;
    }

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        // Copy line by line to PSRAM
        for (int row = 0; row < copy_height; row++)
        {
            int src_row_start = (src_y + row) * width + src_x;
            uint32_t psram_addr = PSRAM_FRAMEBUFFER_ADDR + ((dst_y + row) * PSRAM_ROW_SIZE) + dst_x;

            if (invert)
            {
                // Invert colors while copying - use line buffer
                for (int col = 0; col < copy_width; col++)
                {
                    line_buffer[col] = 255 - byte_data[src_row_start + col];
                }

                // Write inverted data to PSRAM in chunks
                uint32_t remaining = copy_width;
                uint32_t offset = 0;
                while (remaining > 0)
                {
                    uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
                    psram_qspi_write(&psram_instance, psram_addr + offset, line_buffer + offset, chunk_size);
                    offset += chunk_size;
                    remaining -= chunk_size;
                }
            }
            else
            {
                // Direct write to PSRAM in chunks
                uint32_t remaining = copy_width;
                uint32_t offset = 0;
                while (remaining > 0)
                {
                    uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
                    psram_qspi_write(&psram_instance, psram_addr + offset, byte_data + src_row_start + offset, chunk_size);
                    offset += chunk_size;
                    remaining -= chunk_size;
                }
            }
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        // Copy line by line to heap framebuffer (already RGB332)
        for (int row = 0; row < copy_height; row++)
        {
            int src_row_start = (src_y + row) * width + src_x;
            uint8_t *dst_row = &heap_framebuffer[(dst_y + row) * DISPLAY_WIDTH + dst_x];

            if (invert)
            {
                for (int col = 0; col < copy_width; col++)
                {
                    dst_row[col] = 255 - byte_data[src_row_start + col];
                }
            }
            else
            {
                memcpy(dst_row, &byte_data[src_row_start], copy_width);
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_lcd_draw_image_bytearray_obj, 5, 6, picoware_lcd_draw_image_bytearray);

// Set LCD mode (0=PSRAM, 1=HEAP)
// This allows switching modes after initialization
STATIC mp_obj_t picoware_lcd_set_mode(mp_obj_t mode_obj)
{
    uint8_t new_mode = mp_obj_get_int(mode_obj);
    if (new_mode > LCD_MODE_HEAP)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid mode: 0=PSRAM, 1=HEAP"));
    }

    if (new_mode == lcd_mode)
    {
        return mp_const_none; // Already in this mode
    }

    if (new_mode == LCD_MODE_PSRAM)
    {
        // Switch to PSRAM mode
        if (!psram_initialized)
        {
            psram_instance = psram_qspi_init(pio1, -1, 1.0f);
            psram_initialized = true;
        }

        // Free HEAP buffer if it was allocated
        free_heap_framebuffer();
    }
    else if (new_mode == LCD_MODE_HEAP)
    {
        // Switch to HEAP mode
        if (!allocate_heap_framebuffer())
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("Failed to allocate HEAP framebuffer"));
        }
        // Clear the framebuffer to black
        memset(heap_framebuffer, 0, HEAP_BUFFER_SIZE);

        // deinit psram
        if (psram_initialized)
        {
            clear_psram_framebuffer(0);
            psram_qspi_deinit(&psram_instance);
            psram_initialized = false;
        }
    }

    lcd_mode = new_mode;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_lcd_set_mode_obj, picoware_lcd_set_mode);

// Get current LCD mode
STATIC mp_obj_t picoware_lcd_get_mode(void)
{
    return mp_obj_new_int(lcd_mode);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_get_mode_obj, picoware_lcd_get_mode);

// Check if PSRAM framebuffer is initialized
STATIC mp_obj_t picoware_lcd_is_psram_ready(void)
{
    return mp_obj_new_bool(psram_initialized);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_lcd_is_psram_ready_obj, picoware_lcd_is_psram_ready);

// Get PSRAM instance pointer
psram_qspi_inst_t *picoware_get_psram_instance(void)
{
    return psram_initialized ? &psram_instance : NULL;
}

// Module globals table
STATIC const mp_rom_map_elem_t picoware_lcd_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_lcd)},

    // Display control
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_lcd_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_lcd_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_screen), MP_ROM_PTR(&picoware_lcd_clear_screen_obj)},
    {MP_ROM_QSTR(MP_QSTR_display_on), MP_ROM_PTR(&picoware_lcd_display_on_obj)},
    {MP_ROM_QSTR(MP_QSTR_display_off), MP_ROM_PTR(&picoware_lcd_display_off_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_psram_ready), MP_ROM_PTR(&picoware_lcd_is_psram_ready_obj)},

    // Mode control
    {MP_ROM_QSTR(MP_QSTR_set_mode), MP_ROM_PTR(&picoware_lcd_set_mode_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_mode), MP_ROM_PTR(&picoware_lcd_get_mode_obj)},

    // swap
    {MP_ROM_QSTR(MP_QSTR_swap), MP_ROM_PTR(&picoware_lcd_swap_obj)},

    // Drawing functions
    {MP_ROM_QSTR(MP_QSTR_draw_pixel), MP_ROM_PTR(&picoware_lcd_draw_pixel_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_rect), MP_ROM_PTR(&picoware_lcd_fill_rect_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_line), MP_ROM_PTR(&picoware_lcd_draw_line_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_line_custom), MP_ROM_PTR(&picoware_lcd_draw_line_custom_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_circle), MP_ROM_PTR(&picoware_lcd_draw_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_circle), MP_ROM_PTR(&picoware_lcd_fill_circle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_round_rectangle), MP_ROM_PTR(&picoware_lcd_fill_round_rectangle_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill_triangle), MP_ROM_PTR(&picoware_lcd_fill_triangle_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_framebuffer), MP_ROM_PTR(&picoware_lcd_clear_framebuffer_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_image_bytearray), MP_ROM_PTR(&picoware_lcd_draw_image_bytearray_obj)},

    // Font rendering functions
    {MP_ROM_QSTR(MP_QSTR_draw_char), MP_ROM_PTR(&picoware_lcd_draw_char_obj)},
    {MP_ROM_QSTR(MP_QSTR_draw_text), MP_ROM_PTR(&picoware_lcd_draw_text_obj)},

    // Constants
    {MP_ROM_QSTR(MP_QSTR_WIDTH), MP_ROM_INT(DISPLAY_WIDTH)},
    {MP_ROM_QSTR(MP_QSTR_HEIGHT), MP_ROM_INT(DISPLAY_HEIGHT)},
    {MP_ROM_QSTR(MP_QSTR_CHAR_WIDTH), MP_ROM_INT(CHAR_WIDTH)},
    {MP_ROM_QSTR(MP_QSTR_CHAR_HEIGHT), MP_ROM_INT(CHAR_HEIGHT)},
    {MP_ROM_QSTR(MP_QSTR_FONT_HEIGHT), MP_ROM_INT(FONT_HEIGHT)},
    {MP_ROM_QSTR(MP_QSTR_PSRAM_FRAMEBUFFER_ADDR), MP_ROM_INT(PSRAM_FRAMEBUFFER_ADDR)},
    {MP_ROM_QSTR(MP_QSTR_PSRAM_BUFFER_SIZE), MP_ROM_INT(PSRAM_BUFFER_SIZE)},

    // Mode constants
    {MP_ROM_QSTR(MP_QSTR_MODE_PSRAM), MP_ROM_INT(LCD_MODE_PSRAM)},
    {MP_ROM_QSTR(MP_QSTR_MODE_HEAP), MP_ROM_INT(LCD_MODE_HEAP)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_lcd_module_globals, picoware_lcd_module_globals_table);

// Module definition
const mp_obj_module_t picoware_lcd_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_lcd_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_picoware_lcd, picoware_lcd_user_cmodule);