/*
 * LCD Driver for Crow Panel Advanced 10.1-inch ESP32-P4 HMI AI Display
 * Copyright © 2026 JBlanked
 * https://github.com/jblanked
 *
 * Adapted from https://github.com/Elecrow-RD/CrowPanel-Advanced-10.1inch-ESP32-P4-HMI-AI-Display-1024x600-IPS-Touch-Screen/blob/master/example/V1.0/idf-code/Lesson07-Turn_on_the_screen/peripheral/bsp_illuminate/bsp_illuminate.c
 */

#include "esp_ldo_regulator.h" // LDO Function-related API Functions
#include "esp_lcd_ek79007.h"   // lcd ek79007 Function-related API Functions
#include "esp_lcd_mipi_dsi.h"  // lcd mipi dsi Function-related API Functions
#include "esp_lcd_panel_ops.h" // lcd panel ops Function-related API Functions
#include "esp_lcd_panel_io.h"  // lcd panel io Function-related API Functions
#include "driver/gpio.h"       // GPIO Function-related API Functions
#include "driver/ledc.h"       // LEDC PWM Function-related API Functions
#include "esp_attr.h"          // ESP32 attribute macros (PSRAM)
#include <stdlib.h>
#include "lcd.h"

static esp_lcd_panel_handle_t panel_handle = NULL;   /* Type of LCD panel handle */
static esp_lcd_dsi_bus_handle_t mipi_dsi_bus = NULL; /* Type of MIPI DSI bus handle */
static esp_lcd_panel_io_handle_t mipi_dbi_io = NULL; /* Type of LCD panel IO handle */
static esp_ldo_channel_handle_t ldo4 = NULL;         // Handle for LDO channel 4
static esp_ldo_channel_handle_t ldo3 = NULL;         // Handle for LDO channel 3

static bool lcd_initialized = false; // Flag to track LCD initialization status

static FontTable *current_font = NULL; // Pointer to current font table structure

static uint8_t backlight_level; // Variable to store current backlight brightness level (0-100)

/* Static frame buffer in PSRAM - LCD_WIDTH * LCD_HEIGHT * 2 bytes (16bpp RGB565) */
static EXT_RAM_BSS_ATTR uint16_t frame_buffer[LCD_WIDTH * LCD_HEIGHT]; // Frame buffer in external PSRAM

static esp_err_t lcd_backlight_init(void) // Initialize LCD backlight (PWM control)
{
    esp_err_t err = ESP_OK; // Error status variable
    const gpio_config_t gpio_cofig = {
        // GPIO configuration for backlight pin
        .pin_bit_mask = (1ULL << LCD_BACKLIGHT_PIN), // Select backlight GPIO pin
        .mode = GPIO_MODE_OUTPUT,                    // Configure as output
        .pull_up_en = false,                         // Disable pull-up
        .pull_down_en = false,                       // Disable pull-down
        .intr_type = GPIO_INTR_DISABLE,              // Disable interrupt
    };
    err = gpio_config(&gpio_cofig); // Apply GPIO config
    if (err != ESP_OK)
        return err; // Return error if failed

    const ledc_timer_config_t timer_config = {
        // LEDC timer configuration
        .clk_cfg = LEDC_USE_PLL_DIV_CLK,      // Use PLL clock
        .duty_resolution = LEDC_TIMER_11_BIT, // 11-bit duty resolution
        .freq_hz = LCD_BACKLIGHT_PWM_HZ,      // Backlight PWM frequency
        .speed_mode = LEDC_LOW_SPEED_MODE,    // Low-speed mode
        .timer_num = LEDC_TIMER_0,            // Timer 0
    };

    const ledc_channel_config_t channel_config = {
        // LEDC channel configuration
        .gpio_num = LCD_BACKLIGHT_PIN,     // Backlight GPIO pin
        .speed_mode = LEDC_LOW_SPEED_MODE, // Low-speed mode
        .channel = LEDC_CHANNEL_0,         // Channel 0
        .intr_type = LEDC_INTR_DISABLE,    // Disable interrupt
        .timer_sel = LEDC_TIMER_0,         // Use timer 0
        .duty = 0,                         // Initial duty = 0
        .hpoint = 0,                       // Start point
    };
    err = ledc_timer_config(&timer_config); // Configure LEDC timer
    if (err != ESP_OK)
        return err;
    return ledc_channel_config(&channel_config); // Configure LEDC channel
}

