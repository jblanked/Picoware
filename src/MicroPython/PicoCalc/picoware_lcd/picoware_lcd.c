/*
 * Picoware LCD C Library
 * Copyright © 2025 JBlanked
 *
 * Uses a board-specific framebuffer format: RGB565 on ESP32-P4, RGB332 elsewhere.
 */
#include "picoware_lcd.h"
#include "../picoware_psram/picoware_psram_shared.h"
#include "py/runtime.h"

#include "../../log/log_mp.h"

#if defined(PICOCALC_ESP32_P4)
#include "driver/ppa.h"
#include "esp_err.h"
#include "esp_attr.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#endif

#if defined(PICOCALC_ESP32_P4)
#define PSRAM_FRAMEBUFFER_FILL_CHUNK_SIZE 8192
#define LCD_CHUNK_LINES 32
#else
#define PSRAM_FRAMEBUFFER_FILL_CHUNK_SIZE PSRAM_CHUNK_SIZE
#define LCD_CHUNK_LINES 16
#endif

// Module state
static bool module_initialized = false;

#if defined(PICOCALC_ESP32_P4)
typedef uint16_t lcd_pixel_t;
#else
typedef uint8_t lcd_pixel_t;
#endif

#define LCD_PIXEL_BYTES (sizeof(lcd_pixel_t))

// Line buffer for batch operations (reusable)
static lcd_pixel_t line_buffer[DISPLAY_WIDTH] __attribute__((aligned(4)));

#define LCD_MODE_PSRAM 0
#define LCD_MODE_HEAP 1

#if defined(PICOCALC_ESP32_P4)
static uint8_t lcd_mode = LCD_MODE_HEAP;
#else
static uint8_t lcd_mode = LCD_MODE_PSRAM;
#endif

// Heap mode state
static lcd_pixel_t *heap_framebuffer = NULL;
static bool heap_framebuffer_allocated = false;
#define HEAP_BUFFER_SIZE (DISPLAY_WIDTH * DISPLAY_HEIGHT)
#define HEAP_FRAMEBUFFER_BYTES ((size_t)HEAP_BUFFER_SIZE * LCD_PIXEL_BYTES)
static size_t heap_framebuffer_alloc_size;
#if defined(PICOCALC_ESP32_P4)
#define PPA_OUTPUT_ALIGNMENT 64 // ESP-IDF 5.5 P4 cache-line alignment for PPA buffers
// The P4 system PSRAM is memory-mapped and accessible to the PPA.
static lcd_pixel_t p4_heap_framebuffer[HEAP_BUFFER_SIZE] EXT_RAM_BSS_ATTR
    __attribute__((aligned(PPA_OUTPUT_ALIGNMENT)));
#endif

static uint16_t palette[256] __attribute__((aligned(4)));
static uint16_t lcd_line_buffer[DISPLAY_WIDTH * LCD_CHUNK_LINES] __attribute__((aligned(4)));
#if defined(PICOCALC_ESP32_P4)
static const char *TAG = "picocalc-lcd";
static ppa_client_handle_t ppa_fill_client;
static ppa_client_handle_t ppa_blend_client;
static bool ppa_initialized;
#endif

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

static uint8_t color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

static uint16_t lcd_color332_to_565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

static inline lcd_pixel_t rgb565_to_lcd_pixel(uint16_t color)
{
#if defined(PICOCALC_ESP32_P4)
    return color;
#else
    return color565_to_332(color);
#endif
}

static inline lcd_pixel_t rgb332_to_lcd_pixel(uint8_t pixel_index)
{
#if defined(PICOCALC_ESP32_P4)
    return palette[pixel_index];
#else
    return pixel_index;
#endif
}

static inline uint16_t lcd_pixel_to_rgb565(lcd_pixel_t pixel)
{
#if defined(PICOCALC_ESP32_P4)
    return pixel;
#else
    return palette[pixel];
#endif
}

static inline uint32_t psram_framebuffer_pixel_addr(int x, int y)
{
    return PSRAM_FRAMEBUFFER_ADDR + (uint32_t)y * PSRAM_ROW_SIZE + (uint32_t)x * LCD_PIXEL_BYTES;
}

static void psram_write_pixel(int x, int y, lcd_pixel_t pixel)
{
    psram_qspi_write(&psram_instance, psram_framebuffer_pixel_addr(x, y),
                     (const uint8_t *)&pixel, LCD_PIXEL_BYTES);
}

