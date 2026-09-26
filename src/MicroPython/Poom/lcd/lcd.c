/*
 * LCD Driver for the POOM (ESP32-C5, SSD1306 128x64 monochrome OLED, I2C).
 *
 * Draws into an 8-bit framebuffer (0x00 = off, 0xFF = on) so the shared
 * colour APIs keep working; colours are reduced to one bit on swap.
 */

#include "lcd.h"
#include "../board_config.h"

#include <stdlib.h>
#include <string.h>

#include "driver/i2c_master.h"

#define OLED_CONTROL_CMD 0x00
#define OLED_CONTROL_DATA 0x40
#define OLED_PAGE_COUNT (LCD_HEIGHT / 8)
#define OLED_COL_OFFSET 2 /* SH1106 132-col panel offset */

static i2c_master_bus_handle_t s_bus;
static i2c_master_dev_handle_t s_dev;
static bool s_initialized = false;

static const uint8_t LCD_TEXT_SPACING = 1;
static const uint8_t LCD_LINE_SPACING = 2;

#define FB_SIZE (LCD_WIDTH * LCD_HEIGHT)
static uint8_t s_fb[FB_SIZE];

/* Send one control byte followed by payload. */
static void oled_write(uint8_t control, const uint8_t *data, size_t len)
{
    if (!s_initialized || len == 0 || len > LCD_WIDTH)
        return;

    uint8_t buf[LCD_WIDTH + 1];
    buf[0] = control;
    memcpy(&buf[1], data, len);
    i2c_master_transmit(s_dev, buf, len + 1, 100);
}

bool lcd_init(void)
{
    memset(s_fb, 0x00, FB_SIZE);

    if (!s_initialized)
    {
        i2c_master_bus_config_t bus_cfg = {
            .i2c_port = POOM_OLED_I2C_PORT,
            .sda_io_num = POOM_OLED_I2C_SDA_GPIO,
            .scl_io_num = POOM_OLED_I2C_SCL_GPIO,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .flags.enable_internal_pullup = true,
        };
        if (i2c_new_master_bus(&bus_cfg, &s_bus) != ESP_OK)
        {
            s_bus = NULL;
            return false;
        }

        i2c_device_config_t dev_cfg = {
            .dev_addr_length = I2C_ADDR_BIT_LEN_7,
            .device_address = POOM_OLED_I2C_ADDR,
            .scl_speed_hz = POOM_OLED_I2C_FREQ_HZ,
        };
        if (i2c_master_bus_add_device(s_bus, &dev_cfg, &s_dev) != ESP_OK)
        {
            i2c_del_master_bus(s_bus);
            s_bus = NULL;
            return false;
        }
        s_initialized = true;
    }

    /* SH1106 init: 128x64, charge pump, page addressing. */
    static const uint8_t init_seq[] = {
        0xAE, /* display off */
        0xD5,
        0x80, /* clock divide */
        0xA8,
        0x3F, /* multiplex 64 */
        0xD3,
        0x00, /* display offset */
        0x40, /* start line 0 */
        0x8D,
        0x14, /* charge pump on */
        0x20,
        0x02, /* page addressing */
        0xA1, /* segment remap */
        0xC8, /* COM scan dec */
        0xDA,
        0x12, /* COM pins */
        0x81,
        0xCF, /* contrast */
        0xD9,
        0xF1, /* pre-charge */
        0xDB,
        0x40, /* VCOMH deselect */
        0xA4, /* resume RAM content */
        0xA6, /* normal display */
        0x2E, /* deactivate scroll */
        0xAF, /* display on */
    };
    oled_write(OLED_CONTROL_CMD, init_seq, sizeof(init_seq));

    lcd_fill(0x0000);
    lcd_swap();

    return true;
}

void lcd_deinit(void)
{
    if (!s_initialized)
        return;

    uint8_t cmd = 0xAE; /* display off */
    oled_write(OLED_CONTROL_CMD, &cmd, 1);

    i2c_master_bus_rm_device(s_dev);
    i2c_del_master_bus(s_bus);
    s_dev = NULL;
    s_bus = NULL;
    s_initialized = false;
}

bool lcd_set_backlight(uint32_t brightness)
{
    if (brightness > 100)
        brightness = 100;

    uint8_t seq[2] = {0x81, (uint8_t)((brightness * 255U) / 100U)};
    oled_write(OLED_CONTROL_CMD, seq, sizeof(seq));
    return true;
}

/* Bright colours light up (OLED); max luminance is 49784. */
static uint8_t color_to_mono(uint16_t color)
{
    uint8_t r5 = (color >> 11) & 0x1F;
    uint8_t g6 = (color >> 5) & 0x3F;
    uint8_t b5 = color & 0x1F;
    uint32_t lum = (uint32_t)r5 * 299 + (uint32_t)g6 * 587 + (uint32_t)b5 * 114;
    return (lum > 44800) ? 0xFF : 0x00;
}