static esp_err_t lcd_port_init(void) // Initialize LCD port (MIPI DSI + panel config)
{
    esp_err_t err = ESP_OK;
    lcd_color_rgb_pixel_format_t dpi_pixel_format; // Pixel format variable
    esp_lcd_dsi_bus_config_t bus_config = {
        // MIPI DSI bus config
        .bus_id = 0,                                 // Bus ID = 0
        .num_data_lanes = 2,                         // 2 data lanes
        .phy_clk_src = MIPI_DSI_PHY_CLK_SRC_DEFAULT, // Default PHY clock source
        .lane_bit_rate_mbps = 900,                   // Lane bit rate = 900 Mbps
    };
    err = esp_lcd_new_dsi_bus(&bus_config, &mipi_dsi_bus); // Create new DSI bus
    if (err != ESP_OK)
        return err;
    esp_lcd_dbi_io_config_t dbi_config = {
        // DBI interface config
        .virtual_channel = 0, // Virtual channel = 0
        .lcd_cmd_bits = 8,    // 8-bit command
        .lcd_param_bits = 8,  // 8-bit parameter
    };
    err = esp_lcd_new_panel_io_dbi(mipi_dsi_bus, &dbi_config, &mipi_dbi_io); // Create new DBI IO
    if (err != ESP_OK)
        return err;
    if (BITS_PER_PIXEL == 24)
        dpi_pixel_format = LCD_COLOR_PIXEL_FORMAT_RGB888; // 24-bit RGB888
    else if (BITS_PER_PIXEL == 18)
        dpi_pixel_format = LCD_COLOR_PIXEL_FORMAT_RGB666; // 18-bit RGB666
    else if (BITS_PER_PIXEL == 16)
        dpi_pixel_format = LCD_COLOR_PIXEL_FORMAT_RGB565; // 16-bit RGB565

    const esp_lcd_dpi_panel_config_t dpi_config = {
        // DPI panel config
        .dpi_clk_src = MIPI_DSI_DPI_CLK_SRC_DEFAULT, // Default DPI clock source
        .dpi_clock_freq_mhz = 51,                    // DPI clock frequency = 51 MHz
        .virtual_channel = 0,                        // Virtual channel = 0
        .pixel_format = dpi_pixel_format,            // Pixel format
        .num_fbs = 0,                                // No internally allocated frame buffers (we manage our own)
        .video_timing = {
            // Video timing parameters
            .h_size = LCD_WIDTH,      // Horizontal size
            .v_size = LCD_HEIGHT,     // Vertical size
            .hsync_back_porch = 160,  // HSync back porch
            .hsync_pulse_width = 70,  // HSync pulse width
            .hsync_front_porch = 160, // HSync front porch
            .vsync_back_porch = 23,   // VSync back porch
            .vsync_pulse_width = 10,  // VSync pulse width
            .vsync_front_porch = 12,  // VSync front porch
        },
        .flags.use_dma2d = true, // Enable DMA2D
    };

    ek79007_vendor_config_t vendor_config = {
        // Vendor-specific config
        .mipi_config = {
            .dsi_bus = mipi_dsi_bus,   // DSI bus handle
            .dpi_config = &dpi_config, // DPI config reference
        },
    };
    const esp_lcd_panel_dev_config_t panel_config = {
        // Panel device config
        .reset_gpio_num = -1,                       // No reset GPIO
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB, // RGB order
        .bits_per_pixel = BITS_PER_PIXEL,           // Pixel depth
        .vendor_config = &vendor_config,            // Vendor config pointer
    };
    err = esp_lcd_new_panel_ek79007(mipi_dbi_io, &panel_config, &panel_handle); // Create new EK79007 panel
    if (err != ESP_OK)
        return err;
    err = esp_lcd_panel_reset(panel_handle); // Reset panel
    if (err != ESP_OK)
        return err;
    return esp_lcd_panel_init(panel_handle); // Initialize panel
}

