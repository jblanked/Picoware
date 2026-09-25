#include "lcd.h"
#include <string.h>
#include <stdarg.h>

#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "st7789_lcd.pio.h"

#define LCD_PIO pio1
#define LCD_CHUNK_LINES 16
#define HEAP_BUFFER_SIZE (DISPLAY_WIDTH * DISPLAY_HEIGHT)

// PIO configuration
static uint lcd_pio_sm = 0;
static uint lcd_pio_offset = 0;

// Text drawing - simplified for MicroPython extension (no font support needed)
static semaphore_t lcd_sem;

// Module state
static bool module_initialized = false;

static uint8_t line_buffer[DISPLAY_WIDTH] __attribute__((aligned(4)));
static uint16_t line_buffer_16[DISPLAY_WIDTH] __attribute__((aligned(4)));
static uint16_t palette[256] __attribute__((aligned(4)));
static uint16_t lcd_line_buffer[DISPLAY_WIDTH * LCD_CHUNK_LINES] __attribute__((aligned(4)));
static uint8_t framebuffer[HEAP_BUFFER_SIZE];

static uint8_t color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

static uint16_t lcd_color332_to_565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

//
// Low-level PIO SPI functions
//

// Helper to set DC and CS pins together
static inline void lcd_set_dc_cs(bool dc, bool cs)
{
    gpio_put_masked((1u << LCD_DCX) | (1u << LCD_CSX), !!dc << LCD_DCX | !!cs << LCD_CSX);
}

void lcd_write_pixel_fb(int x, int y, uint8_t color_index)
{
    if (framebuffer != NULL && x >= 0 && x < DISPLAY_WIDTH && y >= 0 && y < DISPLAY_HEIGHT)
    {
        framebuffer[y * DISPLAY_WIDTH + x] = color_index;
    }
}

void lcd_write_buffer_fb_16(int x, int y, int width, int height, const uint16_t *buffer)
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
            lcd_write_pixel_fb(fb_x, fb_y, rgb332);
        }
    }
}

static void write_hline(int x, int y, int length, uint8_t color_index)
{
    if (y < 0 || y >= DISPLAY_HEIGHT || length <= 0 || framebuffer == NULL)
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

    memset(&framebuffer[y * DISPLAY_WIDTH + x], color_index, length);
}

static void swap_float(float *a, float *b)
{
    float t = *a;
    *a = *b;
    *b = t;
}

// Protect the SPI bus with a semaphore
void lcd_acquire()
{
    sem_acquire_blocking(&lcd_sem);
}

// Check if the LCD is available for access
bool lcd_available()
{
    // Check if the semaphore is available for LCD access
    return sem_available(&lcd_sem);
}

void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
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

    for (int row = 0; row < copy_height; row++)
    {
        int src_row_start = (src_y + row) * (int)width + src_x;
        uint8_t *dst_row = &framebuffer[(dst_y + row) * DISPLAY_WIDTH + dst_x];
        memcpy(dst_row, buffer + src_row_start, copy_width);
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

    lcd_write_buffer_fb_16(dst_x, dst_y, copy_width, copy_height, buffer);
}

void lcd_deinit(void)
{
    lcd_erase();
    lcd_display_off();
    module_initialized = false;
}

// Turn off the LCD display
void lcd_display_off()
{
    lcd_acquire();
    lcd_write_cmd(LCD_CMD_DISPOFF);
    lcd_release();
}

// Turn on the LCD display
void lcd_display_on()
{
    lcd_acquire();
    lcd_write_cmd(LCD_CMD_DISPON);
    lcd_release();
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
                framebuffer[py * DISPLAY_WIDTH + px] = color_index;
            }
        }
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
                framebuffer[py * DISPLAY_WIDTH + px] = color_index;
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
        write_hline(ix1, iy1, ix2 - ix1 + 1, color_index);
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
            framebuffer[iy1 * DISPLAY_WIDTH + ix1] = color_index;
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