static void psram_write_span_to(psram_qspi_inst_t *psram, int x, int y,
                                const lcd_pixel_t *pixels, size_t count)
{
    if (psram == NULL || count == 0)
    {
        return;
    }

    uint32_t addr = psram_framebuffer_pixel_addr(x, y);
    const uint8_t *source = (const uint8_t *)pixels;
    size_t remaining = count * LCD_PIXEL_BYTES;
    size_t offset = 0;
    while (remaining > 0)
    {
        size_t chunk_size = remaining > PSRAM_CHUNK_SIZE ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(psram, addr + offset, source + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

static void psram_write_span(int x, int y, const lcd_pixel_t *pixels, size_t count)
{
    psram_write_span_to(&psram_instance, x, y, pixels, count);
}

static void psram_read_span(int x, int y, lcd_pixel_t *pixels, size_t count)
{
    if (count == 0)
    {
        return;
    }

    uint32_t addr = psram_framebuffer_pixel_addr(x, y);
    uint8_t *destination = (uint8_t *)pixels;
    size_t remaining = count * LCD_PIXEL_BYTES;
    size_t offset = 0;
    while (remaining > 0)
    {
        size_t chunk_size = remaining > PSRAM_CHUNK_SIZE ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_read(&psram_instance, addr + offset, destination + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

static void write_framebuffer_pixel(int x, int y, lcd_pixel_t pixel)
{
    if (x < 0 || x >= DISPLAY_WIDTH || y < 0 || y >= DISPLAY_HEIGHT)
    {
        return;
    }
    if (lcd_mode == LCD_MODE_PSRAM)
    {
        psram_write_pixel(x, y, pixel);
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        heap_framebuffer[(size_t)y * DISPLAY_WIDTH + x] = pixel;
    }
}

void picoware_write_pixel_fb(psram_qspi_inst_t *psram, int x, int y, uint8_t color_index)
{
    if (lcd_mode == LCD_MODE_PSRAM)
    {
        if (psram != NULL && x >= 0 && x < DISPLAY_WIDTH && y >= 0 && y < DISPLAY_HEIGHT)
        {
            lcd_pixel_t pixel = rgb332_to_lcd_pixel(color_index);
            psram_qspi_write(psram, psram_framebuffer_pixel_addr(x, y),
                             (const uint8_t *)&pixel, LCD_PIXEL_BYTES);
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP)
    {
        if (heap_framebuffer != NULL && x >= 0 && x < DISPLAY_WIDTH && y >= 0 && y < DISPLAY_HEIGHT)
        {
            heap_framebuffer[(size_t)y * DISPLAY_WIDTH + x] = rgb332_to_lcd_pixel(color_index);
        }
    }
}

void picoware_write_buffer_fb_16(psram_qspi_inst_t *psram, int x, int y, int width, int height, const uint16_t *buffer)
{
    if (!buffer || width <= 0 || height <= 0)
        return;

    int src_x = x < 0 ? -x : 0;
    int dst_x = x < 0 ? 0 : x;
    int copy_width = width - src_x;
    if (dst_x + copy_width > DISPLAY_WIDTH)
        copy_width = DISPLAY_WIDTH - dst_x;
    if (copy_width <= 0)
        return;

    for (int row = 0; row < height; row++)
    {
        int fb_y = y + row;
        if (fb_y < 0 || fb_y >= DISPLAY_HEIGHT)
            continue;

        const uint16_t *source = &buffer[(size_t)row * width + src_x];
        for (int col = 0; col < copy_width; col++)
        {
            line_buffer[col] = rgb565_to_lcd_pixel(source[col]);
        }

        if (lcd_mode == LCD_MODE_PSRAM)
        {
            psram_write_span_to(psram, dst_x, fb_y, line_buffer, (size_t)copy_width);
        }
        else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        {
            memcpy(&heap_framebuffer[(size_t)fb_y * DISPLAY_WIDTH + dst_x], line_buffer,
                   (size_t)copy_width * LCD_PIXEL_BYTES);
        }
    }
}

static inline void psram_write_hline(int x, int y, int length, lcd_pixel_t pixel)
{
    if (y < 0 || y >= DISPLAY_HEIGHT || length <= 0)
        return;

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

#if defined(PICOCALC_ESP32_P4)
    for (int i = 0; i < length; i++)
    {
        line_buffer[i] = pixel;
    }
#else
    memset(line_buffer, pixel, length);
#endif
    psram_write_span(x, y, line_buffer, (size_t)length);
}

static void heap_write_hline(int x, int y, int length, lcd_pixel_t pixel)
{
    if (y < 0 || y >= DISPLAY_HEIGHT || length <= 0 || heap_framebuffer == NULL)
        return;

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

#if defined(PICOCALC_ESP32_P4)
    lcd_pixel_t *destination = &heap_framebuffer[(size_t)y * DISPLAY_WIDTH + x];
    for (int i = 0; i < length; i++)
    {
        destination[i] = pixel;
    }
#else
    memset(&heap_framebuffer[(size_t)y * DISPLAY_WIDTH + x], pixel, length);
#endif
}

static bool allocate_heap_framebuffer(void)
{
    if (heap_framebuffer == NULL)
    {
#if defined(PICOCALC_ESP32_P4)
        heap_framebuffer = p4_heap_framebuffer;
        heap_framebuffer_alloc_size = HEAP_FRAMEBUFFER_BYTES;
        memset(heap_framebuffer, 0, HEAP_FRAMEBUFFER_BYTES);
#else
        heap_framebuffer = (lcd_pixel_t *)m_tracked_calloc(1, HEAP_FRAMEBUFFER_BYTES);
        if (heap_framebuffer == NULL)
            return false;
        heap_framebuffer_alloc_size = HEAP_FRAMEBUFFER_BYTES;
        memset(heap_framebuffer, 0, HEAP_FRAMEBUFFER_BYTES);
#endif
        heap_framebuffer_allocated = true;
    }
    return true;
}

static void free_heap_framebuffer(void)
{
    if (heap_framebuffer != NULL && heap_framebuffer_allocated)
    {
#if !defined(PICOCALC_ESP32_P4)
        m_tracked_free(heap_framebuffer);
#endif
        heap_framebuffer = NULL;
        heap_framebuffer_alloc_size = 0;
        heap_framebuffer_allocated = false;
    }
}

static void clear_psram_framebuffer(lcd_pixel_t pixel)
{
#if defined(PICOCALC_ESP32_P4)
    uint32_t fill_value = ((uint32_t)pixel << 16) | pixel;
#else
    uint32_t fill_value = ((uint32_t)pixel << 24) | ((uint32_t)pixel << 16) | ((uint32_t)pixel << 8) | pixel;
#endif

    uint32_t word_count = PSRAM_BUFFER_SIZE / 4;
    static uint32_t fill32_buffer[PSRAM_FRAMEBUFFER_FILL_CHUNK_SIZE / 4] __attribute__((aligned(4)));

    for (size_t i = 0; i < PSRAM_FRAMEBUFFER_FILL_CHUNK_SIZE / 4; i++)
        fill32_buffer[i] = fill_value;

    uint32_t current_addr = PSRAM_FRAMEBUFFER_ADDR;
    uint32_t remaining = word_count;
    while (remaining > 0)
    {
        uint32_t words = (remaining > (PSRAM_FRAMEBUFFER_FILL_CHUNK_SIZE / 4))
                             ? (PSRAM_FRAMEBUFFER_FILL_CHUNK_SIZE / 4)
                             : remaining;
        psram_qspi_write(&psram_instance, current_addr, (const uint8_t *)fill32_buffer, words * 4);
        current_addr += words * 4;
        remaining -= words;
    }
}

static void swap_float(float *a, float *b)
{
    float t = *a;
    *a = *b;
    *b = t;
}

static bool picoware_psram_ensure_initialized(void)
{
    if (lcd_mode != LCD_MODE_PSRAM)
    {
        return false;
    }
    if (!psram_initialized)
    {
        psram_instance = PICOWARE_PSRAM_INIT();
        psram_initialized = true;
    }
    return psram_initialized;
}

#if defined(PICOCALC_ESP32_P4)
static void picoware_ppa_init(void)
{
    if (ppa_initialized)
    {
        return;
    }
    ppa_initialized = true;

    ppa_client_config_t client_config = {
        .oper_type = PPA_OPERATION_FILL,
        .max_pending_trans_num = 1,
        .data_burst_length = PPA_DATA_BURST_LENGTH_128,
    };
    esp_err_t err = ppa_register_client(&client_config, &ppa_fill_client);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "PPA fill client registration failed: %s", esp_err_to_name(err));
    }

    client_config.oper_type = PPA_OPERATION_BLEND;
    err = ppa_register_client(&client_config, &ppa_blend_client);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "PPA blend client registration failed: %s", esp_err_to_name(err));
    }
}

static void picoware_ppa_deinit(void)
{
    if (ppa_blend_client != NULL)
    {
        esp_err_t err = ppa_unregister_client(ppa_blend_client);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "PPA blend client removal failed: %s", esp_err_to_name(err));
        }
        else
        {
            ppa_blend_client = NULL;
        }
    }

    if (ppa_fill_client != NULL)
    {
        esp_err_t err = ppa_unregister_client(ppa_fill_client);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "PPA fill client removal failed: %s", esp_err_to_name(err));
        }
        else
        {
            ppa_fill_client = NULL;
        }
    }
    ppa_initialized = false;
}

static bool ppa_fill_heap_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    if (ppa_fill_client == NULL || heap_framebuffer == NULL || width == 0 || height == 0)
    {
        return false;
    }

    uint8_t r5 = (color >> 11) & 0x1F;
    uint8_t g6 = (color >> 5) & 0x3F;
    uint8_t b5 = color & 0x1F;
    ppa_fill_oper_config_t config = {
        .out = {
            .buffer = heap_framebuffer,
            .buffer_size = (uint32_t)heap_framebuffer_alloc_size,
            .pic_w = DISPLAY_WIDTH,
            .pic_h = DISPLAY_HEIGHT,
            .block_offset_x = x,
            .block_offset_y = y,
            .fill_cm = PPA_FILL_COLOR_MODE_RGB565,
        },
        .fill_block_w = width,
        .fill_block_h = height,
        .fill_argb_color = {
            .a = 0xFF,
            .r = (uint8_t)((r5 << 3) | (r5 >> 2)),
            .g = (uint8_t)((g6 << 2) | (g6 >> 4)),
            .b = (uint8_t)((b5 << 3) | (b5 >> 2)),
        },
        .mode = PPA_TRANS_MODE_BLOCKING,
    };

    esp_err_t err = ppa_do_fill(ppa_fill_client, &config);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "PPA fill failed; using CPU fill: %s", esp_err_to_name(err));
        return false;
    }
    return true;
}

