#include "lcd.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_err.h"
#include "esp_check.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_log.h"
#include "esp_attr.h"          // ESP32 attribute macros (PSRAM)

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "esp_lcd_sh8601.h"

static const char *TAG = "display";

static const sh8601_lcd_init_cmd_t lcd_init_cmds[] = {
    {0x11, (uint8_t[]){0x00}, 0, 120},
    {0xC4, (uint8_t[]){0x80}, 1, 0},
    {0x44, (uint8_t[]){0x01, 0xD1}, 2, 0},
    {0x35, (uint8_t[]){0x00}, 1, 0},
    {0x53, (uint8_t[]){0x20}, 1, 10},
    {0x63, (uint8_t[]){0xFF}, 1, 10},
    {0x51, (uint8_t[]){0x00}, 1, 10},
    {0x2A, (uint8_t[]){0x00, 0x16, 0x01, 0xAF}, 4, 0},
    {0x2B, (uint8_t[]){0x00, 0x00, 0x01, 0xF5}, 4, 0},
    {0x29, (uint8_t[]){0x00}, 0, 10},
    {0x51, (uint8_t[]){0xFF}, 1, 0},
};

static esp_lcd_panel_io_handle_t s_panel_io;
static esp_lcd_panel_handle_t s_panel;
static bool s_spi_bus_owned;
static const FontTable *s_current_font = &Font16;
static uint8_t s_framebuffer[LCD_WIDTH * LCD_HEIGHT];
static uint16_t s_palette[256];

#define LCD_SWAP_LINES 2U
static const uint8_t LCD_TEXT_SPACING = 1;
static const uint8_t LCD_LINE_SPACING = 2;
static uint16_t s_swap_buffer[LCD_WIDTH * LCD_SWAP_LINES];

static esp_err_t display_init(void);
static esp_err_t lcd_swap_internal(void);
static void lcd_init_palette(void);
static esp_err_t lcd_wait_for_color_tx_done(void);

static uint8_t lcd_color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

static uint16_t lcd_color332_to_565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

static void lcd_init_palette(void)
{
    for (int i = 0; i < 256; i++)
    {
        uint8_t r3 = (i >> 5) & 0x07;
        uint8_t g3 = (i >> 2) & 0x07;
        uint8_t b2 = i & 0x03;

        uint8_t r8 = (r3 * 255) / 7;
        uint8_t g8 = (g3 * 255) / 7;
        uint8_t b8 = (b2 * 255) / 3;

        uint16_t pixel = lcd_color332_to_565(r8, g8, b8);
        s_palette[i] = (uint16_t)((pixel << 8) | (pixel >> 8));
    }
}

static esp_err_t lcd_wait_for_color_tx_done(void)
{
    return esp_lcd_panel_io_tx_param(s_panel_io, -1, NULL, 0);
}

static const FontTable *lcd_font_from_size(FontSize size)
{
    switch (size)
    {
    case FONT_SIZE_XTRA_SMALL:
        return &Font8;
    case FONT_SIZE_SMALL:
        return &Font12;
    case FONT_SIZE_LARGE:
        return &Font20;
    case FONT_SIZE_XTRA_LARGE:
        return &Font24;
    case FONT_SIZE_MEDIUM:
    default:
        return &Font16;
    }
}

static const FontTable *lcd_get_font(void)
{
    return s_current_font != NULL ? s_current_font : &Font16;
}

static uint16_t lcd_text_advance(void)
{
    return (uint16_t)(lcd_get_font()->width + LCD_TEXT_SPACING);
}

static uint16_t lcd_line_advance(void)
{
    return (uint16_t)(lcd_get_font()->height + LCD_LINE_SPACING);
}

static size_t lcd_framebuffer_index(uint16_t x, uint16_t y)
{
    return (size_t)y * LCD_WIDTH + x;
}

static void lcd_draw_hline_clipped(int32_t x, int32_t y, int32_t length, uint8_t color)
{
    if (y < 0 || y >= LCD_HEIGHT || length <= 0)
    {
        return;
    }

    if (x < 0)
    {
        length += x;
        x = 0;
    }

    if (x >= LCD_WIDTH || length <= 0)
    {
        return;
    }

    if (x + length > LCD_WIDTH)
    {
        length = LCD_WIDTH - x;
    }

    uint8_t *row = &s_framebuffer[lcd_framebuffer_index((uint16_t)x, (uint16_t)y)];
    for (int32_t pixel = 0; pixel < length; ++pixel)
    {
        row[pixel] = color;
    }
}

