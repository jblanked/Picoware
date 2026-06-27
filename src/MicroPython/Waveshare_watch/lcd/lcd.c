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

static esp_lcd_panel_handle_t s_panel;   /* Type of LCD panel handle */
static esp_lcd_panel_io_handle_t s_panel_io;

static bool s_spi_bus_owned;

static FontTable *s_current_font = NULL; // Pointer to current font table structure

static uint8_t backlight_level; // Variable to store current backlight brightness level (0-100)

/* Static frame buffer in PSRAM - LCD_WIDTH * LCD_HEIGHT * 2 bytes (16bpp RGB565) */
static EXT_RAM_BSS_ATTR uint16_t frame_buffer[LCD_WIDTH * LCD_HEIGHT]; // Frame buffer in external PSRAM

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

static esp_err_t display_init(void);
static esp_err_t display_setup_panel(void);

static uint16_t lcd_color332_to_565(uint8_t color)
{
    return ((color & 0xF8) << 8) | ((color & 0xFC) << 3) | (color >> 3);
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
    lcd_fill(0xafaf);
    lcd_swap();

    return ESP_OK;
}

bool lcd_init(void)
{
    return display_init() == ESP_OK;
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

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color) // Write a pixel into the frame buffer at (x, y)
{
    if (s_panel == NULL) // Check if LCD is initialized
    {
        printf("lcd: LCD not initialized\n");
        return;
    }

    if (x >= LCD_WIDTH || y >= LCD_HEIGHT) // Bounds check
    {
        printf("lcd: Pixel coordinates out of bounds\n");
        return;
    }

    frame_buffer[y * LCD_WIDTH + x] = color; // Write pixel color into frame buffer
}

void lcd_swap(void) // Transfer the entire frame buffer to the LCD
{
    if (s_panel == NULL || s_panel == NULL) // Check if LCD is initialized
    {
        printf("lcd: LCD not initialized\n");
        return;
    }

    // Push the full frame buffer to the panel over DMA
    static esp_err_t err;
    err = esp_lcd_panel_draw_bitmap(s_panel, 0, 0, LCD_WIDTH, LCD_HEIGHT, frame_buffer);
    if (err != ESP_OK)
    {
        printf("lcd: Failed to draw bitmap to panel, %s\n", esp_err_to_name(err));
    }
}

/******************************************************************************
function: Draw a line between two points using Bresenham's algorithm
parameter:
    x1    : Starting X coordinate
    y1    : Starting Y coordinate
    x2    : Ending X coordinate
    y2    : Ending Y coordinate
    color : RGB565 color value
returns: none
******************************************************************************/
void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    int dx = abs((int)x2 - (int)x1);
    int dy = abs((int)y2 - (int)y1);
    int sx = (x1 < x2) ? 1 : -1;
    int sy = (y1 < y2) ? 1 : -1;
    int err = dx - dy;
    while (true)
    {
        // Draw pixel if within bounds
        if (x1 < LCD_WIDTH && y1 < LCD_HEIGHT)
        {
            frame_buffer[y1 * LCD_WIDTH + x1] = color;
        }

        // Check if we've reached the end point
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

/******************************************************************************
function: Draw a rectangle outline to the frame_buffer
parameter:
    x      : Top-left X coordinate
    y      : Top-left Y coordinate
    width  : Width of rectangle
    height : Height of rectangle
    color  : RGB565 color value
returns: none
******************************************************************************/
void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    // Draw four lines to form rectangle
    lcd_draw_line(x, y, x + width - 1, y, color);                           // Top
    lcd_draw_line(x, y + height - 1, x + width - 1, y + height - 1, color); // Bottom
    lcd_draw_line(x, y, x, y + height - 1, color);                          // Left
    lcd_draw_line(x + width - 1, y, x + width - 1, y + height - 1, color);  // Right
}

/******************************************************************************
function: Draw a filled rectangle to the frame_buffer
parameter:
    x      : Top-left X coordinate
    y      : Top-left Y coordinate
    width  : Width of rectangle
    height : Height of rectangle
    color  : RGB565 color value
returns: none
******************************************************************************/
void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    // Bounds clipping
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT)
        return;

    if (x + width > LCD_WIDTH)
        width = LCD_WIDTH - x;
    if (y + height > LCD_HEIGHT)
        height = LCD_HEIGHT - y;

    // Fast fill using optimized loops
    for (uint16_t py = y; py < y + height; py++)
    {
        for (uint16_t px = x; px < x + width; px++)
        {
            frame_buffer[py * LCD_WIDTH + px] = color;
        }
    }
}

void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color)
{
    // Bounds clipping
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT)
        return;

    if (x + width > LCD_WIDTH)
        width = LCD_WIDTH - x;
    if (y + height > LCD_HEIGHT)
        height = LCD_HEIGHT - y;

    // Fast fill using optimized loops
    for (uint16_t py = y; py < y + height; py++)
    {
        for (uint16_t px = x; px < x + width; px++)
        {
            frame_buffer[py * LCD_WIDTH + px] = color;
        }
    }
}