static bool ppa_blend_masked_rgb332(int dst_x, int dst_y, int src_x, int src_y,
                                    uint16_t width, uint16_t height, uint16_t src_width,
                                    const uint8_t *buffer, const uint8_t *mask)
{
    if (ppa_blend_client == NULL || heap_framebuffer == NULL || buffer == NULL || mask == NULL)
    {
        return false;
    }

    size_t pixel_count = (size_t)width * height;
    if (pixel_count > SIZE_MAX / sizeof(color_pixel_argb8888_data_t))
    {
        ESP_LOGW(TAG, "PPA masked image is too large; using CPU blend");
        return false;
    }

    size_t scratch_size = pixel_count * sizeof(color_pixel_argb8888_data_t);
    color_pixel_argb8888_data_t *foreground =
        (color_pixel_argb8888_data_t *)heap_caps_malloc(scratch_size, MALLOC_CAP_SPIRAM | MALLOC_CAP_DMA);
    if (foreground == NULL)
    {
        foreground = (color_pixel_argb8888_data_t *)heap_caps_malloc(
            scratch_size, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT | MALLOC_CAP_DMA);
    }
    if (foreground == NULL)
    {
        ESP_LOGW(TAG, "PPA masked image scratch allocation failed; using CPU blend");
        return false;
    }

    for (uint16_t row = 0; row < height; row++)
    {
        for (uint16_t col = 0; col < width; col++)
        {
            size_t source_index = (size_t)(src_y + row) * src_width + src_x + col;
            color_pixel_argb8888_data_t *pixel = &foreground[(size_t)row * width + col];
            if (mask[source_index >> 3] & (0x80u >> (source_index & 7)))
            {
                uint16_t rgb565 = palette[buffer[source_index]];
                uint8_t r5 = (rgb565 >> 11) & 0x1F;
                uint8_t g6 = (rgb565 >> 5) & 0x3F;
                uint8_t b5 = rgb565 & 0x1F;
                pixel->a = 0xFF;
                pixel->r = (uint8_t)((r5 << 3) | (r5 >> 2));
                pixel->g = (uint8_t)((g6 << 2) | (g6 >> 4));
                pixel->b = (uint8_t)((b5 << 3) | (b5 >> 2));
            }
            else
            {
                pixel->val = 0;
            }
        }
    }

    ppa_blend_oper_config_t config = {
        .in_bg = {
            .buffer = heap_framebuffer,
            .pic_w = DISPLAY_WIDTH,
            .pic_h = DISPLAY_HEIGHT,
            .block_w = width,
            .block_h = height,
            .block_offset_x = dst_x,
            .block_offset_y = dst_y,
            .blend_cm = PPA_BLEND_COLOR_MODE_RGB565,
        },
        .in_fg = {
            .buffer = foreground,
            .pic_w = width,
            .pic_h = height,
            .block_w = width,
            .block_h = height,
            .blend_cm = PPA_BLEND_COLOR_MODE_ARGB8888,
        },
        .out = {
            .buffer = heap_framebuffer,
            .buffer_size = (uint32_t)heap_framebuffer_alloc_size,
            .pic_w = DISPLAY_WIDTH,
            .pic_h = DISPLAY_HEIGHT,
            .block_offset_x = dst_x,
            .block_offset_y = dst_y,
            .blend_cm = PPA_BLEND_COLOR_MODE_RGB565,
        },
        .mode = PPA_TRANS_MODE_BLOCKING,
    };

    esp_err_t err = ppa_do_blend(ppa_blend_client, &config);
    heap_caps_free(foreground);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "PPA masked blend failed; using CPU blend: %s", esp_err_to_name(err));
        return false;
    }
    return true;
}
#endif

// ---------------------------------------------------------------------------
// Public API – matches picoware_lcd.h
// ---------------------------------------------------------------------------

void picocalc_lcd_init(void)
{
    if (!module_initialized)
    {
        if (!lcd_init())
        {
            mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PicoCalc LCD initialization failed"));
        }

        for (int i = 0; i < 256; i++)
        {
            uint8_t r3 = (i >> 5) & 0x07;
            uint8_t g3 = (i >> 2) & 0x07;
            uint8_t b2 = i & 0x03;

            uint8_t r8 = (r3 * 255) / 7;
            uint8_t g8 = (g3 * 255) / 7;
            uint8_t b8 = (b2 * 255) / 3;

            palette[i] = lcd_color332_to_565(r8, g8, b8);
        }

        module_initialized = true;
    }

#if defined(PICOCALC_ESP32_P4)
    picoware_ppa_init();
#endif

    free_heap_framebuffer();

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        picoware_psram_ensure_initialized();
    }
    else if (!allocate_heap_framebuffer())
    {
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("Failed to allocate PicoCalc framebuffer"));
    }
#if defined(PICOCALC_ESP32_P4)
    lcd_ppa_srm_init();
#endif
}

void lcd_deinit(void)
{
    if (module_initialized)
    {
#if defined(PICOCALC_ESP32_P4)
        lcd_ppa_srm_deinit();
        picoware_ppa_deinit();
#endif
        free_heap_framebuffer();

        if (psram_initialized)
        {
            psram_qspi_deinit(&psram_instance);
            psram_initialized = false;
        }

        module_initialized = false;
    }
}

void lcd_swap(void)
{
    picoware_lcd_swap_region(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT);
}

void picoware_lcd_swap_region(uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    if (lcd_mode == LCD_MODE_PSRAM)
    {
        if (module_initialized && !picoware_psram_ensure_initialized())
            return;
    }

#if defined(PICOCALC_ESP32_P4)
    if ((lcd_mode == LCD_MODE_HEAP && heap_framebuffer == NULL) ||
        (lcd_mode != LCD_MODE_HEAP && lcd_mode != LCD_MODE_PSRAM))
    {
        return;
    }

    const bool full_frame = x == 0 && y == 0 &&
                            width == DISPLAY_WIDTH && height == DISPLAY_HEIGHT &&
                            (lcd_mode == LCD_MODE_PSRAM || heap_framebuffer != NULL);
    if (full_frame)
    {
        lcd_acquire();
        lcd_set_window(0, 0, DISPLAY_WIDTH - 1, DISPLAY_HEIGHT - 1);
    }

    for (uint16_t row = 0; row < height; row += LCD_CHUNK_LINES)
    {
        uint16_t lines_to_send = (row + LCD_CHUNK_LINES > height) ? (height - row) : LCD_CHUNK_LINES;
        for (uint16_t line = 0; line < lines_to_send; line++)
        {
            lcd_pixel_t *destination = &lcd_line_buffer[(size_t)line * width];
            uint16_t source_y = y + row + line;
            if (lcd_mode == LCD_MODE_PSRAM)
            {
                psram_read_span(x, source_y, destination, width);
            }
            else
            {
                memcpy(destination, &heap_framebuffer[(size_t)source_y * DISPLAY_WIDTH + x],
                       (size_t)width * LCD_PIXEL_BYTES);
            }
        }

        if (full_frame)
        {
            lcd_write16_buf_2d(lcd_line_buffer, width, lines_to_send);
        }
        else
        {
            lcd_blit(lcd_line_buffer, x, y + row, width, lines_to_send);
        }
    }
    if (full_frame)
    {
        lcd_release();
    }
    return;
#else
    if (lcd_mode == LCD_MODE_PSRAM)
    {
        for (uint16_t row = 0; row < height; row += LCD_CHUNK_LINES)
        {
            uint16_t lines_to_send = (row + LCD_CHUNK_LINES > height) ? (height - row) : LCD_CHUNK_LINES;
            uint8_t psram_row_buffer[DISPLAY_WIDTH];
            for (uint16_t line = 0; line < lines_to_send; line++)
            {
                uint32_t psram_addr = PSRAM_FRAMEBUFFER_ADDR + ((y + row + line) * PSRAM_ROW_SIZE) + x;
                uint32_t remaining = width, offset = 0;
                while (remaining > 0)
                {
                    uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
                    psram_qspi_read(&psram_instance, psram_addr + offset, psram_row_buffer + offset, chunk_size);
                    offset += chunk_size;
                    remaining -= chunk_size;
                }

                for (uint16_t col = 0; col < width; col++)
                {
                    size_t buf_index = (size_t)line * width + col;
                    lcd_line_buffer[buf_index] = palette[psram_row_buffer[col]];
                }
            }
            lcd_blit(lcd_line_buffer, x, y + row, width, lines_to_send);
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        for (uint16_t row = 0; row < height; row += LCD_CHUNK_LINES)
        {
            uint16_t lines_to_send = (row + LCD_CHUNK_LINES > height) ? (height - row) : LCD_CHUNK_LINES;
            for (uint16_t line = 0; line < lines_to_send; line++)
            {
                uint8_t *heap_row = (uint8_t *)&heap_framebuffer[(size_t)(y + row + line) * DISPLAY_WIDTH + x];
                for (uint16_t col = 0; col < width; col++)
                {
                    size_t buf_index = (size_t)line * width + col;
                    lcd_line_buffer[buf_index] = palette[heap_row[col]];
                }
            }
            lcd_blit(lcd_line_buffer, x, y + row, width, lines_to_send);
        }
    }
#endif
}

// ---------------------------------------------------------------------------
// Drawing primitives
// ---------------------------------------------------------------------------

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= DISPLAY_WIDTH || y >= DISPLAY_HEIGHT)
        return;

    write_framebuffer_pixel(x, y, rgb565_to_lcd_pixel(color));
}