// ---------------------------------------------------------------------------
// Drawing primitives
// ---------------------------------------------------------------------------

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= DISPLAY_WIDTH || y >= DISPLAY_HEIGHT)
        return;
    uint8_t color_index = color565_to_332(color);
    framebuffer[y * DISPLAY_WIDTH + x] = color_index;
}

void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    lcd_draw_line(x, y, x + width - 1, y, color);                           // top
    lcd_draw_line(x, y + height - 1, x + width - 1, y + height - 1, color); // bottom
    lcd_draw_line(x, y, x, y + height - 1, color);                          // left
    lcd_draw_line(x + width - 1, y, x + width - 1, y + height - 1, color);  // right
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
                        framebuffer[py * DISPLAY_WIDTH + px] = color_index;
                    }
                }
            }
        }

        current_x += char_spacing;
    }
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2,
                       uint16_t x3, uint16_t y3, uint16_t color)
{
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
}

void lcd_erase(void)
{
    for (uint16_t row = 0; row < DISPLAY_HEIGHT; row++)
    {
        for (uint16_t i = 0; i < DISPLAY_WIDTH; i++)
        {
            line_buffer_16[i] = 0x0000; // black color
        }
        lcd_blit_16bit(0, row, DISPLAY_WIDTH, 1, line_buffer_16);
    }
}

void lcd_fill(uint16_t color)
{
    uint8_t color_index = color565_to_332(color);
    memset(framebuffer, color_index, HEAP_BUFFER_SIZE);
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
        write_hline(cx - xv, cy + yv, 2 * xv + 1, color_index);
        write_hline(cx - xv, cy - yv, 2 * xv + 1, color_index);
        write_hline(cx - yv, cy + xv, 2 * yv + 1, color_index);
        write_hline(cx - yv, cy - xv, 2 * yv + 1, color_index);

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

void lcd_fill_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    if (count < 3)
        return;

    uint8_t color_index = color565_to_332(color);

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

                write_hline(ax, py, bx - ax + 1, color_index);
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

                write_hline(ax, py, bx - ax + 1, color_index);
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

                memcpy(line_buffer, &framebuffer[py * DISPLAY_WIDTH + ax], span);

                // Alpha blend the span in the line buffer
                for (int j = 0; j < span; j++)
                {
                    uint16_t dst_color = palette[line_buffer[j]];
                    uint8_t dr = (dst_color >> 11) & 0x1F;
                    uint8_t dg = (dst_color >> 5) & 0x3F;
                    uint8_t db = dst_color & 0x1F;

                    uint8_t br = (uint8_t)((sr * alpha + dr * inv_alpha) / 255);
                    uint8_t bg = (uint8_t)((sg * alpha + dg * inv_alpha) / 255);
                    uint8_t bb = (uint8_t)((sb * alpha + db * inv_alpha) / 255);

                    line_buffer[j] = color565_to_332(((uint16_t)br << 11) | ((uint16_t)bg << 5) | bb);
                }

                memcpy(&framebuffer[py * DISPLAY_WIDTH + ax], line_buffer, span);
            }
        }
    }
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
    for (int py = iy; py < iy + ih; py++)
        memset(&framebuffer[py * DISPLAY_WIDTH + ix], color_index, iw);
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
                framebuffer[py * DISPLAY_WIDTH + px] = color_index;
            }
        }
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

        write_hline(start_x, scanY, end_x - start_x + 1, color_index);
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

        uint8_t *row = &framebuffer[cur_y * DISPLAY_WIDTH + ax];
        for (int j = 0; j < seg_width; j++)
        {
            uint16_t dst_color = palette[row[j]];
            uint8_t dr = (dst_color >> 11) & 0x1F;
            uint8_t dg = (dst_color >> 5) & 0x3F;
            uint8_t db = dst_color & 0x1F;

            uint8_t br = (uint8_t)((sr * alpha + dr * inv_alpha) / 255);
            uint8_t bg = (uint8_t)((sg * alpha + dg * inv_alpha) / 255);
            uint8_t bb = (uint8_t)((sb * alpha + db * inv_alpha) / 255);

            uint16_t blended = ((uint16_t)br << 11) | ((uint16_t)bg << 5) | bb;
            row[j] = color565_to_332(blended);
        }
    }
}