void lcd_swap(void)
{
    if (!s_initialized)
        return;

    for (uint8_t page = 0; page < OLED_PAGE_COUNT; page++)
    {
        uint8_t cmds[3] = {
            (uint8_t)(0xB0 | page),                     /* page address */
            (uint8_t)(0x00 | (OLED_COL_OFFSET & 0x0F)), /* column low */
            (uint8_t)(0x10 | (OLED_COL_OFFSET >> 4)),   /* column high */
        };
        oled_write(OLED_CONTROL_CMD, cmds, sizeof(cmds));

        uint8_t buf[LCD_WIDTH];
        for (int x = 0; x < LCD_WIDTH; x++)
        {
            uint8_t byte = 0;
            for (int b = 0; b < 8; b++)
            {
                int y = page * 8 + b;
                if (y < LCD_HEIGHT && s_fb[y * LCD_WIDTH + x] != 0)
                {
                    byte |= (1 << b);
                }
            }
            buf[x] = byte;
        }
        oled_write(OLED_CONTROL_DATA, buf, LCD_WIDTH);
    }
}

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT)
        return;
    s_fb[y * LCD_WIDTH + x] = color_to_mono(color);
}

void lcd_fill(uint16_t color)
{
    uint8_t val = color_to_mono(color);
    memset(s_fb, val, FB_SIZE);
}

void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
{
    for (uint16_t row = 0; row < height && y + row < LCD_HEIGHT; row++)
    {
        for (uint16_t col = 0; col < width && x + col < LCD_WIDTH; col++)
        {
            s_fb[(y + row) * LCD_WIDTH + (x + col)] = buffer[row * width + col];
        }
    }
}

void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer)
{
    for (uint16_t row = 0; row < height && y + row < LCD_HEIGHT; row++)
    {
        for (uint16_t col = 0; col < width && x + col < LCD_WIDTH; col++)
        {
            s_fb[(y + row) * LCD_WIDTH + (x + col)] = color_to_mono(buffer[row * width + col]);
        }
    }
}

void lcd_read_row(uint16_t y, uint8_t *out_buffer)
{
    if (y >= LCD_HEIGHT)
        return;
    memcpy(out_buffer, &s_fb[y * LCD_WIDTH], LCD_WIDTH);
}

void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    int16_t dx = abs((int16_t)(x2 - x1));
    int16_t dy = -abs((int16_t)(y2 - y1));
    int16_t sx = x1 < x2 ? 1 : -1;
    int16_t sy = y1 < y2 ? 1 : -1;
    int16_t err = dx + dy;
    uint8_t val = color_to_mono(color);

    while (1)
    {
        if (x1 < LCD_WIDTH && y1 < LCD_HEIGHT)
        {
            s_fb[y1 * LCD_WIDTH + x1] = val;
        }
        if ((int16_t)x1 == (int16_t)x2 && (int16_t)y1 == (int16_t)y2)
            break;
        int16_t e2 = 2 * err;
        if (e2 >= dy)
        {
            err += dy;
            x1 += sx;
        }
        if (e2 <= dx)
        {
            err += dx;
            y1 += sy;
        }
    }
}

void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    lcd_draw_line(x, y, x + width, y, color);
    lcd_draw_line(x, y + height, x + width, y + height, color);
    lcd_draw_line(x, y, x, y + height, color);
    lcd_draw_line(x + width, y, x + width, y + height, color);
}

void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    uint8_t val = color_to_mono(color);
    for (uint16_t row = 0; row < height && y + row < LCD_HEIGHT; row++)
    {
        for (uint16_t col = 0; col < width && x + col < LCD_WIDTH; col++)
        {
            s_fb[(y + row) * LCD_WIDTH + (x + col)] = val;
        }
    }
}

void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color)
{
    (void)radius;
    lcd_fill_rect(x, y, width, height, color);
}

static void lcd_set_pixel_internal(int16_t x, int16_t y, uint8_t val)
{
    if (x >= 0 && x < LCD_WIDTH && y >= 0 && y < LCD_HEIGHT)
    {
        s_fb[y * LCD_WIDTH + x] = val;
    }
}

static void lcd_fill_hline(int16_t cx, int16_t cy, int16_t r, uint8_t val)
{
    if (cy >= 0 && cy < LCD_HEIGHT)
    {
        int16_t x0 = cx - r;
        int16_t x1 = cx + r;
        if (x0 < 0)
            x0 = 0;
        if (x1 > LCD_WIDTH)
            x1 = LCD_WIDTH;
        for (int16_t i = x0; i <= x1; i++)
        {
            s_fb[cy * LCD_WIDTH + i] = val;
        }
    }
}