void lcd_fill(uint16_t color)
{
    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        clear_psram_framebuffer(pixel);
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
#if defined(PICOCALC_ESP32_P4)
        if (ppa_fill_heap_rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, color))
        {
            return;
        }
        uint32_t fill_value = ((uint32_t)color << 16) | color;
        uint32_t *framebuffer_words = (uint32_t *)heap_framebuffer;
        for (size_t i = 0; i < HEAP_FRAMEBUFFER_BYTES / sizeof(uint32_t); i++)
        {
            framebuffer_words[i] = fill_value;
        }
#else
        memset(heap_framebuffer, pixel, HEAP_FRAMEBUFFER_BYTES);
#endif
    }
}

void picocalc_lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
{
    if (!buffer)
        return;

    int src_x = (x < 0) ? -(int)x : 0;
    int src_y = (y < 0) ? -(int)y : 0;
    int dst_x = (x < 0) ? 0 : (int)x;
    int dst_y = (y < 0) ? 0 : (int)y;
    int copy_width = (int)width - src_x;
    int copy_height = (int)height - src_y;

    if (dst_x + copy_width > DISPLAY_WIDTH)
        copy_width = DISPLAY_WIDTH - dst_x;
    if (dst_y + copy_height > DISPLAY_HEIGHT)
        copy_height = DISPLAY_HEIGHT - dst_y;
    if (copy_width <= 0 || copy_height <= 0)
        return;

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        for (int row = 0; row < copy_height; row++)
        {
            int src_row_start = (src_y + row) * (int)width + src_x;
            for (int col = 0; col < copy_width; col++)
            {
                line_buffer[col] = rgb332_to_lcd_pixel(buffer[src_row_start + col]);
            }
            psram_write_span(dst_x, dst_y + row, line_buffer, (size_t)copy_width);
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        for (int row = 0; row < copy_height; row++)
        {
            int src_row_start = (src_y + row) * (int)width + src_x;
            lcd_pixel_t *dst_row = &heap_framebuffer[(size_t)(dst_y + row) * DISPLAY_WIDTH + dst_x];
            for (int col = 0; col < copy_width; col++)
            {
                dst_row[col] = rgb332_to_lcd_pixel(buffer[src_row_start + col]);
            }
        }
    }
}

void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer)
{
    if (!buffer)
        return;

    int src_x = (x < 0) ? -(int)x : 0;
    int src_y = (y < 0) ? -(int)y : 0;
    int dst_x = (x < 0) ? 0 : (int)x;
    int dst_y = (y < 0) ? 0 : (int)y;
    int copy_width = (int)width - src_x;
    int copy_height = (int)height - src_y;

    if (dst_x + copy_width > DISPLAY_WIDTH)
        copy_width = DISPLAY_WIDTH - dst_x;
    if (dst_y + copy_height > DISPLAY_HEIGHT)
        copy_height = DISPLAY_HEIGHT - dst_y;
    if (copy_width <= 0 || copy_height <= 0)
        return;

    if (lcd_mode == LCD_MODE_PSRAM)
        picoware_write_buffer_fb_16(&psram_instance, dst_x, dst_y, copy_width, copy_height, buffer);
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        picoware_write_buffer_fb_16(NULL, dst_x, dst_y, copy_width, copy_height, buffer);
}

void lcd_blit_mask(int16_t dst_x, int16_t dst_y, uint16_t dst_w, uint16_t dst_h,
                   uint16_t src_w, uint16_t src_h, const uint8_t *buffer, const uint8_t *mask)
{
    if (!buffer || !mask || !dst_w || !dst_h || !src_w || !src_h)
        return;
    if (src_w == dst_w && src_h == dst_h)
    {
        const int src_x = dst_x < 0 ? -(int32_t)dst_x : 0;
        const int src_y = dst_y < 0 ? -(int32_t)dst_y : 0;
        const int dxx = dst_x < 0 ? 0 : dst_x;
        const int dyy = dst_y < 0 ? 0 : dst_y;
        int copy_width = (int)dst_w - src_x;
        int copy_height = (int)dst_h - src_y;
        if (dxx + copy_width > DISPLAY_WIDTH)
            copy_width = DISPLAY_WIDTH - dxx;
        if (dyy + copy_height > DISPLAY_HEIGHT)
            copy_height = DISPLAY_HEIGHT - dyy;
        if (copy_width <= 0 || copy_height <= 0)
            return;
        if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer == NULL)
            return;

#if defined(PICOCALC_ESP32_P4)
        if (lcd_mode == LCD_MODE_HEAP &&
            ppa_blend_masked_rgb332(dxx, dyy, src_x, src_y, copy_width, copy_height,
                                    src_w, buffer, mask))
        {
            return;
        }
#endif

        for (int row = 0; row < copy_height; ++row)
        {
            const uint32_t src_row = (uint32_t)(src_y + row) * src_w + src_x;
            int col = 0;
            while (col < copy_width)
            {
                while (col < copy_width && !(mask[(src_row + col) >> 3] & (0x80u >> ((src_row + col) & 7))))
                    ++col;
                const int start = col;
                while (col < copy_width && (mask[(src_row + col) >> 3] & (0x80u >> ((src_row + col) & 7))))
                    ++col;
                if (start == col)
                    continue;
                const uint8_t *source = buffer + src_row + start;
                const size_t length = (size_t)(col - start);
                for (size_t i = 0; i < length; i++)
                {
                    line_buffer[i] = rgb332_to_lcd_pixel(source[i]);
                }
                if (lcd_mode == LCD_MODE_HEAP)
                    memcpy(&heap_framebuffer[(size_t)(dyy + row) * DISPLAY_WIDTH + dxx + start],
                           line_buffer, length * LCD_PIXEL_BYTES);
                else if (lcd_mode == LCD_MODE_PSRAM)
                    psram_write_span(dxx + start, dyy + row, line_buffer, length);
            }
        }
        return;
    }

    // Keep nearest-neighbor sampling for resized masked sprites.
    const int offset_x = dst_x < 0 ? -(int32_t)dst_x : 0;
    const int offset_y = dst_y < 0 ? -(int32_t)dst_y : 0;
    const int dxx = dst_x < 0 ? 0 : dst_x, dyy = dst_y < 0 ? 0 : dst_y;
    int cw = (int)dst_w - offset_x, ch = (int)dst_h - offset_y;
    if (dxx + cw > DISPLAY_WIDTH)
        cw = DISPLAY_WIDTH - dxx;
    if (dyy + ch > DISPLAY_HEIGHT)
        ch = DISPLAY_HEIGHT - dyy;
    if (cw <= 0 || ch <= 0)
        return;

    for (int dr = 0; dr < ch; ++dr)
    {
        const uint32_t sy = ((uint32_t)dr + offset_y) * src_h / dst_h;
        const uint32_t buf_row = sy * src_w;
        const int fb_y = dyy + dr;
        uint32_t numerator = (uint32_t)offset_x * src_w;
        if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        {
            lcd_pixel_t *dst_row = &heap_framebuffer[(size_t)fb_y * DISPLAY_WIDTH + dxx];
            for (int dc = 0; dc < cw; ++dc)
            {
                const uint32_t pixel = buf_row + numerator / dst_w;
                numerator += src_w;
                if (mask[pixel >> 3] & (0x80u >> (pixel & 7)))
                    dst_row[dc] = rgb332_to_lcd_pixel(buffer[pixel]);
            }
        }
        else if (lcd_mode == LCD_MODE_PSRAM)
        {
            // A bounded row buffer batches opaque spans without touching transparent pixels.
            int start = 0, length = 0;
            for (int dc = 0; dc <= cw; ++dc)
            {
                bool opaque = false;
                uint32_t pixel = 0;
                if (dc < cw)
                {
                    pixel = buf_row + numerator / dst_w;
                    numerator += src_w;
                    opaque = (mask[pixel >> 3] & (0x80u >> (pixel & 7))) != 0;
                }
                if (opaque)
                {
                    if (!length)
                        start = dc;
                    line_buffer[length++] = rgb332_to_lcd_pixel(buffer[pixel]);
                }
                if (length && (!opaque || length == PSRAM_CHUNK_SIZE))
                {
                    psram_write_span(dxx + start, fb_y, line_buffer, (size_t)length);
                    length = 0;
                }
            }
        }
        else
            return;
    }
}