void lcd_deinit(void) // De-initialize LCD and free resources
{
    esp_err_t err = ESP_OK;
    err = esp_lcd_panel_del(panel_handle); // Delete panel handle
    if (err != ESP_OK)
    {
        printf("lcd: deinit panel_handle error, %s\n", esp_err_to_name(err));
    }
    err = esp_lcd_panel_io_del(mipi_dbi_io); // Delete panel IO
    if (err != ESP_OK)
    {
        printf("lcd: deinit mipi_dbi_io error, %s\n", esp_err_to_name(err));
    }
    err = esp_lcd_del_dsi_bus(mipi_dsi_bus); // Delete DSI bus
    if (err != ESP_OK)
    {
        printf("lcd: deinit mipi_dsi_bus error, %s\n", esp_err_to_name(err));
    }

    panel_handle = NULL; // Clear panel handle
    mipi_dbi_io = NULL;  // Clear DBI IO handle
    mipi_dsi_bus = NULL; // Clear DSI bus handle

    lcd_set_backlight(0); // Turn off backlight

    lcd_initialized = false; // Reset initialization flag
}

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color) // Write a pixel into the frame buffer at (x, y)
{
    if (!lcd_initialized) // Check if LCD is initialized
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
    if (!lcd_initialized || panel_handle == NULL) // Check if LCD is initialized
    {
        printf("lcd: LCD not initialized\n");
        return;
    }

    // Push the full frame buffer to the panel over DMA
    static esp_err_t err;
    err = esp_lcd_panel_draw_bitmap(panel_handle, 0, 0, LCD_WIDTH, LCD_HEIGHT, frame_buffer);
    if (err != ESP_OK)
    {
        printf("lcd: Failed to draw bitmap to panel, %s\n", esp_err_to_name(err));
    }
}

bool lcd_init(void) // Initialize LCD and set up necessary configurations
{
    if (lcd_initialized) // Check if already initialized
    {
        return true; // Return success if already initialized
    }
    esp_ldo_channel_config_t ldo3_cof = {
        // LDO3 configuration
        .chan_id = 3,       // LDO channel ID = 3
        .voltage_mv = 2500, // Set output voltage = 2500 mV
    };
    if (esp_ldo_acquire_channel(&ldo3_cof, &ldo3) != ESP_OK) // Acquire LDO3 channel
    {
        printf("lcd: Failed to acquire LDO3 channel\n");
        return false; // Return failure if acquisition fails
    }
    esp_ldo_channel_config_t ldo4_cof = {
        // LDO4 configuration
        .chan_id = 4,       // LDO channel ID = 4
        .voltage_mv = 3300, // Set output voltage = 3300 mV
    };
    if (esp_ldo_acquire_channel(&ldo4_cof, &ldo4) != ESP_OK) // Acquire LDO4 channel
    {
        printf("lcd: Failed to acquire LDO4 channel\n");
        return false; // Return failure if acquisition fails
    }
    if (lcd_backlight_init() != ESP_OK) /* Backlight initialization function */
    {
        printf("lcd: lcd_backlight_init failed\n");
        return false;
    }
    if (lcd_port_init() != ESP_OK) /* Display screen interface initialization function */
    {
        printf("lcd: lcd_port_init failed\n");
        return false;
    }
    lcd_set_backlight(0);                /* Set backlight to off */
    lcd_set_font(LCD_DEFAULT_FONT_SIZE); // Set default font
    lcd_initialized = true;              // Set initialization flag
    return true;                         /* Return success */
}

/* brightness -  (0 - 100) */
bool lcd_set_backlight(uint32_t brightness) // Set LCD backlight brightness
{
    if (brightness != 0) // If brightness > 0
    {
        if (ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, ((brightness * 18) + 200)) != ESP_OK) // Calculate PWM duty
        {
            printf("lcd: ledc_set_duty failed\n");
            return false;
        }
        if (ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0) != ESP_OK) // Apply duty update
        {
            printf("lcd: ledc_update_duty failed\n");
            return false;
        }
    }
    else // If brightness = 0, turn off
    {
        if (ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0) != ESP_OK) // Set duty = 0
        {
            printf("lcd: ledc_set_duty failed\n");
            return false;
        }
        if (ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0) != ESP_OK) // Apply duty update
        {
            printf("lcd: ledc_update_duty failed\n");
            return false;
        }
    }
    backlight_level = brightness; // Store current backlight level
    return true;
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

/******************************************************************************
function: Draw a single character to the frame_buffer
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
void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer)
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
function: Set the current font size for text rendering
parameter:
    size : FontSize enum value specifying desired font size
returns: none
********************************************************************************/
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