// Initialize the LCD display
void lcd_init()
{
    if (module_initialized)
    {
        return; // already initialized
    }

    // initialise GPIO pins
    gpio_init(LCD_SCL);
    gpio_init(LCD_SDI);
    gpio_init(LCD_SDO);
    gpio_init(LCD_CSX);
    gpio_init(LCD_DCX);
    gpio_init(LCD_RST);

    gpio_set_dir(LCD_CSX, GPIO_OUT);
    gpio_set_dir(LCD_DCX, GPIO_OUT);
    gpio_set_dir(LCD_RST, GPIO_OUT);

    // Initialize PIO for fast SPI communication
    lcd_pio_offset = pio_add_program(LCD_PIO, &st7789_lcd_program);
    lcd_pio_sm = pio_claim_unused_sm(LCD_PIO, true);

    // Set clock (SCL) and data (SDI) to 8 mA fast slew.
    gpio_set_drive_strength(LCD_SCL, GPIO_DRIVE_STRENGTH_8MA);
    gpio_set_drive_strength(LCD_SDI, GPIO_DRIVE_STRENGTH_8MA);
    gpio_set_slew_rate(LCD_SCL, GPIO_SLEW_RATE_FAST);
    gpio_set_slew_rate(LCD_SDI, GPIO_SLEW_RATE_FAST);

    // PIO runs at 2 instructions per bit.
    float clkdiv = (float)clock_get_hz(clk_sys) / (float)(LCD_BAUDRATE * 2);
    if (clkdiv < 1.0f)
        clkdiv = 1.0f;

    st7789_lcd_program_init(LCD_PIO, lcd_pio_sm, lcd_pio_offset, LCD_SDI, LCD_SCL, clkdiv);

    // Set initial pin states
    lcd_set_dc_cs(0, 1); // CS high (inactive)
    gpio_put(LCD_RST, 1);

    lcd_reset(); // reset the LCD controller

    lcd_write_cmd(LCD_CMD_SWRESET);
    sleep_ms(120);

    lcd_write_cmd(LCD_CMD_COLMOD);
    lcd_write_data(1, 0x66); // 18-bit RGB666 over SPI

    lcd_write_cmd(LCD_CMD_MADCTL);
    lcd_write_data(1, 0xE8); // 90-degree counterclockwise

    lcd_write_cmd(LCD_CMD_INVON);

    lcd_write_cmd(LCD_CMD_SLPOUT);
    sleep_ms(120);

    // Prevent issues with other operations
    sem_init(&lcd_sem, 1, 1);

    // Clear the screen
    lcd_erase();

    // Now that the display is initialized, display RAM garbage is cleared,
    // turn on the display
    lcd_display_on();

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

void lcd_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    if (count < 2)
        return;

    uint8_t color_index = color565_to_332(color);
    int ix1 = (int)x[count - 1], iy1 = (int)y[count - 1];

    for (int i = 0; i < count; i++)
    {
        int ix2 = (int)x[i], iy2 = (int)y[i];

        // Fast path - horizontal edge
        if (iy1 == iy2)
        {
            int ax = (ix1 < ix2) ? ix1 : ix2;
            int bx = (ix1 < ix2) ? ix2 : ix1;
            write_hline(ax, iy1, bx - ax + 1, color_index);
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
                    framebuffer[iy1 * DISPLAY_WIDTH + ix1] = color_index;
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

bool lcd_read_row(uint16_t row, uint8_t *dst)
{
    if (row >= DISPLAY_HEIGHT || !dst)
        return false;
    memcpy(dst, &framebuffer[(uint32_t)row * DISPLAY_WIDTH], DISPLAY_WIDTH);
    return true;
}

// Release the SPI bus
void lcd_release()
{
    sem_release(&lcd_sem);
}

// Reset the LCD display
void lcd_reset()
{
    // Blip the reset pin to reset the LCD controller
    gpio_put(LCD_RST, 0);
    sleep_us(20); // 20µs reset pulse (10µs minimum)

    gpio_put(LCD_RST, 1);
    sleep_ms(120); // 5ms required after reset, but 120ms needed before sleep out command
}

void lcd_solid_rectangle(uint16_t colour, uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    for (uint16_t row = 0; row < height; row++)
    {
        for (uint16_t i = 0; i < width; i++)
        {
            line_buffer_16[i] = colour;
        }
        lcd_blit_16bit(x, y + row, width, 1, line_buffer_16);
    }
}

void lcd_swap(void)
{
    lcd_swap_region(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT);
}

void lcd_swap_region(uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    if (x >= DISPLAY_WIDTH || y >= DISPLAY_HEIGHT || width == 0 || height == 0)
        return;

    if ((uint32_t)x + width > DISPLAY_WIDTH)
        width = DISPLAY_WIDTH - x;
    if ((uint32_t)y + height > DISPLAY_HEIGHT)
        height = DISPLAY_HEIGHT - y;

    uint16_t x_end = x + width - 1;

    for (uint16_t row = 0; row < height; row += LCD_CHUNK_LINES)
    {
        uint16_t lines_to_send = (row + LCD_CHUNK_LINES > height) ? (height - row) : LCD_CHUNK_LINES;
        uint16_t y_start = y + row;
        uint16_t y_end = y_start + lines_to_send - 1;

        lcd_write_cmd(LCD_CMD_CASET);
        lcd_write_data(4, x >> 8, x & 0xFF, x_end >> 8, x_end & 0xFF);
        lcd_write_cmd(LCD_CMD_RASET);
        lcd_write_data(4, y_start >> 8, y_start & 0xFF, y_end >> 8, y_end & 0xFF);
        lcd_write_cmd(LCD_CMD_RAMWR);

        for (uint16_t line = 0; line < lines_to_send; line++)
        {
            uint8_t *heap_row = &framebuffer[(y_start + line) * DISPLAY_WIDTH + x];
            for (uint16_t col = 0; col < width; col++)
            {
                lcd_line_buffer[line * width + col] = palette[heap_row[col]];
            }
        }

        lcd_write16_buf(lcd_line_buffer, (size_t)lines_to_send * width);
    }
}

void lcd_write16_buf(const uint16_t *buffer, size_t len)
{
    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(1, 0); // DC=1 (data), CS=0 (active)

    for (size_t i = 0; i < len; i++)
    {
        uint16_t color = buffer[i];
        color = (uint16_t)~color;
        uint8_t red = (color >> 11) & 0x1F;
        uint8_t green = (color >> 5) & 0x3F;
        uint8_t blue = color & 0x1F;

        red = (red << 1) | (red >> 4);
        blue = (blue << 1) | (blue >> 4);
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, red << 2);
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, green << 2);
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, blue << 2);
    }

    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(0, 1); // CS=1 (inactive)
}

// Send a command
void lcd_write_cmd(uint8_t cmd)
{
    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(0, 0); // DC=0 (command), CS=0 (active)
    st7789_lcd_put(LCD_PIO, lcd_pio_sm, cmd);
    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(0, 1); // CS=1 (inactive)
}

// Send 8-bit data (byte)
void lcd_write_data(uint8_t len, ...)
{
    va_list args;
    va_start(args, len);

    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(1, 0); // DC=1 (data), CS=0 (active)

    for (uint8_t i = 0; i < len; i++)
    {
        uint8_t data = va_arg(args, int);
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, data);
    }

    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(0, 1); // CS=1 (inactive)
    va_end(args);
}