void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);
    int ix1 = (int)x1, iy1 = (int)y1, ix2 = (int)x2, iy2 = (int)y2;

    // Fast path – horizontal line
    if (iy1 == iy2)
    {
        if (ix1 > ix2)
        {
            int t = ix1;
            ix1 = ix2;
            ix2 = t;
        }
        if (lcd_mode == LCD_MODE_PSRAM)
            psram_write_hline(ix1, iy1, ix2 - ix1 + 1, pixel);
        else
            heap_write_hline(ix1, iy1, ix2 - ix1 + 1, pixel);
        return;
    }

    // Bresenham's line algorithm
    int dx = abs(ix2 - ix1), dy = abs(iy2 - iy1);
    int sx = (ix1 < ix2) ? 1 : -1;
    int sy = (iy1 < iy2) ? 1 : -1;
    int err = dx - dy;

    while (true)
    {
        if (ix1 >= 0 && ix1 < DISPLAY_WIDTH && iy1 >= 0 && iy1 < DISPLAY_HEIGHT)
        {
            write_framebuffer_pixel(ix1, iy1, pixel);
        }

        if (ix1 == ix2 && iy1 == iy2)
            break;

        int e2 = 2 * err;
        if (e2 > -dy)
        {
            err -= dy;
            ix1 += sx;
        }
        if (e2 < dx)
        {
            err += dx;
            iy1 += sy;
        }
    }
}

void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    lcd_draw_line(x, y, x + width - 1, y, color);                           // top
    lcd_draw_line(x, y + height - 1, x + width - 1, y + height - 1, color); // bottom
    lcd_draw_line(x, y, x, y + height - 1, color);                          // left
    lcd_draw_line(x + width - 1, y, x + width - 1, y + height - 1, color);  // right
}

void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    int ix = (int)x, iy = (int)y, iw = (int)width, ih = (int)height;

    if (ix < 0)
    {
        iw += ix;
        ix = 0;
    }
    if (iy < 0)
    {
        ih += iy;
        iy = 0;
    }
    if (ix + iw > DISPLAY_WIDTH)
        iw = DISPLAY_WIDTH - ix;
    if (iy + ih > DISPLAY_HEIGHT)
        ih = DISPLAY_HEIGHT - iy;
    if (iw <= 0 || ih <= 0)
        return;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        for (int py = iy; py < iy + ih; py++)
        {
            psram_write_hline(ix, py, iw, pixel);
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
#if defined(PICOCALC_ESP32_P4)
        if (ppa_fill_heap_rect((uint16_t)ix, (uint16_t)iy, (uint16_t)iw, (uint16_t)ih, color))
        {
            return;
        }
#endif
        for (int py = iy; py < iy + ih; py++)
            heap_write_hline(ix, py, iw, pixel);
    }
}

void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    if (radius == 0)
        return;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);
    int cx = (int)center_x, cy = (int)center_y, r = (int)radius;
    int xv = 0, yv = r, d = 3 - 2 * r;

    while (xv <= yv)
    {
        int pts[8][2] = {
            {cx + xv, cy + yv},
            {cx - xv, cy + yv},
            {cx + xv, cy - yv},
            {cx - xv, cy - yv},
            {cx + yv, cy + xv},
            {cx - yv, cy + xv},
            {cx + yv, cy - xv},
            {cx - yv, cy - xv},
        };
        for (int i = 0; i < 8; i++)
        {
            int px = pts[i][0], py = pts[i][1];
            if (px >= 0 && px < DISPLAY_WIDTH && py >= 0 && py < DISPLAY_HEIGHT)
            {
                write_framebuffer_pixel(px, py, pixel);
            }
        }

        if (d < 0)
            d += 4 * xv + 6;
        else
        {
            d += 4 * (xv - yv) + 10;
            yv--;
        }
        xv++;
    }
}

void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    if (radius == 0)
        return;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);
    int cx = (int)center_x, cy = (int)center_y, r = (int)radius;
    int xv = 0, yv = r, d = 3 - 2 * r;

    while (xv <= yv)
    {
        if (lcd_mode == LCD_MODE_PSRAM)
        {
            psram_write_hline(cx - xv, cy + yv, 2 * xv + 1, pixel);
            psram_write_hline(cx - xv, cy - yv, 2 * xv + 1, pixel);
            psram_write_hline(cx - yv, cy + xv, 2 * yv + 1, pixel);
            psram_write_hline(cx - yv, cy - xv, 2 * yv + 1, pixel);
        }
        else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        {
            heap_write_hline(cx - xv, cy + yv, 2 * xv + 1, pixel);
            heap_write_hline(cx - xv, cy - yv, 2 * xv + 1, pixel);
            heap_write_hline(cx - yv, cy + xv, 2 * yv + 1, pixel);
            heap_write_hline(cx - yv, cy - xv, 2 * yv + 1, pixel);
        }

        if (d < 0)
            d += 4 * xv + 6;
        else
        {
            d += 4 * (xv - yv) + 10;
            yv--;
        }
        xv++;
    }
}

void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                       uint16_t x3, uint16_t y3, uint16_t color)
{
    float p1_x = (float)x1, p1_y = (float)y1;
    float p2_x = (float)x2, p2_y = (float)y2;
    float p3_x = (float)x3, p3_y = (float)y3;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);

    // Sort vertices by Y (p1.y <= p2.y <= p3.y)
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

    int iy1 = (int)p1_y, iy2 = (int)p2_y, iy3 = (int)p3_y;
    if (iy1 == iy3)
        return;

    for (int scanY = iy1; scanY <= iy3; scanY++)
    {
        if (scanY < 0 || scanY >= DISPLAY_HEIGHT)
            continue;

        float x_long = p1_x + (p3_x - p1_x) * (scanY - iy1) / (float)(iy3 - iy1);
        float x_short;

        if (scanY <= iy2)
            x_short = (iy2 != iy1)
                          ? p1_x + (p2_x - p1_x) * (scanY - iy1) / (float)(iy2 - iy1)
                          : p1_x;
        else
            x_short = (iy3 != iy2)
                          ? p2_x + (p3_x - p2_x) * (scanY - iy2) / (float)(iy3 - iy2)
                          : p2_x;

        int start_x = (int)(x_long < x_short ? x_long : x_short);
        int end_x = (int)(x_long > x_short ? x_long : x_short);

        if (lcd_mode == LCD_MODE_PSRAM)
            psram_write_hline(start_x, scanY, end_x - start_x + 1, pixel);
        else
            heap_write_hline(start_x, scanY, end_x - start_x + 1, pixel);
    }
}