/******************************************************************************
function: Draw a single character to the frame_buffer
parameter:
    x     : Top-left X coordinate
    y     : Top-left Y coordinate
    c     : Character to draw
    color : RGB565 color value
returns: none
******************************************************************************/
void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size)
{
    lcd_set_font(size);
    if (s_current_font == NULL || c < 32 || c > 126)
        return; // invalid font or character

    // Calculate bytes per row (width rounded up to nearest byte boundary)
    uint8_t bytes_per_row = (s_current_font->width + 7) / 8;
    const uint8_t *char_data = &s_current_font->table[(c - 32) * s_current_font->height * bytes_per_row];

    for (uint8_t row = 0; row < s_current_font->height; row++)
    {
        const uint8_t *row_data = &char_data[row * bytes_per_row];

        for (uint8_t col = 0; col < s_current_font->width; col++)
        {
            uint8_t byte_index = col / 8;
            uint8_t bit_index = 7 - (col % 8);

            if (row_data[byte_index] & (1 << bit_index))
            {
                lcd_draw_pixel(x + col, y + row, color);
            }
        }
    }
}

/******************************************************************************
function: Draw a circle outline to the frame_buffer
parameter:
    center_x : Center X coordinate
    center_y : Center Y coordinate
    radius   : Radius in pixels
    color    : RGB565 color value
returns: none
******************************************************************************/
void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    if (radius == 0 || radius > 100)
        return;

    int x = 0;
    int y = radius;
    int d = 3 - 2 * radius;
    while (x <= y)
    {
        // Draw 8 symmetric points
        if (center_x + x < LCD_WIDTH && center_y + y < LCD_HEIGHT)
            frame_buffer[(center_y + y) * LCD_WIDTH + (center_x + x)] = color;
        if (center_x - x < LCD_WIDTH && center_y + y < LCD_HEIGHT)
            frame_buffer[(center_y + y) * LCD_WIDTH + (center_x - x)] = color;
        if (center_x + x < LCD_WIDTH && center_y - y < LCD_HEIGHT)
            frame_buffer[(center_y - y) * LCD_WIDTH + (center_x + x)] = color;
        if (center_x - x < LCD_WIDTH && center_y - y < LCD_HEIGHT)
            frame_buffer[(center_y - y) * LCD_WIDTH + (center_x - x)] = color;
        if (center_x + y < LCD_WIDTH && center_y + x < LCD_HEIGHT)
            frame_buffer[(center_y + x) * LCD_WIDTH + (center_x + y)] = color;
        if (center_x - y < LCD_WIDTH && center_y + x < LCD_HEIGHT)
            frame_buffer[(center_y + x) * LCD_WIDTH + (center_x - y)] = color;
        if (center_x + y < LCD_WIDTH && center_y - x < LCD_HEIGHT)
            frame_buffer[(center_y - x) * LCD_WIDTH + (center_x + y)] = color;
        if (center_x - y < LCD_WIDTH && center_y - x < LCD_HEIGHT)
            frame_buffer[(center_y - x) * LCD_WIDTH + (center_x - y)] = color;

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

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size)
{
    lcd_set_font(size);
    if (s_current_font == NULL)
        return; // invalid font

    uint16_t cursor_x = x;
    uint16_t cursor_y = y;

    while (*text)
    {
        char ch = *text;

        if (ch == '\n')
        {
            cursor_x = x;                     // Reset to start of line
            cursor_y += s_current_font->height; // Move down one line
        }
        else if (ch == ' ')
        {
            // Handle space - just advance position without drawing
            cursor_x += s_current_font->width;
        }
        else
        {
            // Check if character would exceed screen width
            if (cursor_x + s_current_font->width > LCD_WIDTH)
            {
                // Wrap to next line
                cursor_x = x;
                cursor_y += s_current_font->height;
            }

            // Check if we're still within screen height
            if (cursor_y + s_current_font->height <= LCD_HEIGHT)
            {
                lcd_draw_char(cursor_x, cursor_y, ch, color, size);
            }

            cursor_x += s_current_font->width;
        }
        text++;
    }
}

/******************************************************************************
function: Draw a filled circle to the frame_buffer
parameter:
    center_x : Center X coordinate
    center_y : Center Y coordinate
    radius   : Radius in pixels
    color    : RGB565 color value
returns: none
******************************************************************************/
void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    if (radius == 0 || radius > 100)
        return;

    int radius_squared = radius * radius;

    // Calculate bounding box
    int start_x = (center_x > radius) ? (center_x - radius) : 0;
    int end_x = (center_x + radius < LCD_WIDTH) ? (center_x + radius) : (LCD_WIDTH - 1);
    int start_y = (center_y > radius) ? (center_y - radius) : 0;
    int end_y = (center_y + radius < LCD_HEIGHT) ? (center_y + radius) : (LCD_HEIGHT - 1);

    // Fill using distance check
    for (int y = start_y; y <= end_y; y++)
    {
        int dy = y - center_y;
        int dy_squared = dy * dy;

        for (int x = start_x; x <= end_x; x++)
        {
            int dx = x - center_x;
            int distance_squared = dx * dx + dy_squared;

            if (distance_squared <= radius_squared)
            {
                frame_buffer[y * LCD_WIDTH + x] = color;
            }
        }
    }
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color){
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x1, y1, x3, y3, color);
}

