#include "lcd.h"
#include "qspi_pio.h"
#include "hardware/dma.h"
#include "hardware/pio.h"
#include "hardware/sync.h"

static bool lcd_initialized = false; // flag to indicate if the LCD is initialized

// Static framebuffer (16-bit per pixel for RGB565)
static uint8_t framebuffer[LCD_WIDTH * LCD_HEIGHT];
static uint16_t palette[256]; // 256-color palette for RGB332
static uint8_t backlight_level;
static uint8_t last_cmd = 0x00; // Track last command for data writes
static bool set_brightness_flag = false;

static FontTable *current_font = NULL;

// DMA channel and configuration for QSPI transfers
static int dma_tx;
static dma_channel_config c;

/******************************************************************************
 * function: Convert a 16-bit RGB565 color to an 8-bit RGB332 color
 * parameter:
 *    color : 16-bit RGB565 color value
 * returns: 8-bit RGB332 color value
 ******************************************************************************/
static uint8_t lcd_color565_to_332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}
/******************************************************************************
 * function: Convert 8-bit RGB332 components to a 16-bit RGB565 color
 * parameter:
 *    r : Red component (0-255)
 *    g : Green component (0-255)
 *    b : Blue component (0-255)
 * returns: 16-bit RGB565 color value
 ******************************************************************************/
static uint16_t lcd_color332_to_565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

typedef struct
{
    int cmd;               /*<! The specific LCD command */
    const uint8_t *data;   /*<! Buffer that holds the command specific data */
    size_t data_bytes;     /*<! Size of `data` in memory, in bytes */
    unsigned int delay_ms; /*<! Delay in milliseconds after this command */
} sh8601_lcd_init_cmd_t;

static void tx_param(sh8601_lcd_init_cmd_t *cmds, size_t cmd_len)
{
    for (int i = 0; i < cmd_len; i++)
    {
        QSPI_Select(qspi);
        QSPI_REGISTER_Write(qspi, cmds[i].cmd);

        for (int j = 0; j < cmds[i].data_bytes; j++)
        {
            QSPI_DATA_Write(qspi, cmds[i].data[j]);
        }
        QSPI_Deselect(qspi);

        if (cmds[i].delay_ms > 0)
        {
            sleep_ms(cmds[i].delay_ms);
        }
    }
}

static void set_window()
{
    sh8601_lcd_init_cmd_t cmds[2];

    uint16_t x_start = LCD_X_OFFSET;
    uint16_t x_end = LCD_WIDTH + LCD_X_OFFSET;

    uint16_t y_start = 0;
    uint16_t y_end = LCD_HEIGHT;
    uint8_t x_data[4];
    uint8_t y_data[4];
    x_data[0] = (x_start >> 8) & 0xFF;
    x_data[1] = x_start & 0xFF;
    x_data[2] = (x_end >> 8) & 0xFF;
    x_data[3] = x_end & 0xFF;

    y_data[0] = (y_start >> 8) & 0xFF;
    y_data[1] = y_start & 0xFF;
    y_data[2] = (y_end >> 8) & 0xFF;
    y_data[3] = y_end & 0xFF;

    cmds[0].cmd = 0x2a;
    cmds[0].data = x_data;
    cmds[0].data_bytes = 4;
    cmds[0].delay_ms = 0;

    cmds[1].cmd = 0x2b;
    cmds[1].data = y_data;
    cmds[1].data_bytes = 4;
    cmds[1].delay_ms = 0;

    tx_param(cmds, 2);
}

/******************************************************************************
function: Send command and data to OLED using the CO5300 protocol with PIO QSPI
parameter:
    cmd  : Command byte
    data : Data bytes (can be NULL if data_len is 0)
    data_len : Number of data bytes
returns: none
note: Low-level function used internally for OLED communication
      CO5300 protocol: Header(0x02, 0x00, cmd, 0x00) + data bytes
******************************************************************************/
static void lcd_send_cmd_data(uint8_t cmd, const uint8_t *data, size_t data_len)
{
    QSPI_Select(qspi);
    QSPI_REGISTER_Write(qspi, cmd);

    for (size_t i = 0; i < data_len; i++)
    {
        QSPI_DATA_Write(qspi, data[i]);
    }
    QSPI_Deselect(qspi);
}