void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color, uint8_t alpha)
{
    if (alpha == 0)
        return;

    if (alpha == 255)
    {
        lcd_fill_triangle(x1, y1, x2, y2, x3, y3, color);
        return;
    }

    // Extract source RGB565 components
    uint8_t sr = (color >> 11) & 0x1F;
    uint8_t sg = (color >> 5) & 0x3F;
    uint8_t sb = color & 0x1F;
    uint8_t inv_alpha = 255 - alpha;

    // Sort vertices by Y (p1 top, p3 bottom)
    if (y1 > y2)
    {
        uint16_t t;
        t = x1;
        x1 = x2;
        x2 = t;
        t = y1;
        y1 = y2;
        y2 = t;
    }
    if (y1 > y3)
    {
        uint16_t t;
        t = x1;
        x1 = x3;
        x3 = t;
        t = y1;
        y1 = y3;
        y3 = t;
    }
    if (y2 > y3)
    {
        uint16_t t;
        t = x2;
        x2 = x3;
        x3 = t;
        t = y2;
        y2 = y3;
        y3 = t;
    }

    uint16_t total_h = y3 - y1;
    if (total_h == 0)
        return;

    for (uint16_t i = 0; i < total_h; i++)
    {
        bool second_half = i > y2 - y1 || y2 == y1;
        uint16_t seg_h = second_half ? y3 - y2 : y2 - y1;
        float t = (float)i / total_h;
        float beta = (float)(i - (second_half ? y2 - y1 : 0)) / seg_h;

        int ax = (int)(x1 + (float)((int)x3 - (int)x1) * t);
        int bx = second_half
                     ? (int)(x2 + (float)((int)x3 - (int)x2) * beta)
                     : (int)(x1 + (float)((int)x2 - (int)x1) * beta);

        if (ax > bx)
        {
            int tmp = ax;
            ax = bx;
            bx = tmp;
        }

        int cur_y = y1 + i;
        if (cur_y < 0 || cur_y >= DISPLAY_HEIGHT)
            continue;

        // Clip to screen bounds
        if (ax < 0)
            ax = 0;
        if (bx >= DISPLAY_WIDTH)
            bx = DISPLAY_WIDTH - 1;
        int seg_width = bx - ax + 1;
        if (seg_width <= 0)
            continue;

        if (lcd_mode == LCD_MODE_PSRAM)
        {
            psram_read_span(ax, cur_y, line_buffer, (size_t)seg_width);

            // Alpha blend each pixel in place
            for (int j = 0; j < seg_width; j++)
            {
                uint16_t dst_color = lcd_pixel_to_rgb565(line_buffer[j]);
                uint8_t dr = (dst_color >> 11) & 0x1F;
                uint8_t dg = (dst_color >> 5) & 0x3F;
                uint8_t db = dst_color & 0x1F;

                uint8_t br = (uint8_t)((sr * alpha + dr * inv_alpha) / 255);
                uint8_t bg = (uint8_t)((sg * alpha + dg * inv_alpha) / 255);
                uint8_t bb = (uint8_t)((sb * alpha + db * inv_alpha) / 255);

                uint16_t blended = ((uint16_t)br << 11) | ((uint16_t)bg << 5) | bb;
                line_buffer[j] = rgb565_to_lcd_pixel(blended);
            }
            psram_write_span(ax, cur_y, line_buffer, (size_t)seg_width);
        }
        else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        {
            lcd_pixel_t *row = &heap_framebuffer[(size_t)cur_y * DISPLAY_WIDTH + ax];
            for (int j = 0; j < seg_width; j++)
            {
                uint16_t dst_color = lcd_pixel_to_rgb565(row[j]);
                uint8_t dr = (dst_color >> 11) & 0x1F;
                uint8_t dg = (dst_color >> 5) & 0x3F;
                uint8_t db = dst_color & 0x1F;

                uint8_t br = (uint8_t)((sr * alpha + dr * inv_alpha) / 255);
                uint8_t bg = (uint8_t)((sg * alpha + dg * inv_alpha) / 255);
                uint8_t bb = (uint8_t)((sb * alpha + db * inv_alpha) / 255);

                uint16_t blended = ((uint16_t)br << 11) | ((uint16_t)bg << 5) | bb;
                row[j] = rgb565_to_lcd_pixel(blended);
            }
        }
    }
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                       uint16_t x3, uint16_t y3, uint16_t color)
{
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
}

void lcd_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    if (count < 2)
        return;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);
    int ix1 = (int)x[count - 1], iy1 = (int)y[count - 1];

    for (int i = 0; i < count; i++)
    {
        int ix2 = (int)x[i], iy2 = (int)y[i];

        // Fast path - horizontal edge
        if (iy1 == iy2)
        {
            int ax = (ix1 < ix2) ? ix1 : ix2;
            int bx = (ix1 < ix2) ? ix2 : ix1;
            if (lcd_mode == LCD_MODE_PSRAM)
                psram_write_hline(ax, iy1, bx - ax + 1, pixel);
            else
                heap_write_hline(ax, iy1, bx - ax + 1, pixel);
        }
        else // Bresenham's line algorithm
        {
            int dx = abs(ix2 - ix1), dy = abs(iy2 - iy1);
            int sx = (ix1 < ix2) ? 1 : -1;
            int sy = (iy1 < iy2) ? 1 : -1;
            int err = dx - dy;

            while (true)
            {
                if (ix1 >= 0 && ix1 < DISPLAY_WIDTH && iy1 >= 0 && iy1 < DISPLAY_HEIGHT)
                {
                    write_framebuffer_pixel(ix1, iy1, pixel);
                }

                if (ix1 == ix2 && iy1 == iy2)
                    break;

                int e2 = 2 * err;
                if (e2 > -dy)
                {
                    err -= dy;
                    ix1 += sx;
                }
                if (e2 < dx)
                {
                    err += dx;
                    iy1 += sy;
                }
            }
        }

        ix1 = ix2;
        iy1 = iy2;
    }
}

void lcd_fill_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    if (count < 3)
        return;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);

    // Edge x at top vertex (14.14 fixed point), row step, vertex levels
    int xtop[count], dxf[count], ys[count];

    for (int i = 0; i < count; i++)
    {
        int j = (i + 1 == count) ? 0 : i + 1;
        int y0 = (int)y[i], y1 = (int)y[j], x0 = (int)x[i], x1 = (int)x[j];
        int top_x = (y0 <= y1) ? x0 : x1;
        int bot_x = (y0 <= y1) ? x1 : x0;
        int rows = (y0 <= y1) ? (y1 - y0) : (y0 - y1);

        xtop[i] = top_x << 14;
        dxf[i] = rows ? (int)(((int64_t)(bot_x - top_x) << 14) / rows) : 0;
        ys[i] = (int)y[i];
    }

    // Sort vertex levels
    for (int a = 1; a < count; a++)
    {
        int v = ys[a], b = a - 1;
        while (b >= 0 && ys[b] > v)
        {
            ys[b + 1] = ys[b];
            b--;
        }
        ys[b + 1] = v;
    }

    int xa[count], dxa[count], xs[count];

    // Horizontal cut at every vertex: sides stay straight inside a band
    for (int b = 0; b + 1 < count; b++)
    {
        int ya = ys[b], yb = ys[b + 1];
        if (ya == yb)
            continue;

        int row0 = (ya < 0) ? 0 : ya;
        int row1 = (yb > DISPLAY_HEIGHT) ? DISPLAY_HEIGHT : yb;
        if (row0 >= row1)
            continue;

        // Sides crossing this band, x at first row
        int n = 0;
        for (int i = 0; i < count; i++)
        {
            int j = (i + 1 == count) ? 0 : i + 1;
            int y0 = (int)y[i], y1 = (int)y[j];
            int top = (y0 < y1) ? y0 : y1;
            int bot = (y0 < y1) ? y1 : y0;

            if (top <= ya && bot > ya)
            {
                xa[n] = xtop[i] + (row0 - top) * dxf[i];
                dxa[n] = dxf[i];
                n++;
            }
        }

        if (n < 2)
            continue;

        // Order sides once (equal x: flatter side is left)
        for (int a = 1; a < n; a++)
        {
            int v = xa[a], s = dxa[a], k = a - 1;
            while (k >= 0 && (xa[k] > v || (xa[k] == v && dxa[k] > s)))
            {
                xa[k + 1] = xa[k];
                dxa[k + 1] = dxa[k];
                k--;
            }
            xa[k + 1] = v;
            dxa[k + 1] = s;
        }

        if (n == 2)
        {
            // Two sides: trace both with Bresenham steps
            int xl = xa[0], xr = xa[1], dl = dxa[0], dr = dxa[1];

            for (int py = row0; py < row1; py++)
            {
                int ax = xl >> 14, bx = xr >> 14;
                xl += dl;
                xr += dr;

                if (bx < 0 || ax >= DISPLAY_WIDTH || bx < ax)
                    continue;
                if (ax < 0)
                    ax = 0;
                if (bx >= DISPLAY_WIDTH)
                    bx = DISPLAY_WIDTH - 1;

                if (lcd_mode == LCD_MODE_PSRAM)
                    psram_write_hline(ax, py, bx - ax + 1, pixel);
                else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
                    heap_write_hline(ax, py, bx - ax + 1, pixel);
            }
            continue;
        }

        for (int py = row0; py < row1; py++)
        {
            for (int k = 0; k < n; k++)
            {
                xs[k] = xa[k] >> 14;
                xa[k] += dxa[k];
            }

            // Sides keep order; re-sort if a crossing flipped them
            bool ordered = true;
            for (int k = 1; k < n; k++)
                if (xs[k] < xs[k - 1])
                {
                    ordered = false;
                    break;
                }

            if (!ordered)
                for (int a = 1; a < n; a++)
                {
                    int v = xs[a], k = a - 1;
                    while (k >= 0 && xs[k] > v)
                    {
                        xs[k + 1] = xs[k];
                        k--;
                    }
                    xs[k + 1] = v;
                }

            for (int k = 0; k + 1 < n; k += 2)
            {
                int ax = xs[k], bx = xs[k + 1];
                if (bx < 0 || ax >= DISPLAY_WIDTH || bx < ax)
                    continue;
                if (ax < 0)
                    ax = 0;
                if (bx >= DISPLAY_WIDTH)
                    bx = DISPLAY_WIDTH - 1;

                if (lcd_mode == LCD_MODE_PSRAM)
                    psram_write_hline(ax, py, bx - ax + 1, pixel);
                else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
                    heap_write_hline(ax, py, bx - ax + 1, pixel);
            }
        }
    }
}