void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int16_t x = 0;
    int16_t y = radius;
    int16_t d = 3 - 2 * (int16_t)radius;
    uint8_t val = color_to_mono(color);

    while (y >= x)
    {
        lcd_set_pixel_internal(center_x + x, center_y + y, val);
        lcd_set_pixel_internal(center_x - x, center_y + y, val);
        lcd_set_pixel_internal(center_x + x, center_y - y, val);
        lcd_set_pixel_internal(center_x - x, center_y - y, val);
        lcd_set_pixel_internal(center_x + y, center_y + x, val);
        lcd_set_pixel_internal(center_x - y, center_y + x, val);
        lcd_set_pixel_internal(center_x + y, center_y - x, val);
        lcd_set_pixel_internal(center_x - y, center_y - x, val);
        x++;
        if (d > 0)
        {
            y--;
            d = d + 4 * (x - y) + 10;
        }
        else
        {
            d = d + 4 * x + 6;
        }
    }
}

void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int16_t x = 0;
    int16_t y = radius;
    int16_t d = 3 - 2 * (int16_t)radius;
    uint8_t val = color_to_mono(color);

    while (y >= x)
    {
        lcd_fill_hline(center_x, center_y + y, x, val);
        lcd_fill_hline(center_x, center_y - y, x, val);
        lcd_fill_hline(center_x, center_y + x, y, val);
        lcd_fill_hline(center_x, center_y - x, y, val);
        x++;
        if (d > 0)
        {
            y--;
            d = d + 4 * (x - y) + 10;
        }
        else
        {
            d = d + 4 * x + 6;
        }
    }
}

static int16_t min_int16(int16_t a, int16_t b) { return a < b ? a : b; }
static int16_t max_int16(int16_t a, int16_t b) { return a > b ? a : b; }

static int32_t edge_func(int16_t ax, int16_t ay, int16_t bx, int16_t by, int16_t cx, int16_t cy)
{
    return (int32_t)(bx - ax) * (cy - ay) - (int32_t)(by - ay) * (cx - ax);
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color)
{
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
}

void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color)
{
    uint8_t val = color_to_mono(color);

    int16_t min_x = max_int16(0, min_int16(min_int16(x1, x2), x3));
    int16_t max_x = min_int16(LCD_WIDTH, max_int16(max_int16(x1, x2), x3));
    int16_t min_y = max_int16(0, min_int16(min_int16(y1, y2), y3));
    int16_t max_y = min_int16(LCD_HEIGHT, max_int16(max_int16(y1, y2), y3));

    for (int16_t py = min_y; py <= max_y; py++)
    {
        for (int16_t px = min_x; px <= max_x; px++)
        {
            int32_t w0 = edge_func(x2, y2, x3, y3, px, py);
            int32_t w1 = edge_func(x3, y3, x1, y1, px, py);
            int32_t w2 = edge_func(x1, y1, x2, y2, px, py);
            if ((w0 >= 0 && w1 >= 0 && w2 >= 0) || (w0 <= 0 && w1 <= 0 && w2 <= 0))
            {
                s_fb[py * LCD_WIDTH + px] = val;
            }
        }
    }
}

void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color, uint8_t alpha)
{
    (void)alpha;
    lcd_fill_triangle(x1, y1, x2, y2, x3, y3, color);
}

void lcd_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    for (int i = 0; i < count; i++)
    {
        int next = (i + 1) % count;
        lcd_draw_line(x[i], y[i], x[next], y[next], color);
    }
}

void lcd_fill_polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    if (count < 3)
        return;
    for (int i = 1; i + 1 < count; ++i)
        lcd_fill_triangle(x[0], y[0], x[i], y[i], x[i + 1], y[i + 1], color);
}

void lcd_fill_polygon_alpha(uint16_t x[], uint16_t y[], int count,
                            uint16_t color, uint8_t alpha)
{
    if (count < 3)
        return;
    for (int i = 1; i + 1 < count; ++i)
        lcd_fill_triangle_alpha(x[0], y[0], x[i], y[i], x[i + 1], y[i + 1], color, alpha);
}

void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size)
{
    int char_code = (int)(unsigned char)c;
    if (char_code < 32 || char_code > 126)
        return;

    uint8_t char_width = font_get_width(size);
    uint8_t char_height = font_get_height(size);
    uint8_t bytes_per_row = (char_width + 7) / 8;

    const uint8_t *char_data = font_get_character(size, c);
    if (!char_data)
        return;

    uint8_t val = color_to_mono(color);

    if ((int)x + char_width > LCD_WIDTH || (int)y + char_height > LCD_HEIGHT)
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
                uint16_t px = x + col;
                uint16_t py = y + row;
                if (px < LCD_WIDTH && py < LCD_HEIGHT)
                {
                    s_fb[py * LCD_WIDTH + px] = val;
                }
            }
        }
    }
}

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size)
{
    uint8_t char_width = font_get_width(size);
    uint8_t char_height = font_get_height(size);
    uint16_t cur_x = x;

    while (*text)
    {
        if (*text == '\n')
        {
            cur_x = x;
            y += char_height + LCD_LINE_SPACING;
            text++;
            continue;
        }
        lcd_draw_char(cur_x, y, *text, color, size);
        cur_x += char_width + LCD_TEXT_SPACING;
        text++;
    }
}