/********************************************************************************
function: Hardware reset sequence
parameter: qspi - PIO QSPI configuration structure
returns: none
note: Toggles the reset pin and performs timing delays
********************************************************************************/
static void lcd_reset(pio_qspi_t qspi)
{
    gpio_put(qspi.pin_rst, 1);
    sleep_ms(200);
    gpio_put(qspi.pin_rst, 0);
    sleep_ms(200);
    gpio_put(qspi.pin_rst, 1);
    sleep_ms(200);
}

/******************************************************************************
function: Draw a single pixel to the framebuffer
parameter:
    X     : X coordinate (0 to LCD_WIDTH-1)
    Y     : Y coordinate (0 to LCD_HEIGHT-1)
    color : RGB565 color value
returns: none
******************************************************************************/
void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT)
    {
        return; // bounds check
    }
    // Convert to 8-bit and store
    framebuffer[y * LCD_WIDTH + x] = lcd_color565_to_332(color);
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
    const uint8_t color_index = lcd_color565_to_332(color);
    while (true)
    {
        // Draw pixel if within bounds
        if (x1 < LCD_WIDTH && y1 < LCD_HEIGHT)
        {
            framebuffer[y1 * LCD_WIDTH + x1] = color_index;
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
function: Draw a rectangle outline to the framebuffer
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
    const uint8_t color_index = lcd_color565_to_332(color);
    // Draw four lines to form rectangle
    lcd_draw_line(x, y, x + width - 1, y, color_index);                           // Top
    lcd_draw_line(x, y + height - 1, x + width - 1, y + height - 1, color_index); // Bottom
    lcd_draw_line(x, y, x, y + height - 1, color_index);                          // Left
    lcd_draw_line(x + width - 1, y, x + width - 1, y + height - 1, color_index);  // Right
}

/******************************************************************************
function: Draw a filled rectangle to the framebuffer
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

    const uint8_t color_index = lcd_color565_to_332(color);

    // Fast fill using optimized loops
    for (uint16_t py = y; py < y + height; py++)
    {
        for (uint16_t px = x; px < x + width; px++)
        {
            framebuffer[py * LCD_WIDTH + px] = color_index;
        }
    }
}

/******************************************************************************
function: Draw a single character to the framebuffer
parameter:
    x     : Top-left X coordinate
    y     : Top-left Y coordinate
    c     : Character to draw
    color : RGB565 color value
returns: none
******************************************************************************/
void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color)
{
    if (current_font == NULL || c < 32 || c > 126)
        return; // invalid font or character

    // Calculate bytes per row (width rounded up to nearest byte boundary)
    uint8_t bytes_per_row = (current_font->width + 7) / 8;
    const uint8_t *char_data = &current_font->table[(c - 32) * current_font->height * bytes_per_row];

    for (uint8_t row = 0; row < current_font->height; row++)
    {
        const uint8_t *row_data = &char_data[row * bytes_per_row];

        for (uint8_t col = 0; col < current_font->width; col++)
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
function: Draw a circle outline to the framebuffer
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
    const uint8_t color_index = lcd_color565_to_332(color);

    while (x <= y)
    {
        // Draw 8 symmetric points
        if (center_x + x < LCD_WIDTH && center_y + y < LCD_HEIGHT)
            framebuffer[(center_y + y) * LCD_WIDTH + (center_x + x)] = color_index;
        if (center_x - x < LCD_WIDTH && center_y + y < LCD_HEIGHT)
            framebuffer[(center_y + y) * LCD_WIDTH + (center_x - x)] = color_index;
        if (center_x + x < LCD_WIDTH && center_y - y < LCD_HEIGHT)
            framebuffer[(center_y - y) * LCD_WIDTH + (center_x + x)] = color_index;
        if (center_x - x < LCD_WIDTH && center_y - y < LCD_HEIGHT)
            framebuffer[(center_y - y) * LCD_WIDTH + (center_x - x)] = color_index;
        if (center_x + y < LCD_WIDTH && center_y + x < LCD_HEIGHT)
            framebuffer[(center_y + x) * LCD_WIDTH + (center_x + y)] = color_index;
        if (center_x - y < LCD_WIDTH && center_y + x < LCD_HEIGHT)
            framebuffer[(center_y + x) * LCD_WIDTH + (center_x - y)] = color_index;
        if (center_x + y < LCD_WIDTH && center_y - x < LCD_HEIGHT)
            framebuffer[(center_y - x) * LCD_WIDTH + (center_x + y)] = color_index;
        if (center_x - y < LCD_WIDTH && center_y - x < LCD_HEIGHT)
            framebuffer[(center_y - x) * LCD_WIDTH + (center_x - y)] = color_index;

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

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color)
{
    if (current_font == NULL)
        return; // invalid font

    uint16_t cursor_x = x;
    uint16_t cursor_y = y;

    while (*text)
    {
        char ch = *text;

        if (ch == '\n')
        {
            cursor_x = x;                     // Reset to start of line
            cursor_y += current_font->height; // Move down one line
        }
        else if (ch == ' ')
        {
            // Handle space - just advance position without drawing
            cursor_x += current_font->width;
        }
        else
        {
            // Check if character would exceed screen width
            if (cursor_x + current_font->width > LCD_WIDTH)
            {
                // Wrap to next line
                cursor_x = x;
                cursor_y += current_font->height;
            }

            // Check if we're still within screen height
            if (cursor_y + current_font->height <= LCD_HEIGHT)
            {
                lcd_draw_char(cursor_x, cursor_y, ch, color);
            }

            cursor_x += current_font->width;
        }
        text++;
    }
}

/******************************************************************************
function: Draw a filled circle to the framebuffer
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

    const uint8_t color_index = lcd_color565_to_332(color);

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
                framebuffer[y * LCD_WIDTH + x] = color_index;
            }
        }
    }
}

/******************************************************************************
function: Draw a filled triangle to the framebuffer
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

    const uint8_t color_index = lcd_color565_to_332(color);

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
            framebuffer[y * LCD_WIDTH + x] = color_index;
        }
    }
}

/******************************************************************************
function: Fill the entire framebuffer with a solid color
parameter:
    color : RGB565 color value to fill with
returns: none
******************************************************************************/
void lcd_fill(uint16_t color)
{
    const uint8_t color_index = lcd_color565_to_332(color);
    for (uint32_t i = 0; i < LCD_HEIGHT * LCD_WIDTH; i++)
    {
        framebuffer[i] = color_index;
    }
}

/******************************************************************************
function: Copy an external image buffer into the framebuffer at specified position
parameter:
    x      : Top-left X coordinate
    y      : Top-left Y coordinate
    width  : Width of the buffer to blit
    height : Height of the buffer to blit
    buffer : Pointer to RGB332 pixel data array (8-bit per pixel)
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
                framebuffer[(y + j) * LCD_WIDTH + (x + i)] = buffer[j * width + i];
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
    if (current_font != NULL)
    {
        return current_font->height;
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
    if (current_font != NULL)
    {
        return current_font->width;
    }
    return 0;
}

/********************************************************************************
function: Initialize the LCD display hardware and framebuffer
returns: none
note: Can only be called once; subsequent calls are ignored
********************************************************************************/
void lcd_init()
{
    if (lcd_initialized)
    {
        return; // already initialized
    }

    // Hardware reset
    lcd_reset(qspi);

    // Initialize QSPI GPIO and PIO
    QSPI_GPIO_Init(qspi);
    QSPI_PIO_Init(qspi);
    // Enable 4-wire mode for data transfers
    QSPI_4Wrie_Mode(&qspi);

    // Initialize DMA for QSPI transfers
    dma_tx = dma_claim_unused_channel(true);
    c = dma_channel_get_default_config(dma_tx);
    channel_config_set_transfer_data_size(&c, DMA_SIZE_8);
    channel_config_set_read_increment(&c, true);
    channel_config_set_write_increment(&c, false);
    channel_config_set_dreq(&c, pio_get_dreq(qspi.pio, qspi.sm, false));
    irq_set_enabled(DMA_IRQ_0, false);

    // SH8601 LCD controller initialization sequence - declared as local array
    sh8601_lcd_init_cmd_t lcd_init_cmds[] = {
        {0xBB, (uint8_t[]){0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x5A, 0xA5}, 8, 0},
        {0xA0, (uint8_t[]){0x00, 0x30, 0x00, 0x02, 0x00, 0x00, 0x04, 0x3F, 0x20, 0x05, 0x3F, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00}, 17, 0},
        {0xA2, (uint8_t[]){0x30, 0x19, 0x60, 0x64, 0x9B, 0x22, 0x38, 0x80, 0xAC, 0x28, 0x7F, 0x7F, 0x7F, 0x20, 0xF8, 0x10, 0x02, 0xFF, 0xFF, 0xF0, 0x90, 0x01, 0x32, 0xA0, 0x91, 0xC0, 0x20, 0x7F, 0xFF, 0x00, 0x54}, 31, 0},
        {0xD0, (uint8_t[]){0x80, 0xAC, 0x21, 0x24, 0x08, 0x09, 0x10, 0x01, 0x80, 0x12, 0xC2, 0x00, 0x22, 0x22, 0xAA, 0x03, 0x10, 0x12, 0x40, 0x14, 0x1E, 0x51, 0x15, 0x00, 0x40, 0x10, 0x00, 0x03, 0x7D, 0x12}, 30, 0},
        {0xA3, (uint8_t[]){0xA0, 0x06, 0xAA, 0x00, 0x08, 0x02, 0x0A, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x55, 0x55}, 22, 0},
        {0xC1, (uint8_t[]){0x33, 0x04, 0x02, 0x02, 0x71, 0x05, 0x24, 0x55, 0x02, 0x00, 0x41, 0x00, 0x53, 0xFF, 0xFF, 0xFF, 0x4F, 0x52, 0x00, 0x4F, 0x52, 0x00, 0x45, 0x3B, 0x0B, 0x02, 0x0D, 0x00, 0xFF, 0x40}, 30, 0},
        {0xC3, (uint8_t[]){0x00, 0x00, 0x00, 0x50, 0x03, 0x00, 0x00, 0x00, 0x01, 0x80, 0x01}, 11, 0},
        {0xC4, (uint8_t[]){0x00, 0x24, 0x33, 0x80, 0x11, 0xEA, 0x64, 0x32, 0xC8, 0x64, 0xC8, 0x32, 0x90, 0x90, 0x11, 0x06, 0xDC, 0xFA, 0x00, 0x00, 0x80, 0xFE, 0x10, 0x10, 0x00, 0x0A, 0x0A, 0x44, 0x50}, 29, 0},
        {0xC5, (uint8_t[]){0x18, 0x00, 0x00, 0x03, 0xFE, 0x08, 0x68, 0x30, 0x10, 0x10, 0x88, 0xDE, 0x0D, 0x08, 0x0F, 0x0F, 0x01, 0x08, 0x68, 0x30, 0x10, 0x10, 0x00}, 23, 0},
        {0xC6, (uint8_t[]){0x05, 0x0A, 0x05, 0x0A, 0x00, 0xE0, 0x2E, 0x0B, 0x12, 0x22, 0x12, 0x22, 0x01, 0x00, 0x00, 0x3F, 0x6A, 0x18, 0xC8, 0x22}, 20, 0},
        {0xC7, (uint8_t[]){0x50, 0x32, 0x28, 0x00, 0xA2, 0x80, 0x8F, 0x00, 0x80, 0xFF, 0x07, 0x11, 0x9F, 0x6F, 0xFF, 0x24, 0x0C, 0x0D, 0x0E, 0x0F}, 20, 0},
        {0xC9, (uint8_t[]){0x33, 0x44, 0x44, 0x01}, 4, 0},
        {0xCF, (uint8_t[]){0x2C, 0x1E, 0x88, 0x58, 0x13, 0x18, 0x56, 0x18, 0x1E, 0x68, 0xF8, 0x00, 0x66, 0x0D, 0x22, 0xC4, 0x0C, 0x77, 0x22, 0x44, 0xAA, 0x55, 0x04, 0x04, 0x12, 0xA0, 0x08}, 28, 0},
        {0xD5, (uint8_t[]){0x50, 0x60, 0x8A, 0x00, 0x35, 0x04, 0x60, 0x10, 0x03, 0x03, 0x03, 0x00, 0x04, 0x02, 0x13, 0x46, 0x03, 0x03, 0x03, 0x03, 0x86, 0x00, 0x00, 0x00, 0x80, 0x52, 0x7C, 0x00, 0x00, 0x00}, 30, 0},
        {0xD6, (uint8_t[]){0x10, 0x32, 0x54, 0x76, 0x98, 0xBA, 0xDC, 0xFE, 0x00, 0x00, 0x01, 0x83, 0x03, 0x03, 0x33, 0x03, 0x03, 0x33, 0x3F, 0x03, 0x03, 0x03, 0x20, 0x20, 0x00, 0x24, 0x51, 0x23, 0x01, 0x00}, 30, 0},
        {0xD7, (uint8_t[]){0x18, 0x1A, 0x1B, 0x1F, 0x0A, 0x08, 0x0E, 0x0C, 0x00, 0x1F, 0x1D, 0x1F, 0x50, 0x60, 0x04, 0x00, 0x1F, 0x1F, 0x1F}, 19, 0},
        {0xD8, (uint8_t[]){0x18, 0x1A, 0x1B, 0x1F, 0x0B, 0x09, 0x0F, 0x0D, 0x01, 0x1F, 0x1D, 0x1F}, 12, 0},
        {0xD9, (uint8_t[]){0x0F, 0x09, 0x0B, 0x1F, 0x18, 0x19, 0x1F, 0x01, 0x1E, 0x1D, 0x1F}, 11, 0},
        {0xDD, (uint8_t[]){0x0E, 0x08, 0x0A, 0x1F, 0x18, 0x19, 0x1F, 0x00, 0x1E, 0x1A, 0x1F}, 11, 0},
        {0xDF, (uint8_t[]){0x44, 0x73, 0x4B, 0x69, 0x00, 0x0A, 0x02, 0x90}, 8, 0},
        {0xE0, (uint8_t[]){0x35, 0x08, 0x19, 0x1C, 0x0C, 0x09, 0x13, 0x2A, 0x54, 0x21, 0x0B, 0x15, 0x13, 0x25, 0x27, 0x08, 0x00}, 17, 0},
        {0xE1, (uint8_t[]){0x3E, 0x08, 0x19, 0x1C, 0x0C, 0x08, 0x13, 0x2A, 0x54, 0x21, 0x0B, 0x14, 0x13, 0x26, 0x27, 0x08, 0x0F}, 17, 0},
        {0xE2, (uint8_t[]){0x19, 0x20, 0x0A, 0x11, 0x09, 0x06, 0x11, 0x25, 0xD4, 0x22, 0x0B, 0x13, 0x12, 0x2D, 0x32, 0x2F, 0x03}, 17, 0},
        {0xE3, (uint8_t[]){0x38, 0x20, 0x0A, 0x11, 0x09, 0x06, 0x11, 0x25, 0xC4, 0x21, 0x0A, 0x12, 0x11, 0x2C, 0x32, 0x2F, 0x27}, 17, 0},
        {0xE4, (uint8_t[]){0x19, 0x20, 0x0D, 0x14, 0x0D, 0x08, 0x12, 0x2A, 0xD4, 0x26, 0x0E, 0x15, 0x13, 0x34, 0x39, 0x2F, 0x03}, 17, 0},
        {0xE5, (uint8_t[]){0x38, 0x20, 0x0D, 0x13, 0x0D, 0x07, 0x12, 0x29, 0xC4, 0x25, 0x0D, 0x15, 0x12, 0x33, 0x39, 0x2F, 0x27}, 17, 0},
        {0xA4, (uint8_t[]){0x85, 0x85, 0x95, 0x82, 0xAF, 0xAA, 0xAA, 0x80, 0x10, 0x30, 0x40, 0x40, 0x20, 0xFF, 0x60, 0x30}, 16, 0},
        {0xA4, (uint8_t[]){0x85, 0x85, 0x95, 0x85}, 4, 0},
        {0xBB, (uint8_t[]){0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, 8, 0},
        {0x11, (uint8_t[]){0x00}, 0, 120},
        // Display ON command (0x29) will be sent AFTER clearing framebuffer
    };

    // Send initialization commands (except display ON)
    tx_param(lcd_init_cmds, sizeof(lcd_init_cmds) / sizeof(sh8601_lcd_init_cmd_t));

    // Set initial brightness
    uint8_t oled_brightness = 0x25 + (LCD_DEFAULT_BRIGHTNESS * (0xFF - 0x25)) / 100;
    sh8601_lcd_init_cmd_t brightness_cmd = {.cmd = 0x51, .data = &oled_brightness, .data_bytes = 1, .delay_ms = 0};
    tx_param(&brightness_cmd, 1);

    // init palette
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

    lcd_set_font(LCD_DEFAULT_FONT_SIZE); // Set default font

    set_window(); // Set the drawing window to full screen

    // Clear framebuffer to black and push to display BEFORE turning display on
    lcd_fill(COLOR_BLACK);
    lcd_swap(); // Push black frame to display

    // Now turn on the display
    sh8601_lcd_init_cmd_t display_on_cmd = {.cmd = 0x29, .data = (uint8_t[]){0x00}, .data_bytes = 0, .delay_ms = 20};
    tx_param(&display_on_cmd, 1);

    lcd_initialized = true; // set the flag to indicate initialization is done
}
/******************************************************************************
function: Set the OLED display brightness
parameter:
    brightness : Brightness level from 0 (off) to 100 (full)
returns: none
******************************************************************************/
void lcd_set_backlight_level(uint8_t brightness)
{
    if (brightness > 100)
    {
        brightness = 100;
    }

    backlight_level = brightness;
    set_brightness_flag = true;
}

void lcd_set_font(FontSize size)
{
    switch (size)
    {
    case FONT_XTRA_SMALL:
        current_font = (FontTable *)&Font8;
        break;
    case FONT_SMALL:
        current_font = (FontTable *)&Font12;
        break;
    case FONT_MEDIUM:
        current_font = (FontTable *)&Font16;
        break;
    case FONT_LARGE:
        current_font = (FontTable *)&Font20;
        break;
    case FONT_XTRA_LARGE:
        current_font = (FontTable *)&Font24;
        break;
    default:
        current_font = (FontTable *)&Font16; // Default to medium if invalid size
        break;
    }
}

/******************************************************************************
function: Send the framebuffer contents to the physical display
parameter: none
returns: none
note: Call this after drawing operations to update the screen. This is the
      only function that actually writes to the display hardware, preventing
      screen tearing and ensuring atomic frame updates.
******************************************************************************/
void lcd_swap(void)
{
    // Set window to full screen
    QSPI_Select(qspi);
    QSPI_REGISTER_Write(qspi, 0x2a);
    QSPI_DATA_Write(qspi, LCD_X_OFFSET >> 8);
    QSPI_DATA_Write(qspi, LCD_X_OFFSET & 0xff);
    QSPI_DATA_Write(qspi, (LCD_WIDTH + LCD_X_OFFSET - 1) >> 8);
    QSPI_DATA_Write(qspi, (LCD_WIDTH + LCD_X_OFFSET - 1) & 0xff);
    QSPI_Deselect(qspi);

    QSPI_Select(qspi);
    QSPI_REGISTER_Write(qspi, 0x2b);
    QSPI_DATA_Write(qspi, 0);
    QSPI_DATA_Write(qspi, 0);
    QSPI_DATA_Write(qspi, (LCD_HEIGHT - 1) >> 8);
    QSPI_DATA_Write(qspi, (LCD_HEIGHT - 1) & 0xff);
    QSPI_Deselect(qspi);

    // Start pixel write command - use QSPI_Pixel_Write like the original
    QSPI_Select(qspi);
    QSPI_Pixel_Write(qspi, 0x2c);

    // Convert framebuffer from RGB332 to RGB565 and send via DMA
    // Configure DMA DREQ before transfer (like original)
    channel_config_set_dreq(&c, pio_get_dreq(qspi.pio, qspi.sm, true));

    for (uint16_t y = 0; y < LCD_HEIGHT; y += LCD_CHUNK_LINES)
    {
        uint16_t lines_to_send = (y + LCD_CHUNK_LINES > LCD_HEIGHT) ? (LCD_HEIGHT - y) : LCD_CHUNK_LINES;
        size_t pixels_in_chunk = LCD_WIDTH * lines_to_send;

        // Static buffer for converted data
        static uint16_t line_buffer[LCD_WIDTH * LCD_CHUNK_LINES];

        // Convert this chunk from RGB332 to RGB565 with byte swapping
        for (size_t i = 0; i < pixels_in_chunk; i++)
        {
            uint8_t palette_index = framebuffer[y * LCD_WIDTH + i];
            uint16_t color = palette[palette_index];
            // Swap bytes: convert from host byte order to big-endian for display
            line_buffer[i] = (color >> 8) | (color << 8);
        }

        // Send this chunk via DMA
        dma_channel_configure(dma_tx,
                              &c,
                              &qspi.pio->txf[qspi.sm],
                              (uint8_t *)line_buffer,
                              pixels_in_chunk * 2,
                              true);

        // Wait for DMA to complete before next chunk
        while (dma_channel_is_busy(dma_tx))
            ;
    }

    // Deselect only after all data is sent
    QSPI_Deselect(qspi);
}

/******************************************************************************
function: Send a command byte to the OLED controller
parameter:
    cmd : Command byte to send
returns: none
note: Low-level function used internally for OLED communication
******************************************************************************/
void lcd_write_cmd(uint8_t cmd)
{
    last_cmd = cmd;
    lcd_send_cmd_data(cmd, NULL, 0);
}

/******************************************************************************
function: Send a single data byte to the OLED controller
parameter:
    data : 8-bit data value to send
returns: none
note: Low-level function used internally for OLED communication
      Sends data for the last command that was sent
******************************************************************************/
void lcd_write_data(uint8_t data)
{
    lcd_send_cmd_data(last_cmd, &data, 1);
}

/******************************************************************************
function: Send a 16-bit data value to the OLED controller
parameter:
    data : 16-bit data value to send (e.g., RGB565 color)
returns: none
note: Low-level function used internally for OLED communication
******************************************************************************/
void lcd_write_data_16bit(uint16_t data)
{
    uint8_t bytes[2] = {data >> 8, data & 0xFF};
    lcd_send_cmd_data(last_cmd, bytes, 2);
}