void lcd_fill_polygon_alpha(uint16_t x[], uint16_t y[], int count,
                            uint16_t color, uint8_t alpha)
{
    if (count < 3 || alpha == 0)
        return;

    if (alpha == 255)
    {
        lcd_fill_polygon(x, y, count, color);
        return;
    }

    // Extract source RGB565 components
    uint8_t sr = (color >> 11) & 0x1F;
    uint8_t sg = (color >> 5) & 0x3F;
    uint8_t sb = color & 0x1F;
    uint8_t inv_alpha = 255 - alpha;

    // Edge x at top vertex (14.14 fixed point), row step, vertex levels
    int xtop[count], dxf[count], ys[count];

    for (int i = 0; i < count; i++)
    {
        int j = (i + 1 == count) ? 0 : i + 1;
        int y0 = (int)y[i], y1 = (int)y[j], x0 = (int)x[i], x1 = (int)x[j];
        int top_x = (y0 <= y1) ? x0 : x1;
        int bot_x = (y0 <= y1) ? x1 : x0;
        int rows = (y0 <= y1) ? (y1 - y0) : (y0 - y1);

        xtop[i] = top_x << 14;
        dxf[i] = rows ? (int)(((int64_t)(bot_x - top_x) << 14) / rows) : 0;
        ys[i] = (int)y[i];
    }

    // Sort vertex levels
    for (int a = 1; a < count; a++)
    {
        int v = ys[a], b = a - 1;
        while (b >= 0 && ys[b] > v)
        {
            ys[b + 1] = ys[b];
            b--;
        }
        ys[b + 1] = v;
    }

    int xa[count], dxa[count], xs[count];

    // Horizontal cut at every vertex: sides stay straight inside a band
    for (int b = 0; b + 1 < count; b++)
    {
        int ya = ys[b], yb = ys[b + 1];
        if (ya == yb)
            continue;

        int row0 = (ya < 0) ? 0 : ya;
        int row1 = (yb > DISPLAY_HEIGHT) ? DISPLAY_HEIGHT : yb;
        if (row0 >= row1)
            continue;

        // Sides crossing this band, x at first row
        int n = 0;
        for (int i = 0; i < count; i++)
        {
            int j = (i + 1 == count) ? 0 : i + 1;
            int y0 = (int)y[i], y1 = (int)y[j];
            int top = (y0 < y1) ? y0 : y1;
            int bot = (y0 < y1) ? y1 : y0;

            if (top <= ya && bot > ya)
            {
                xa[n] = xtop[i] + (row0 - top) * dxf[i];
                dxa[n] = dxf[i];
                n++;
            }
        }

        if (n < 2)
            continue;

        // Order sides once (equal x: flatter side is left)
        for (int a = 1; a < n; a++)
        {
            int v = xa[a], s = dxa[a], k = a - 1;
            while (k >= 0 && (xa[k] > v || (xa[k] == v && dxa[k] > s)))
            {
                xa[k + 1] = xa[k];
                dxa[k + 1] = dxa[k];
                k--;
            }
            xa[k + 1] = v;
            dxa[k + 1] = s;
        }

        for (int py = row0; py < row1; py++)
        {
            for (int k = 0; k < n; k++)
            {
                xs[k] = xa[k] >> 14;
                xa[k] += dxa[k];
            }

            // Sides keep order; re-sort if a crossing flipped them
            bool ordered = true;
            for (int k = 1; k < n; k++)
                if (xs[k] < xs[k - 1])
                {
                    ordered = false;
                    break;
                }

            if (!ordered)
                for (int a = 1; a < n; a++)
                {
                    int v = xs[a], k = a - 1;
                    while (k >= 0 && xs[k] > v)
                    {
                        xs[k + 1] = xs[k];
                        k--;
                    }
                    xs[k + 1] = v;
                }

            for (int k = 0; k + 1 < n; k += 2)
            {
                int ax = xs[k], bx = xs[k + 1];
                if (bx < 0 || ax >= DISPLAY_WIDTH || bx < ax)
                    continue;
                if (ax < 0)
                    ax = 0;
                if (bx >= DISPLAY_WIDTH)
                    bx = DISPLAY_WIDTH - 1;

                int span = bx - ax + 1;

                if (lcd_mode == LCD_MODE_PSRAM)
                {
                    psram_read_span(ax, py, line_buffer, (size_t)span);
                }
                else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
                {
                    memcpy(line_buffer, &heap_framebuffer[(size_t)py * DISPLAY_WIDTH + ax],
                           (size_t)span * LCD_PIXEL_BYTES);
                }
                else
                    continue;

                // Alpha blend the span in the line buffer
                for (int j = 0; j < span; j++)
                {
                    uint16_t dst_color = lcd_pixel_to_rgb565(line_buffer[j]);
                    uint8_t dr = (dst_color >> 11) & 0x1F;
                    uint8_t dg = (dst_color >> 5) & 0x3F;
                    uint8_t db = dst_color & 0x1F;

                    uint8_t br = (uint8_t)((sr * alpha + dr * inv_alpha) / 255);
                    uint8_t bg = (uint8_t)((sg * alpha + dg * inv_alpha) / 255);
                    uint8_t bb = (uint8_t)((sb * alpha + db * inv_alpha) / 255);

                    line_buffer[j] = rgb565_to_lcd_pixel(((uint16_t)br << 11) | ((uint16_t)bg << 5) | bb);
                }

                if (lcd_mode == LCD_MODE_PSRAM)
                {
                    psram_write_span(ax, py, line_buffer, (size_t)span);
                }
                else
                {
                    memcpy(&heap_framebuffer[(size_t)py * DISPLAY_WIDTH + ax], line_buffer,
                           (size_t)span * LCD_PIXEL_BYTES);
                }
            }
        }
    }
}

void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                              uint16_t radius, uint16_t color)
{
    int ix = (int)x, iy = (int)y, iw = (int)width, ih = (int)height, r = (int)radius;

    if (iw <= 0 || ih <= 0 || r <= 0)
        return;

    if (ix < 0)
    {
        iw += ix;
        ix = 0;
    }
    if (iy < 0)
    {
        ih += iy;
        iy = 0;
    }
    if (ix + iw > DISPLAY_WIDTH)
        iw = DISPLAY_WIDTH - ix;
    if (iy + ih > DISPLAY_HEIGHT)
        ih = DISPLAY_HEIGHT - iy;
    if (iw <= 0 || ih <= 0)
        return;

    if (r > iw / 2)
        r = iw / 2;
    if (r > ih / 2)
        r = ih / 2;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);

    int tl_cx = ix + r, tl_cy = iy + r;
    int tr_cx = ix + iw - r, tr_cy = iy + r;
    int bl_cx = ix + r, bl_cy = iy + ih - r;
    int br_cx = ix + iw - r, br_cy = iy + ih - r;
    int rsq = r * r;

    for (int py = iy; py < iy + ih; py++)
    {
        for (int px = ix; px < ix + iw; px++)
        {
            bool in_corner = false;

            if (px < tl_cx && py < tl_cy)
            {
                int dx = px - tl_cx, dy = py - tl_cy;
                if (dx * dx + dy * dy > rsq)
                    in_corner = true;
            }
            else if (px >= tr_cx && py < tr_cy)
            {
                int dx = px - tr_cx, dy = py - tr_cy;
                if (dx * dx + dy * dy > rsq)
                    in_corner = true;
            }
            else if (px < bl_cx && py >= bl_cy)
            {
                int dx = px - bl_cx, dy = py - bl_cy;
                if (dx * dx + dy * dy > rsq)
                    in_corner = true;
            }
            else if (px >= br_cx && py >= br_cy)
            {
                int dx = px - br_cx, dy = py - br_cy;
                if (dx * dx + dy * dy > rsq)
                    in_corner = true;
            }

            if (!in_corner)
            {
                write_framebuffer_pixel(px, py, pixel);
            }
        }
    }
}