static int32_t lcd_edge_function(int32_t ax, int32_t ay, int32_t bx, int32_t by, int32_t px,
                                 int32_t py)
{
    return (px - ax) * (by - ay) - (py - ay) * (bx - ax);
}

static esp_err_t display_setup_panel(void)
{
    const spi_bus_config_t bus_cfg = SH8601_PANEL_BUS_QSPI_CONFIG(WATCH_LCD_SCLK_GPIO,
                                                                 WATCH_LCD_DATA0_GPIO,
                                                                 WATCH_LCD_DATA1_GPIO,
                                                                 WATCH_LCD_DATA2_GPIO,
                                                                 WATCH_LCD_DATA3_GPIO,
                                                                 LCD_WIDTH * LCD_HEIGHT * BITS_PER_PIXEL / 8);

    esp_err_t err = spi_bus_initialize(WATCH_LCD_HOST, &bus_cfg, SPI_DMA_CH_AUTO);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE)
    {
        return err;
    }
    s_spi_bus_owned = (err == ESP_OK);

    const esp_lcd_panel_io_spi_config_t io_cfg = SH8601_PANEL_IO_QSPI_CONFIG(WATCH_LCD_CS_GPIO, NULL, NULL);

    sh8601_vendor_config_t vendor_config = {
        .init_cmds = lcd_init_cmds,
        .init_cmds_size = sizeof(lcd_init_cmds) / sizeof(lcd_init_cmds[0]),
        .flags = {
            .use_qspi_interface = 1,
        },
    };

    ESP_RETURN_ON_ERROR(
        esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)WATCH_LCD_HOST, &io_cfg,
                                 &s_panel_io),
        TAG, "failed to create panel io");

    esp_lcd_panel_dev_config_t panel_cfg = {
        .reset_gpio_num = WATCH_LCD_RST_GPIO,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .bits_per_pixel = 16,
        .vendor_config = &vendor_config,
    };
    ESP_RETURN_ON_ERROR(esp_lcd_new_panel_sh8601(s_panel_io, &panel_cfg, &s_panel), TAG,
                        "failed to create sh8601 panel");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_reset(s_panel), TAG, "panel reset failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_init(s_panel), TAG, "panel init failed");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_set_gap(s_panel, 0x16, 0), TAG,
                        "failed to set pixel gap");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_disp_on_off(s_panel, true), TAG,
                        "failed to enable panel");
    return ESP_OK;
}

