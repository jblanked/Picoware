/*
 * Picoware LCD C Library
 * Copyright © 2025 JBlanked
 *
 * Uses PSRAM for framebuffer storage instead of static RAM
 */
#include "picoware_lcd.h"
#include "../picoware_psram/psram_qspi.h"
#include "../picoware_psram/picoware_psram_shared.h"
#include "py/runtime.h"

#ifndef FONT_DEFAULT
#define FONT_DEFAULT FONT_XTRA_SMALL
#endif

#define LCD_CHUNK_LINES 16

// Module state
static bool module_initialized = false;

// Line buffer for batch operations (reusable)
static uint8_t line_buffer[DISPLAY_WIDTH] __attribute__((aligned(64)));

#define LCD_MODE_PSRAM 0 // PSRAM framebuffer with RGB332 palette
#define LCD_MODE_HEAP 1  // Heap RAM framebuffer with RGB332 (converted to RGB565 on swap)

static uint8_t lcd_mode = LCD_MODE_PSRAM;

// Heap mode state
static uint8_t *heap_framebuffer = NULL;
static bool heap_framebuffer_allocated = false;
#define HEAP_BUFFER_SIZE (DISPLAY_WIDTH * DISPLAY_HEIGHT)

static uint16_t palette[256] __attribute__((aligned(64)));

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

            uint16_t rgb565 = buffer[row * width + col];
            uint8_t rgb332 = color565_to_332(rgb565);
            picoware_write_pixel_fb(psram, fb_x, fb_y, rgb332);
        }
    }
}

__force_inline static void psram_write_hline(int x, int y, int length, uint8_t color_index)
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

    uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (y * PSRAM_ROW_SIZE) + x;
    memset(line_buffer, color_index, length);

    uint32_t remaining = length, offset = 0;
    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, addr + offset, line_buffer + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

static void heap_write_hline(int x, int y, int length, uint8_t color_index)
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

    memset(&heap_framebuffer[y * DISPLAY_WIDTH + x], color_index, length);
}

static bool allocate_heap_framebuffer(void)
{
    if (heap_framebuffer == NULL)
    {
        heap_framebuffer = (uint8_t *)m_malloc(HEAP_BUFFER_SIZE);
        if (heap_framebuffer == NULL)
            return false;
        memset(heap_framebuffer, 0, HEAP_BUFFER_SIZE);
        heap_framebuffer_allocated = true;
    }
    return true;
}

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
    uint32_t fill_value = ((uint32_t)color_index << 24) | ((uint32_t)color_index << 16) | ((uint32_t)color_index << 8) | color_index;

    uint32_t word_count = PSRAM_BUFFER_SIZE / 4;
    static uint32_t fill32_buffer[PSRAM_CHUNK_SIZE / 4] __attribute__((aligned(64)));

    for (size_t i = 0; i < PSRAM_CHUNK_SIZE / 4; i++)
        fill32_buffer[i] = fill_value;

    uint32_t current_addr = PSRAM_FRAMEBUFFER_ADDR;
    uint32_t remaining = word_count;
    while (remaining > 0)
    {
        uint32_t words = (remaining > (PSRAM_CHUNK_SIZE / 4)) ? (PSRAM_CHUNK_SIZE / 4) : remaining;
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

// ---------------------------------------------------------------------------
// Public API – matches picoware_lcd.h
// ---------------------------------------------------------------------------

void picocalc_lcd_init(void)
{
    if (!module_initialized)
    {
        lcd_init();
        lcd_set_background(0x0000); // black
        lcd_set_underscore(false);
        lcd_enable_cursor(false);

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

    lcd_mode = LCD_MODE_PSRAM;

    if (!psram_initialized)
    {
        psram_instance = psram_qspi_init(pio1, -1, 1.0f);
        psram_initialized = true;
    }

    free_heap_framebuffer();
}

void lcd_deinit(void)
{
    if (module_initialized)
    {
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
    uint16_t lcd_line_buffer[DISPLAY_WIDTH * LCD_CHUNK_LINES];

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        uint8_t psram_row_buffer[DISPLAY_WIDTH];

        for (uint16_t row = 0; row < height; row += LCD_CHUNK_LINES)
        {
            uint16_t lines_to_send = (row + LCD_CHUNK_LINES > height) ? (height - row) : LCD_CHUNK_LINES;

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
                    size_t buf_index = line * width + col;
                    uint8_t pal_index = psram_row_buffer[col];
                    lcd_line_buffer[buf_index] = palette[pal_index];
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
                uint8_t *heap_row = &heap_framebuffer[(y + row + line) * DISPLAY_WIDTH + x];
                for (uint16_t col = 0; col < width; col++)
                {
                    size_t buf_index = line * width + col;
                    uint8_t pal_index = heap_row[col];
                    lcd_line_buffer[buf_index] = palette[pal_index];
                }
            }

            lcd_blit(lcd_line_buffer, x, y + row, width, lines_to_send);
        }
    }
}

// ---------------------------------------------------------------------------
// Drawing primitives
// ---------------------------------------------------------------------------

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= DISPLAY_WIDTH || y >= DISPLAY_HEIGHT)
        return;

    uint8_t color_index = color565_to_332(color);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (y * PSRAM_ROW_SIZE) + x;
        psram_qspi_write8(&psram_instance, addr, color_index);
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        heap_framebuffer[y * DISPLAY_WIDTH + x] = color_index;
    }
}

