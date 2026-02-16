#include "lcd.h"

static bool lcd_initialized = false; // flag to indicate if the LCD is initialized

// Static framebuffer (16-bit per pixel for RGB565)
uint8_t framebuffer[LCD_WIDTH * LCD_HEIGHT];
static uint16_t palette[256]; // 256-color palette for RGB332
static uint8_t backlight_level;
static uint slice_num;

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

/******************************************************************************
 * function: Initialize the backlight PWM for the LCD
 * parameter: none
 * returns: none
 ******************************************************************************/
static void lcd_backlight_init(void)
{
    // PWM Config
    gpio_set_function(LCD_BL_PIN, GPIO_FUNC_PWM); // Set backlight pin to PWM mode
    slice_num = pwm_gpio_to_slice_num(LCD_BL_PIN);
    pwm_set_wrap(slice_num, 100);                               // 0-100 range
    backlight_level = LCD_DEFAULT_BRIGHTNESS;                   // start at default brightness
    pwm_set_chan_level(slice_num, PWM_CHAN_B, backlight_level); // Start at default brightness
    pwm_set_clkdiv(slice_num, 50);
    pwm_set_enabled(slice_num, true);
}

/******************************************************************************
function: Draw a single pixel to the framebuffer
parameter:
    X     : X coordinate (0 to LCD_WIDTH-1)
    Y     : Y coordinate (0 to LCD_HEIGHT-1)
    color : RGB565 color value
returns: none
******************************************************************************/
void lcd_draw_pixel(uint8_t x, uint8_t y, uint16_t color)
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
void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize font_size)
{
    const FontTable current_font = font_get_table(font_size);
    if (c < 32 || c > 126)
        return; // invalid font or character

    // Calculate bytes per row (width rounded up to nearest byte boundary)
    uint8_t bytes_per_row = (current_font.width + 7) / 8;
    const uint8_t *char_data = &current_font.table[(c - 32) * current_font.height * bytes_per_row];

    for (uint8_t row = 0; row < current_font.height; row++)
    {
        const uint8_t *row_data = &char_data[row * bytes_per_row];

        for (uint8_t col = 0; col < current_font.width; col++)
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

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize font_size)
{
    const FontTable current_font = font_get_table(font_size);

    uint16_t cursor_x = x;
    uint16_t cursor_y = y;

    while (*text)
    {
        char ch = *text;

        if (ch == '\n')
        {
            cursor_x = x;                    // Reset to start of line
            cursor_y += current_font.height; // Move down one line
        }
        else if (ch == ' ')
        {
            // Handle space - just advance position without drawing
            cursor_x += current_font.width;
        }
        else
        {
            // Check if character would exceed screen width
            if (cursor_x + current_font.width > LCD_WIDTH)
            {
                // Wrap to next line
                cursor_x = x;
                cursor_y += current_font.height;
            }

            // Check if we're still within screen height
            if (cursor_y + current_font.height <= LCD_HEIGHT)
            {
                lcd_draw_char(cursor_x, cursor_y, ch, color, font_size);
            }

            cursor_x += current_font.width;
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
function: Draw a filled rounded rectangle to the framebuffer
parameter:
    x      : Top-left X coordinate
    y      : Top-left Y coordinate
    width  : Width of rectangle
    height : Height of rectangle
    radius : Corner radius in pixels
    color  : RGB565 color value
returns: none
******************************************************************************/
void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color)
{
    if (width <= 0 || height <= 0 || radius <= 0)
        return;

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
    if (x + width > LCD_WIDTH)
    {
        width = LCD_WIDTH - x;
    }
    if (y + height > LCD_HEIGHT)
    {
        height = LCD_HEIGHT - y;
    }

    if (width <= 0 || height <= 0)
        return;

    // Calculate effective radius considering clipping
    int effective_radius = radius;
    if (effective_radius > width / 2)
        effective_radius = width / 2;
    if (effective_radius > height / 2)
        effective_radius = height / 2;

    uint8_t color_index = lcd_color565_to_332(color);

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
                framebuffer[py * LCD_WIDTH + px] = color_index;
            }
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
void lcd_blit(uint8_t x, uint8_t y, uint8_t width, uint8_t height, const uint8_t *buffer)
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
function: Initialize the LCD display hardware and framebuffer
parameter:
    horizontal : true for horizontal/landscape mode, false for vertical/portrait mode
returns: none
note: Can only be called once; subsequent calls are ignored
********************************************************************************/
void lcd_init(bool horizontal)
{
    if (lcd_initialized)
    {
        return; // already initialized
    }

    // initialize the GPIO
    gpio_init(LCD_RST_PIN);
    gpio_init(LCD_DC_PIN);
    gpio_init(LCD_CS_PIN);
    gpio_init(LCD_BL_PIN);

    gpio_set_dir(LCD_RST_PIN, GPIO_OUT);
    gpio_set_dir(LCD_DC_PIN, GPIO_OUT);
    gpio_set_dir(LCD_CS_PIN, GPIO_OUT);
    gpio_set_dir(LCD_BL_PIN, GPIO_OUT);

    gpio_put(LCD_CS_PIN, 1);
    gpio_put(LCD_DC_PIN, 0);
    gpio_put(LCD_BL_PIN, 1);

    // SPI init
    spi_init(LCD_SPI_PORT, LCD_BAUDRATE);
    gpio_set_function(LCD_CLK_PIN, GPIO_FUNC_SPI);
    gpio_set_function(LCD_MOSI_PIN, GPIO_FUNC_SPI);

    // Hardware reset
    lcd_reset();

    // Set the read / write scan direction of the frame memory
    lcd_write_cmd(0x36); // MX, MY, RGB mode

    lcd_write_data(horizontal ? 0xc8 : 0X68); // 0x08 set RGB

    // Set the initialization register
    lcd_write_cmd(0xEF);
    lcd_write_cmd(0xEB);
    lcd_write_data(0x14);

    lcd_write_cmd(0xFE);
    lcd_write_cmd(0xEF);

    lcd_write_cmd(0xEB);
    lcd_write_data(0x14);

    lcd_write_cmd(0x84);
    lcd_write_data(0x40);

    lcd_write_cmd(0x85);
    lcd_write_data(0xFF);

    lcd_write_cmd(0x86);
    lcd_write_data(0xFF);

    lcd_write_cmd(0x87);
    lcd_write_data(0xFF);

    lcd_write_cmd(0x88);
    lcd_write_data(0x0A);

    lcd_write_cmd(0x89);
    lcd_write_data(0x21);

    lcd_write_cmd(0x8A);
    lcd_write_data(0x00);

    lcd_write_cmd(0x8B);
    lcd_write_data(0x80);

    lcd_write_cmd(0x8C);
    lcd_write_data(0x01);

    lcd_write_cmd(0x8D);
    lcd_write_data(0x01);

    lcd_write_cmd(0x8E);
    lcd_write_data(0xFF);

    lcd_write_cmd(0x8F);
    lcd_write_data(0xFF);

    lcd_write_cmd(0xB6);
    lcd_write_data(0x00);
    lcd_write_data(0x20);

    lcd_write_cmd(0x36);
    lcd_write_data(0x08); // Set as vertical screen

    lcd_write_cmd(0x3A);
    lcd_write_data(0x05);

    lcd_write_cmd(0x90);
    lcd_write_data(0x08);
    lcd_write_data(0x08);
    lcd_write_data(0x08);
    lcd_write_data(0x08);

    lcd_write_cmd(0xBD);
    lcd_write_data(0x06);

    lcd_write_cmd(0xBC);
    lcd_write_data(0x00);

    lcd_write_cmd(0xFF);
    lcd_write_data(0x60);
    lcd_write_data(0x01);
    lcd_write_data(0x04);

    lcd_write_cmd(0xC3);
    lcd_write_data(0x13);
    lcd_write_cmd(0xC4);
    lcd_write_data(0x13);

    lcd_write_cmd(0xC9);
    lcd_write_data(0x22);

    lcd_write_cmd(0xBE);
    lcd_write_data(0x11);

    lcd_write_cmd(0xE1);
    lcd_write_data(0x10);
    lcd_write_data(0x0E);

    lcd_write_cmd(0xDF);
    lcd_write_data(0x21);
    lcd_write_data(0x0c);
    lcd_write_data(0x02);

    lcd_write_cmd(0xF0);
    lcd_write_data(0x45);
    lcd_write_data(0x09);
    lcd_write_data(0x08);
    lcd_write_data(0x08);
    lcd_write_data(0x26);
    lcd_write_data(0x2A);

    lcd_write_cmd(0xF1);
    lcd_write_data(0x43);
    lcd_write_data(0x70);
    lcd_write_data(0x72);
    lcd_write_data(0x36);
    lcd_write_data(0x37);
    lcd_write_data(0x6F);

    lcd_write_cmd(0xF2);
    lcd_write_data(0x45);
    lcd_write_data(0x09);
    lcd_write_data(0x08);
    lcd_write_data(0x08);
    lcd_write_data(0x26);
    lcd_write_data(0x2A);

    lcd_write_cmd(0xF3);
    lcd_write_data(0x43);
    lcd_write_data(0x70);
    lcd_write_data(0x72);
    lcd_write_data(0x36);
    lcd_write_data(0x37);
    lcd_write_data(0x6F);

    lcd_write_cmd(0xED);
    lcd_write_data(0x1B);
    lcd_write_data(0x0B);

    lcd_write_cmd(0xAE);
    lcd_write_data(0x77);

    lcd_write_cmd(0xCD);
    lcd_write_data(0x63);

    lcd_write_cmd(0x70);
    lcd_write_data(0x07);
    lcd_write_data(0x07);
    lcd_write_data(0x04);
    lcd_write_data(0x0E);
    lcd_write_data(0x0F);
    lcd_write_data(0x09);
    lcd_write_data(0x07);
    lcd_write_data(0x08);
    lcd_write_data(0x03);

    lcd_write_cmd(0xE8);
    lcd_write_data(0x34);

    lcd_write_cmd(0x62);
    lcd_write_data(0x18);
    lcd_write_data(0x0D);
    lcd_write_data(0x71);
    lcd_write_data(0xED);
    lcd_write_data(0x70);
    lcd_write_data(0x70);
    lcd_write_data(0x18);
    lcd_write_data(0x0F);
    lcd_write_data(0x71);
    lcd_write_data(0xEF);
    lcd_write_data(0x70);
    lcd_write_data(0x70);

    lcd_write_cmd(0x63);
    lcd_write_data(0x18);
    lcd_write_data(0x11);
    lcd_write_data(0x71);
    lcd_write_data(0xF1);
    lcd_write_data(0x70);
    lcd_write_data(0x70);
    lcd_write_data(0x18);
    lcd_write_data(0x13);
    lcd_write_data(0x71);
    lcd_write_data(0xF3);
    lcd_write_data(0x70);
    lcd_write_data(0x70);

    lcd_write_cmd(0x64);
    lcd_write_data(0x28);
    lcd_write_data(0x29);
    lcd_write_data(0xF1);
    lcd_write_data(0x01);
    lcd_write_data(0xF1);
    lcd_write_data(0x00);
    lcd_write_data(0x07);

    lcd_write_cmd(0x66);
    lcd_write_data(0x3C);
    lcd_write_data(0x00);
    lcd_write_data(0xCD);
    lcd_write_data(0x67);
    lcd_write_data(0x45);
    lcd_write_data(0x45);
    lcd_write_data(0x10);
    lcd_write_data(0x00);
    lcd_write_data(0x00);
    lcd_write_data(0x00);

    lcd_write_cmd(0x67);
    lcd_write_data(0x00);
    lcd_write_data(0x3C);
    lcd_write_data(0x00);
    lcd_write_data(0x00);
    lcd_write_data(0x00);
    lcd_write_data(0x01);
    lcd_write_data(0x54);
    lcd_write_data(0x10);
    lcd_write_data(0x32);
    lcd_write_data(0x98);

    lcd_write_cmd(0x74);
    lcd_write_data(0x10);
    lcd_write_data(0x85);
    lcd_write_data(0x80);
    lcd_write_data(0x00);
    lcd_write_data(0x00);
    lcd_write_data(0x4E);
    lcd_write_data(0x00);

    lcd_write_cmd(0x98);
    lcd_write_data(0x3e);
    lcd_write_data(0x07);

    lcd_write_cmd(0x35);
    lcd_write_cmd(0x21);

    lcd_write_cmd(0x11);
    sleep_ms(120);
    lcd_write_cmd(0x29);
    sleep_ms(20);

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

    lcd_backlight_init(); // Initialize backlight PWM

    lcd_initialized = true; // set the flag to indicate initialization is done
}

/********************************************************************************
function: Hardware reset sequence for the LCD display
parameter: none
returns: none
note: Toggles the reset pin and performs timing delays
********************************************************************************/
void lcd_reset(void)
{
    gpio_put(LCD_RST_PIN, 1);
    sleep_ms(100);
    gpio_put(LCD_RST_PIN, 0);
    sleep_ms(100);
    gpio_put(LCD_RST_PIN, 1);
    gpio_put(LCD_CS_PIN, 0);
    sleep_ms(100);
}

/******************************************************************************
function: Set the LCD backlight brightness using PWM
parameter:
    brightness : Brightness level from 0 (off) to 100 (full)
returns: none
******************************************************************************/
void lcd_set_backlight_level(uint8_t brightness)
{
    if (brightness < 0)
    {
        backlight_level = 0;
    }
    else if (brightness > 100)
    {
        backlight_level = 100;
    }
    else
    {
        backlight_level = brightness;
    }

    pwm_set_chan_level(slice_num, PWM_CHAN_B, backlight_level);
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
    // set the X coordinates
    lcd_write_cmd(0x2A);
    lcd_write_data(0x00);
    lcd_write_data(0);
    lcd_write_data((LCD_WIDTH - 1) >> 8);
    lcd_write_data(LCD_WIDTH - 1);

    // set the Y coordinates
    lcd_write_cmd(0x2B);
    lcd_write_data(0x00);
    lcd_write_data(0);
    lcd_write_data((LCD_HEIGHT - 1) >> 8);
    lcd_write_data(LCD_HEIGHT - 1);

    lcd_write_cmd(0X2C);

    gpio_put(LCD_DC_PIN, 1);

    // Convert 8-bit palette indices to 16-bit RGB565 and send
    for (uint32_t i = 0; i < LCD_WIDTH * LCD_HEIGHT; i++)
    {
        uint8_t palette_index = framebuffer[i];
        uint16_t color = palette[palette_index];
        uint8_t high_byte = color >> 8;
        uint8_t low_byte = color & 0xFF;
        uint8_t data[2] = {high_byte, low_byte};
        spi_write_blocking(LCD_SPI_PORT, data, 2);
    }
}

/******************************************************************************
function: Send a command byte to the LCD controller
parameter:
    cmd : Command byte to send
returns: none
note: Low-level function used internally for LCD communication
******************************************************************************/
void lcd_write_cmd(uint8_t cmd)
{
    gpio_put(LCD_DC_PIN, 0);
    spi_write_blocking(LCD_SPI_PORT, &cmd, 1);
}

/******************************************************************************
function: Send a single data byte to the LCD controller
parameter:
    data : 8-bit data value to send
returns: none
note: Low-level function used internally for LCD communication
******************************************************************************/
void lcd_write_data(uint8_t data)
{
    gpio_put(LCD_DC_PIN, 1);
    spi_write_blocking(LCD_SPI_PORT, &data, 1);
}

/******************************************************************************
function: Send a 16-bit data value to the LCD controller
parameter:
    data : 16-bit data value to send (e.g., RGB565 color)
returns: none
note: Low-level function used internally for LCD communication
******************************************************************************/
void lcd_write_data_16bit(uint16_t data)
{
    gpio_put(LCD_DC_PIN, 1);
    uint8_t high_byte = data >> 8;
    uint8_t low_byte = data & 0xFF;
    spi_write_blocking(LCD_SPI_PORT, &high_byte, 1);
    spi_write_blocking(LCD_SPI_PORT, &low_byte, 1);
}