static esp_err_t lcd_swap_internal(void)
{
    if (s_panel == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    for (uint16_t y = 0; y < LCD_HEIGHT; y += LCD_SWAP_LINES)
    {
        uint16_t chunk_height = LCD_SWAP_LINES;
        if (y + chunk_height > LCD_HEIGHT)
        {
            chunk_height = LCD_HEIGHT - y;
        }

        for (uint16_t row = 0; row < chunk_height; ++row)
        {
            size_t src_offset = lcd_framebuffer_index(0, (uint16_t)(y + row));
            size_t dst_offset = (size_t)row * LCD_WIDTH;
            for (uint16_t x = 0; x < LCD_WIDTH; ++x)
            {
                s_swap_buffer[dst_offset + x] = s_palette[s_framebuffer[src_offset + x]];
            }
        }

        esp_err_t err = esp_lcd_panel_draw_bitmap(s_panel, 0, y, LCD_WIDTH, y + chunk_height,
                                                  s_swap_buffer);
        if (err != ESP_OK)
        {
            return err;
        }

        err = lcd_wait_for_color_tx_done();
        if (err != ESP_OK)
        {
            return err;
        }
    }

    return ESP_OK;
}

static esp_err_t display_init(void)
{
    if (s_panel != NULL)
    {
        return ESP_OK;
    }

    esp_err_t err = display_setup_panel();
    if (err != ESP_OK)
    {
        lcd_deinit();
        return err;
    }

    if (!lcd_set_backlight(100))
    {
        lcd_deinit();
        return ESP_FAIL;
    }

    lcd_set_font(FONT_DEFAULT);
    lcd_init_palette();
    lcd_fill(0x0000);

    err = lcd_swap_internal();
    if (err != ESP_OK)
    {
        lcd_deinit();
        return err;
    }
    return ESP_OK;
}

bool lcd_init(void)
{
    return display_init() == ESP_OK;
}

void lcd_deinit(void)
{
    if (s_panel != NULL)
    {
        esp_lcd_panel_disp_on_off(s_panel, false);
        esp_lcd_panel_del(s_panel);
        s_panel = NULL;
    }

    if (s_panel_io != NULL)
    {
        esp_lcd_panel_io_del(s_panel_io);
        s_panel_io = NULL;
    }

    if (s_spi_bus_owned)
    {
        spi_bus_free(WATCH_LCD_HOST);
        s_spi_bus_owned = false;
    }
}

bool lcd_set_backlight(uint32_t brightness)
{
    if (s_panel == NULL)
    {
        ESP_LOGE(TAG, "Panel handle is not initialized");
        return false;
    }

    if (brightness < 0 || brightness > 100)
    {
        ESP_LOGE(TAG, "Invalid brightness percentage. Should be between 0 and 100.");
        return false;
    }
    uint8_t brightness_byte = (uint8_t)(brightness * 255 / 100);
    uint32_t lcd_cmd = 0x51;
    lcd_cmd &= 0xff;
    lcd_cmd <<= 8;
    lcd_cmd |= 0x02 << 24;
    uint8_t param = brightness_byte;
    esp_lcd_panel_io_tx_param(s_panel_io, lcd_cmd, &param, 1);

    return true;
}

void lcd_swap(void)
{
    esp_err_t err = lcd_swap_internal();
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "lcd_swap failed: %s", esp_err_to_name(err));
    }
}

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT)
    {
        return;
    }

    s_framebuffer[lcd_framebuffer_index(x, y)] = lcd_color565_to_332(color);
}

void lcd_fill(uint16_t color)
{
    uint8_t c = lcd_color565_to_332(color);
    for (size_t pixel = 0; pixel < (size_t)LCD_WIDTH * LCD_HEIGHT; ++pixel)
    {
        s_framebuffer[pixel] = c;
    }
}

void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
{
    if (buffer == NULL || x >= LCD_WIDTH || y >= LCD_HEIGHT || width == 0 || height == 0)
    {
        return;
    }

    uint16_t copy_width = width;
    uint16_t copy_height = height;
    if (x + copy_width > LCD_WIDTH)
    {
        copy_width = LCD_WIDTH - x;
    }
    if (y + copy_height > LCD_HEIGHT)
    {
        copy_height = LCD_HEIGHT - y;
    }

    for (uint16_t row = 0; row < copy_height; ++row)
    {
        memcpy(&s_framebuffer[lcd_framebuffer_index(x, y + row)], &buffer[(size_t)row * width],
               copy_width * sizeof(uint8_t));
    }
}

void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                    const uint16_t *buffer)
{
    if (buffer == NULL || x >= LCD_WIDTH || y >= LCD_HEIGHT || width == 0 || height == 0)
    {
        return;
    }

    uint16_t copy_width = width;
    uint16_t copy_height = height;
    if (x + copy_width > LCD_WIDTH)
    {
        copy_width = LCD_WIDTH - x;
    }
    if (y + copy_height > LCD_HEIGHT)
    {
        copy_height = LCD_HEIGHT - y;
    }

    for (uint16_t row = 0; row < copy_height; ++row)
    {
        const uint16_t *src_row = &buffer[(size_t)row * width];
        uint8_t *dst_row = &s_framebuffer[lcd_framebuffer_index(x, y + row)];

        for (uint16_t col = 0; col < copy_width; ++col)
        {
            dst_row[col] = lcd_color565_to_332(src_row[col]);
        }
    }
}

void lcd_read_row(uint16_t y, uint8_t *out_buffer)
{
    if (out_buffer == NULL || y >= LCD_HEIGHT)
    {
        return;
    }

    memcpy(out_buffer, &s_framebuffer[lcd_framebuffer_index(0, y)], LCD_WIDTH);
}