void lcd_fill(uint16_t color)
{
    uint8_t color_index = color565_to_332(color);

    if (lcd_mode == LCD_MODE_PSRAM)
        clear_psram_framebuffer(color_index);
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        memset(heap_framebuffer, color_index, HEAP_BUFFER_SIZE);
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
            uint32_t psram_addr = PSRAM_FRAMEBUFFER_ADDR + ((dst_y + row) * PSRAM_ROW_SIZE) + dst_x;
            uint32_t remaining = copy_width, offset = 0;
            while (remaining > 0)
            {
                uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
                psram_qspi_write(&psram_instance, psram_addr + offset,
                                 buffer + src_row_start + offset, chunk_size);
                offset += chunk_size;
                remaining -= chunk_size;
            }
        }
    }
    else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
    {
        for (int row = 0; row < copy_height; row++)
        {
            int src_row_start = (src_y + row) * (int)width + src_x;
            uint8_t *dst_row = &heap_framebuffer[(dst_y + row) * DISPLAY_WIDTH + dst_x];
            memcpy(dst_row, buffer + src_row_start, copy_width);
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

void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    uint8_t color_index = color565_to_332(color);
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
            psram_write_hline(ix1, iy1, ix2 - ix1 + 1, color_index);
        else
            heap_write_hline(ix1, iy1, ix2 - ix1 + 1, color_index);
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
            if (lcd_mode == LCD_MODE_PSRAM)
            {
                uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (iy1 * PSRAM_ROW_SIZE) + ix1;
                psram_qspi_write8(&psram_instance, addr, color_index);
            }
            else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
            {
                heap_framebuffer[iy1 * DISPLAY_WIDTH + ix1] = color_index;
            }
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

    uint8_t color_index = color565_to_332(color);

    if (lcd_mode == LCD_MODE_PSRAM)
    {
        memset(line_buffer, color_index, iw);
        for (int py = iy; py < iy + ih; py++)
        {
            uint32_t addr = PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + ix;
            uint32_t remaining = iw, offset = 0;
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
        for (int py = iy; py < iy + ih; py++)
            memset(&heap_framebuffer[py * DISPLAY_WIDTH + ix], color_index, iw);
    }
}

void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    if (radius == 0)
        return;

    uint8_t color_index = color565_to_332(color);
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
                if (lcd_mode == LCD_MODE_PSRAM)
                    psram_qspi_write8(&psram_instance,
                                      PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);
                else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
                    heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;
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

    uint8_t color_index = color565_to_332(color);
    int cx = (int)center_x, cy = (int)center_y, r = (int)radius;
    int xv = 0, yv = r, d = 3 - 2 * r;

    while (xv <= yv)
    {
        if (lcd_mode == LCD_MODE_PSRAM)
        {
            psram_write_hline(cx - xv, cy + yv, 2 * xv + 1, color_index);
            psram_write_hline(cx - xv, cy - yv, 2 * xv + 1, color_index);
            psram_write_hline(cx - yv, cy + xv, 2 * yv + 1, color_index);
            psram_write_hline(cx - yv, cy - xv, 2 * yv + 1, color_index);
        }
        else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
        {
            heap_write_hline(cx - xv, cy + yv, 2 * xv + 1, color_index);
            heap_write_hline(cx - xv, cy - yv, 2 * xv + 1, color_index);
            heap_write_hline(cx - yv, cy + xv, 2 * yv + 1, color_index);
            heap_write_hline(cx - yv, cy - xv, 2 * yv + 1, color_index);
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

    uint8_t color_index = color565_to_332(color);

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
            psram_write_hline(start_x, scanY, end_x - start_x + 1, color_index);
        else
            heap_write_hline(start_x, scanY, end_x - start_x + 1, color_index);
    }
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                       uint16_t x3, uint16_t y3, uint16_t color)
{
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
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

    uint8_t color_index = color565_to_332(color);

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
                if (lcd_mode == LCD_MODE_PSRAM)
                    psram_qspi_write8(&psram_instance,
                                      PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);
                else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
                    heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;
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

    uint8_t color_index = color565_to_332(color);
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
                if (lcd_mode == LCD_MODE_PSRAM)
                    psram_qspi_write8(&psram_instance,
                                      PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);
                else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
                    heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;
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
    uint8_t color_index = color565_to_332(color);

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
                        if (lcd_mode == LCD_MODE_PSRAM)
                            psram_qspi_write8(&psram_instance,
                                              PSRAM_FRAMEBUFFER_ADDR + (py * PSRAM_ROW_SIZE) + px, color_index);
                        else if (lcd_mode == LCD_MODE_HEAP && heap_framebuffer != NULL)
                            heap_framebuffer[py * DISPLAY_WIDTH + px] = color_index;
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
            psram_instance = psram_qspi_init(pio1, -1, 1.0f);
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
        memset(heap_framebuffer, 0, HEAP_BUFFER_SIZE);

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

psram_qspi_inst_t *picoware_get_psram_instance(void)
{
    return psram_initialized ? &psram_instance : NULL;
}