/******************************************************************************
function: Draw a filled triangle to the frame_buffer
parameter:
    x1, y1 : First vertex coordinates
    x2, y2 : Second vertex coordinates
    x3, y3 : Third vertex coordinates
    color  : RGB565 color value
returns: none
******************************************************************************/
void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color)
{
    // Sort vertices by Y coordinate (y1 <= y2 <= y3)
    if (y1 > y2)
    {
        uint16_t temp = x1;
        x1 = x2;
        x2 = temp;
        temp = y1;
        y1 = y2;
        y2 = temp;
    }
    if (y2 > y3)
    {
        uint16_t temp = x2;
        x2 = x3;
        x3 = temp;
        temp = y2;
        y2 = y3;
        y3 = temp;
    }
    if (y1 > y2)
    {
        uint16_t temp = x1;
        x1 = x2;
        x2 = temp;
        temp = y1;
        y1 = y2;
        y2 = temp;
    }

    // Handle degenerate case
    if (y1 == y3)
        return;

    // Fill the triangle using horizontal scanlines
    for (uint16_t y = y1; y <= y3; y++)
    {
        if (y >= LCD_HEIGHT)
            break;

        int x_left, x_right;
        bool has_intersection = false;

        // Find left edge intersection
        if (y3 != y1)
        {
            x_left = x1 + (int)((x3 - x1) * (int)(y - y1)) / (int)(y3 - y1);
            has_intersection = true;
        }

        // Find right edge intersection
        if (y <= y2 && y2 != y1)
        {
            x_right = x1 + (int)((x2 - x1) * (int)(y - y1)) / (int)(y2 - y1);
        }
        else if (y > y2 && y3 != y2)
        {
            x_right = x2 + (int)((x3 - x2) * (int)(y - y2)) / (int)(y3 - y2);
        }
        else
        {
            x_right = x_left;
        }

        if (!has_intersection)
            continue;

        // Ensure x_left <= x_right
        if (x_left > x_right)
        {
            int temp = x_left;
            x_left = x_right;
            x_right = temp;
        }

        // Clamp to screen bounds
        if (x_left < 0)
            x_left = 0;
        if (x_right >= LCD_WIDTH)
            x_right = LCD_WIDTH - 1;

        // Draw horizontal line
        for (int x = x_left; x <= x_right; x++)
        {
            frame_buffer[y * LCD_WIDTH + x] = color;
        }
    }
}

/******************************************************************************
function: Fill the entire frame_buffer with a solid color
parameter:
    color : RGB565 color value to fill with
returns: none
******************************************************************************/
void lcd_fill(uint16_t color)
{
    for (uint32_t i = 0; i < LCD_HEIGHT * LCD_WIDTH; i++)
    {
        frame_buffer[i] = color;
    }
}

/******************************************************************************
function: Copy an external image buffer into the frame_buffer at specified position
parameter:
    x      : Top-left X coordinate
    y      : Top-left Y coordinate
    width  : Width of the buffer to blit
    height : Height of the buffer to blit
    buffer : Pointer to RGB565 pixel data array (16-bit per pixel)
returns: none
******************************************************************************/
void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
{
    for (uint16_t j = 0; j < height; j++)
    {
        for (uint16_t i = 0; i < width; i++)
        {
            if ((x + i) < LCD_WIDTH && (y + j) < LCD_HEIGHT)
            {
                frame_buffer[(y + j) * LCD_WIDTH + (x + i)] = lcd_color332_to_565(buffer[j * width + i]);
            }
        }
    }
}

void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer)
{
    for (uint16_t j = 0; j < height; j++)
    {
        for (uint16_t i = 0; i < width; i++)
        {
            if ((x + i) < LCD_WIDTH && (y + j) < LCD_HEIGHT)
            {
                frame_buffer[(y + j) * LCD_WIDTH + (x + i)] = buffer[j * width + i];
            }
        }
    }
}

/********************************************************************************
function: Get the current backlight brightness level
parameter: none
returns: Brightness level from 0 (off) to 100 (full)
********************************************************************************/
uint8_t lcd_get_backlight_level(void)
{
    return backlight_level;
}

/********************************************************************************
function: Get the current font height
parameter: none
returns: Font height in pixels
********************************************************************************/
uint8_t lcd_get_font_height(void)
{
    if (s_current_font != NULL)
    {
        return s_current_font->height;
    }
    return 0;
}

/********************************************************************************
function: Get the current font width
parameter: none
returns: Font width in pixels
********************************************************************************/
uint8_t lcd_get_font_width(void)
{
    if (s_current_font != NULL)
    {
        return s_current_font->width;
    }
    return 0;
}

/********************************************************************************
function: Set the current font size for text rendering
parameter:
    size : FontSize enum value specifying desired font size
returns: none
********************************************************************************/
void lcd_set_font(FontSize size)
{
    s_current_font = lcd_font_from_size(size);
}