void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    int32_t current_x = x1;
    int32_t current_y = y1;
    const int32_t target_x = x2;
    const int32_t target_y = y2;
    const int32_t delta_x = abs(target_x - current_x);
    const int32_t step_x = current_x < target_x ? 1 : -1;
    const int32_t delta_y = -abs(target_y - current_y);
    const int32_t step_y = current_y < target_y ? 1 : -1;
    int32_t error = delta_x + delta_y;

    while (true)
    {
        if (current_x >= 0 && current_x < LCD_WIDTH && current_y >= 0 && current_y < LCD_HEIGHT)
        {
            lcd_draw_pixel((uint16_t)current_x, (uint16_t)current_y, color);
        }

        if (current_x == target_x && current_y == target_y)
        {
            break;
        }

        int32_t twice_error = error * 2;
        if (twice_error >= delta_y)
        {
            error += delta_y;
            current_x += step_x;
        }
        if (twice_error <= delta_x)
        {
            error += delta_x;
            current_y += step_y;
        }
    }
}

void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    if (width == 0 || height == 0)
    {
        return;
    }

    uint8_t c = lcd_color565_to_332(color);
    lcd_draw_hline_clipped(x, y, width, c);
    lcd_draw_hline_clipped(x, (int32_t)y + height - 1, width, c);
    lcd_draw_line(x, y, x, y + height - 1, color);
    lcd_draw_line(x + width - 1, y, x + width - 1, y + height - 1, color);
}

void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT || width == 0 || height == 0)
    {
        return;
    }

    uint16_t fill_width = width;
    uint16_t fill_height = height;
    if (x + fill_width > LCD_WIDTH)
    {
        fill_width = LCD_WIDTH - x;
    }
    if (y + fill_height > LCD_HEIGHT)
    {
        fill_height = LCD_HEIGHT - y;
    }

    uint8_t c = lcd_color565_to_332(color);
    for (uint16_t row = 0; row < fill_height; ++row)
    {
        lcd_draw_hline_clipped(x, y + row, fill_width, c);
    }
}

void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int32_t x = radius;
    int32_t y = 0;
    int32_t decision = 1 - x;

    while (x >= y)
    {
        lcd_draw_pixel(center_x + x, center_y + y, color);
        lcd_draw_pixel(center_x + y, center_y + x, color);
        lcd_draw_pixel(center_x - y, center_y + x, color);
        lcd_draw_pixel(center_x - x, center_y + y, color);
        lcd_draw_pixel(center_x - x, center_y - y, color);
        lcd_draw_pixel(center_x - y, center_y - x, color);
        lcd_draw_pixel(center_x + y, center_y - x, color);
        lcd_draw_pixel(center_x + x, center_y - y, color);

        ++y;
        if (decision <= 0)
        {
            decision += 2 * y + 1;
        }
        else
        {
            --x;
            decision += 2 * (y - x) + 1;
        }
    }
}

void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int32_t x = radius;
    int32_t y = 0;
    int32_t decision = 1 - x;

    uint8_t c = lcd_color565_to_332(color);
    while (x >= y)
    {
        lcd_draw_hline_clipped((int32_t)center_x - x, center_y + y, 2 * x + 1, c);
        lcd_draw_hline_clipped((int32_t)center_x - x, center_y - y, 2 * x + 1, c);
        lcd_draw_hline_clipped((int32_t)center_x - y, center_y + x, 2 * y + 1, c);
        lcd_draw_hline_clipped((int32_t)center_x - y, center_y - x, 2 * y + 1, c);

        ++y;
        if (decision <= 0)
        {
            decision += 2 * y + 1;
        }
        else
        {
            --x;
            decision += 2 * (y - x) + 1;
        }
    }
}