void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size)
{
    int char_code = (int)(unsigned char)c;
    if (char_code < 32 || char_code > 126)
        return;

    uint8_t char_width = font_get_width(size);
    uint8_t char_height = font_get_height(size);
    uint8_t bytes_per_row = (char_width + 7) / 8;

    if ((int)x + char_width > DISPLAY_WIDTH || (int)y + char_height > DISPLAY_HEIGHT)
        return;

    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);
    const uint8_t *char_data = font_get_character(size, char_code);
    if (!char_data)
        return;

    for (uint8_t row = 0; row < char_height; row++)
    {
        const uint8_t *row_data = &char_data[row * bytes_per_row];
        for (uint8_t col = 0; col < char_width; col++)
        {
            uint8_t byte_index = col / 8;
            uint8_t bit_index = 7 - (col % 8);

            if (row_data[byte_index] & (1 << bit_index))
            {
                int px = (int)x + col, py = (int)y + row;
                write_framebuffer_pixel(px, py, pixel);
            }
        }
    }
}

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size)
{
    if (!text)
        return;

    uint8_t char_width = font_get_width(size);
    uint8_t char_height = font_get_height(size);
    uint8_t bytes_per_row = (char_width + 7) / 8;
    uint8_t char_spacing = char_width + 1;
    lcd_pixel_t pixel = rgb565_to_lcd_pixel(color);

    const uint8_t *font_data = font_get_data(size);

    int current_x = (int)x, current_y = (int)y;

    for (const char *p = text; *p != '\0'; p++)
    {
        char ch = *p;

        if (ch == '\n')
        {
            current_x = (int)x;
            current_y += char_height;
            continue;
        }
        if (ch == ' ')
        {
            current_x += char_spacing;
            continue;
        }

        if (current_y + char_height > DISPLAY_HEIGHT)
            break;

        if (current_x + char_width > DISPLAY_WIDTH)
        {
            current_x = (int)x;
            current_y += char_height;
            if (current_y + char_height > DISPLAY_HEIGHT)
                break;
        }

        int char_code = (int)(unsigned char)ch;
        if (char_code < 32 || char_code > 126)
            char_code = 32;

        const uint8_t *char_data = &font_data[(char_code - 32) * char_height * bytes_per_row];

        for (uint8_t row = 0; row < char_height; row++)
        {
            const uint8_t *row_data = &char_data[row * bytes_per_row];
            for (uint8_t col = 0; col < char_width; col++)
            {
                uint8_t byte_index = col / 8;
                uint8_t bit_index = 7 - (col % 8);

                if (row_data[byte_index] & (1 << bit_index))
                {
                    int px = current_x + col, py = current_y + row;
                    if (px < DISPLAY_WIDTH && py < DISPLAY_HEIGHT)
                    {
                        write_framebuffer_pixel(px, py, pixel);
                    }
                }
            }
        }

        current_x += char_spacing;
    }
}

// ---------------------------------------------------------------------------
// Misc public helpers
// ---------------------------------------------------------------------------

void lcd_set_mode(uint8_t mode)
{
    if (mode == lcd_mode)
    {
        return; // Already in this mode
    }

    if (mode == LCD_MODE_PSRAM)
    {
        // Switch to PSRAM mode
        if (!psram_initialized)
        {
            psram_instance = PICOWARE_PSRAM_INIT();
            psram_initialized = true;
        }

        // Free HEAP buffer if it was allocated
        free_heap_framebuffer();
    }
    else if (mode == LCD_MODE_HEAP)
    {
        // Switch to HEAP mode
        if (!allocate_heap_framebuffer())
        {
            // Allocation failed, stay in PSRAM mode
            return;
        }
        // Clear the framebuffer to black
        memset(heap_framebuffer, 0, HEAP_FRAMEBUFFER_BYTES);

        // deinit psram
        if (psram_initialized)
        {
            clear_psram_framebuffer(0);
            psram_qspi_deinit(&psram_instance);
            psram_initialized = false;
        }
    }

    lcd_mode = mode;
}

uint8_t lcd_get_mode(void)
{
    return lcd_mode;
}

void lcd_psram(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint32_t addr)
{
    if (!psram_initialized)
        return;

    if (x >= DISPLAY_WIDTH || y >= DISPLAY_HEIGHT)
        return;

    uint32_t row_bytes = (uint32_t)width * 2;
    uint16_t lcd_row_buffer[width];

    for (uint16_t row = 0; row < height; row++)
    {
        uint16_t cur_y = y + row;
        if (cur_y >= DISPLAY_HEIGHT)
            break;

        uint32_t src_offset = row * row_bytes;
        uint32_t remaining = row_bytes, off = 0;
        while (remaining > 0)
        {
            uint32_t chunk = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
            psram_qspi_read(&psram_instance, addr + src_offset + off,
                            (uint8_t *)lcd_row_buffer + off, chunk);
            off += chunk;
            remaining -= chunk;
        }

        lcd_blit_16bit(x, cur_y, width, 1, lcd_row_buffer);
    }
}

bool lcd_psram_read_row(uint32_t addr, uint16_t row, uint16_t width, uint16_t *dst)
{
    if (!psram_initialized || !dst)
        return false;

    uint32_t row_bytes = (uint32_t)width * 2;
    uint32_t row_addr = addr + (uint32_t)row * row_bytes;
    uint32_t remaining = row_bytes, off = 0;
    while (remaining > 0)
    {
        uint32_t chunk = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_read(&psram_instance, row_addr + off,
                        (uint8_t *)dst + off, chunk);
        off += chunk;
        remaining -= chunk;
    }
    return true;
}

psram_qspi_inst_t *picoware_get_psram_instance(void)
{
    return psram_initialized ? &psram_instance : NULL;
}

bool lcd_read_row(uint16_t row, uint8_t *dst)
{
    if (row >= DISPLAY_HEIGHT || !dst)
        return false;
    if (lcd_mode == LCD_MODE_HEAP)
    {
        if (heap_framebuffer == NULL)
            return false;
#if defined(PICOCALC_ESP32_P4)
        const lcd_pixel_t *source = &heap_framebuffer[(size_t)row * DISPLAY_WIDTH];
        for (uint16_t col = 0; col < DISPLAY_WIDTH; col++)
        {
            dst[col] = color565_to_332(source[col]);
        }
#else
        memcpy(dst, &heap_framebuffer[(uint32_t)row * DISPLAY_WIDTH], DISPLAY_WIDTH);
#endif
        return true;
    }
    // Keep the row-read API in RGB332 even when the P4 framebuffer is RGB565.
#if defined(PICOCALC_ESP32_P4)
    psram_read_span(0, row, line_buffer, DISPLAY_WIDTH);
    for (uint16_t col = 0; col < DISPLAY_WIDTH; col++)
    {
        dst[col] = color565_to_332(line_buffer[col]);
    }
#else
    uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (uint32_t)row * PSRAM_ROW_SIZE;
    uint32_t remaining = DISPLAY_WIDTH, off = 0;
    while (remaining > 0)
    {
        uint32_t chunk = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_read(&psram_instance, addr + off, dst + off, chunk);
        off += chunk;
        remaining -= chunk;
    }
#endif
    return true;
}