void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3,
                       uint16_t y3, uint16_t color)
{
    int32_t min_x = x1;
    int32_t max_x = x1;
    int32_t min_y = y1;
    int32_t max_y = y1;

    if (x2 < min_x)
        min_x = x2;
    if (x3 < min_x)
        min_x = x3;
    if (x2 > max_x)
        max_x = x2;
    if (x3 > max_x)
        max_x = x3;
    if (y2 < min_y)
        min_y = y2;
    if (y3 < min_y)
        min_y = y3;
    if (y2 > max_y)
        max_y = y2;
    if (y3 > max_y)
        max_y = y3;

    if (max_x < 0 || max_y < 0 || min_x >= LCD_WIDTH || min_y >= LCD_HEIGHT)
    {
        return;
    }

    if (min_x < 0)
        min_x = 0;
    if (min_y < 0)
        min_y = 0;
    if (max_x >= LCD_WIDTH)
        max_x = LCD_WIDTH - 1;
    if (max_y >= LCD_HEIGHT)
        max_y = LCD_HEIGHT - 1;

    int32_t area = lcd_edge_function(x1, y1, x2, y2, x3, y3);
    if (area == 0)
    {
        lcd_draw_line(x1, y1, x2, y2, color);
        lcd_draw_line(x2, y2, x3, y3, color);
        lcd_draw_line(x3, y3, x1, y1, color);
        return;
    }

    uint8_t c = lcd_color565_to_332(color);
    for (int32_t py = min_y; py <= max_y; ++py)
    {
        for (int32_t px = min_x; px <= max_x; ++px)
        {
            int32_t w0 = lcd_edge_function(x2, y2, x3, y3, px, py);
            int32_t w1 = lcd_edge_function(x3, y3, x1, y1, px, py);
            int32_t w2 = lcd_edge_function(x1, y1, x2, y2, px, py);

            if ((area > 0 && w0 >= 0 && w1 >= 0 && w2 >= 0) ||
                (area < 0 && w0 <= 0 && w1 <= 0 && w2 <= 0))
            {
                s_framebuffer[lcd_framebuffer_index((uint16_t)px, (uint16_t)py)] = c;
            }
        }
    }
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3,
                       uint16_t y3, uint16_t color)
{
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
}

void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                              uint16_t radius, uint16_t color)
{
    (void)radius;
    lcd_fill_rect(x, y, width, height, color);
}

void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size)
{
    lcd_set_font(size);
    const FontTable *font = lcd_get_font();
    uint8_t character = (uint8_t)c;
    if (character < 32 || character > 126)
    {
        character = '?';
    }

    uint8_t bytes_per_row = (uint8_t)((font->width + 7U) / 8U);
    size_t glyph_stride = (size_t)font->height * bytes_per_row;
    const uint8_t *glyph = &font->table[(size_t)(character - 32U) * glyph_stride];

    uint8_t c332 = lcd_color565_to_332(color);
    for (uint8_t row = 0; row < font->height; ++row)
    {
        for (uint8_t col = 0; col < font->width; ++col)
        {
            uint8_t glyph_byte = glyph[(size_t)row * bytes_per_row + (col / 8U)];
            if ((glyph_byte & (uint8_t)(0x80U >> (col % 8U))) != 0)
            {
                s_framebuffer[lcd_framebuffer_index(x + col, y + row)] = c332;
            }
        }
    }
}

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size)
{
    if (text == NULL)
    {
        return;
    }

    lcd_set_font(size);

    uint16_t cursor_x = x;
    uint16_t cursor_y = y;
    uint16_t start_x = x;

    for (const char *cursor = text; *cursor != '\0'; ++cursor)
    {
        if (*cursor == '\r')
        {
            continue;
        }

        if (*cursor == '\n')
        {
            cursor_x = start_x;
            cursor_y = (uint16_t)(cursor_y + lcd_line_advance());
            if (cursor_y >= LCD_HEIGHT)
            {
                break;
            }
            continue;
        }

        if ((uint32_t)cursor_x + lcd_get_font()->width > LCD_WIDTH)
        {
            cursor_x = start_x;
            cursor_y = (uint16_t)(cursor_y + lcd_line_advance());
        }

        if ((uint32_t)cursor_y + lcd_get_font()->height > LCD_HEIGHT)
        {
            break;
        }

        lcd_draw_char(cursor_x, cursor_y, *cursor, color, size);
        cursor_x = (uint16_t)(cursor_x + lcd_text_advance());
    }
}

uint8_t lcd_get_font_height(void)
{
    return lcd_get_font()->height;
}

uint8_t lcd_get_font_width(void)
{
    return lcd_get_font()->width;
}

void lcd_set_font(FontSize size)
{
    s_current_font = lcd_font_from_size(size);
}
