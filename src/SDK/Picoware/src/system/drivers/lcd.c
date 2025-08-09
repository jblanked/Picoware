//
//  PicoCalc LCD display driver
//
//  This driver interfaces with the ST7789P LCD controller on the PicoCalc.
//
//  It is optimised for a character-based display with a fixed-width, 8-pixel wide font
//  and 65K colours in the RGB565 format. This driver requires little memory as it
//  uses the frame memory on the controller directly.
//
//  NOTE: Some code below is written to respect timing constraints of the ST7789P controller.
//        For instance, you can usually get away with a short chip select high pulse widths, but
//        writing to the display RAM requires the minimum chip select high pulse width of 40ns.
//

#include <string.h>

#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/spi.h"

#include "lcd.h"

static bool lcd_initialised = false; // flag to indicate if the LCD is initialised

static uint16_t lcd_scroll_top = 0;                      // top fixed area for vertical scrolling
static uint16_t lcd_memory_scroll_height = FRAME_HEIGHT; // scroll area height
static uint16_t lcd_scroll_bottom = 0;                   // bottom fixed area for vertical scrolling
static uint16_t lcd_y_offset = 0;                        // offset for vertical scrolling

static uint16_t foreground = 0xFFFF; // default foreground colour (white)
static uint16_t background = 0x0000; // default background colour (black)

static bool underscore = false; // underscore state
static bool reverse = false;    // reverse video state
static bool bold = false;       // bold text state

// Text drawing
const font_t *font = &font_8x10; // default font is 8x10
static uint16_t char_buffer[8 * GLYPH_HEIGHT] __attribute__((aligned(4)));

// Background processing
static semaphore_t lcd_sem;
static repeating_timer_t cursor_timer;

//
// Character attributes
//

void lcd_set_reverse(bool reverse_on)
{
    // swap foreground and background colors if reverse is "reversed"
    if ((reverse && !reverse_on) || (!reverse && reverse_on))
    {
        uint16_t temp = foreground;
        foreground = background;
        background = temp;
    }
    reverse = reverse_on;
}

void lcd_set_underscore(bool underscore_on)
{
    // Underscore is not implemented, but we can toggle the state
    underscore = underscore_on;
}

void lcd_set_bold(bool bold_on)
{
    // Toggles the bold state. Bold text is implemented in the lcd_putc function.
    bold = bold_on;
}

void lcd_set_font(const font_t *new_font)
{
    // Set the new font
    font = new_font;
}

uint8_t lcd_get_columns(void)
{
    // Calculate the number of columns based on the font width and display width
    return WIDTH / font->width;
}

uint8_t lcd_get_glyph_width(void)
{
    // Return the width of the current font glyph
    return font->width;
}

// Set foreground colour
void lcd_set_foreground(uint16_t colour)
{
    if (reverse)
    {
        background = colour; // if reverse is enabled, set background to the new foreground colour
    }
    else
    {
        foreground = colour;
    }
}

// Set background colour
void lcd_set_background(uint16_t colour)
{
    if (reverse)
    {
        foreground = colour; // if reverse is enabled, set foreground to the new background colour
    }
    else
    {
        background = colour;
    }
}

//
// Protect the LCD access with a semaphore
//

// Check if the LCD is available for access
bool lcd_available()
{
    // Check if the semaphore is available for LCD access
    return sem_available(&lcd_sem);
}

// Protect the SPI bus with a semaphore
void lcd_acquire()
{
    sem_acquire_blocking(&lcd_sem);
}

// Release the SPI bus
void lcd_release()
{
    sem_release(&lcd_sem);
}

//
// Low-level SPI functions
//

// Send a command
void lcd_write_cmd(uint8_t cmd)
{
    gpio_put(LCD_DCX, 0); // Command
    gpio_put(LCD_CSX, 0);
    spi_write_blocking(LCD_SPI, &cmd, 1);
    gpio_put(LCD_CSX, 1);
}

// Send 8-bit data (byte)
void lcd_write_data(uint8_t len, ...)
{
    va_list args;
    va_start(args, len);
    gpio_put(LCD_DCX, 1); // Data
    gpio_put(LCD_CSX, 0);
    for (uint8_t i = 0; i < len; i++)
    {
        uint8_t data = va_arg(args, int); // get the next byte of data
        spi_write_blocking(LCD_SPI, &data, 1);
    }
    gpio_put(LCD_CSX, 1);
    va_end(args);
}

// Send 16-bit data (half-word)
void lcd_write16_data(uint8_t len, ...)
{
    va_list args;

    // DO NOT MOVE THE spi_set_format() OR THE gpio_put(LCD_DCX) CALLS!
    // They are placed before the gpio_put(LCD_CSX) to ensure that a minimum
    // chip select high pulse width is achieved (at least 40ns)
    spi_set_format(LCD_SPI, 16, 0, 0, SPI_MSB_FIRST);

    va_start(args, len);
    gpio_put(LCD_DCX, 1); // Data
    gpio_put(LCD_CSX, 0);
    for (uint8_t i = 0; i < len; i++)
    {
        uint16_t data = va_arg(args, int); // get the next half-word of data
        spi_write16_blocking(LCD_SPI, &data, 1);
    }
    gpio_put(LCD_CSX, 1);
    va_end(args);

    spi_set_format(LCD_SPI, 8, 0, 0, SPI_MSB_FIRST);
}

void lcd_write16_buf(const uint16_t *buffer, size_t len)
{
    // DO NOT MOVE THE spi_set_format() OR THE gpio_put(LCD_DCX) CALLS!
    // They are placed before the gpio_put(LCD_CSX) to ensure that a minimum
    // chip select high pulse width is achieved (at least 40ns)
    spi_set_format(LCD_SPI, 16, 0, 0, SPI_MSB_FIRST);

    gpio_put(LCD_DCX, 1); // Data
    gpio_put(LCD_CSX, 0);
    spi_write16_blocking(LCD_SPI, buffer, len);
    gpio_put(LCD_CSX, 1);

    spi_set_format(LCD_SPI, 8, 0, 0, SPI_MSB_FIRST);
}

//
//  ST7365P LCD controller functions
//

// Select the target of the pixel data in the display RAM that will follow
void lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    // lcd_acquire() and lcd_release() are not needed here, as this function
    // is only called from lcd_blit() which already acquires the semaphore

    // Set column address (X)
    lcd_write_cmd(LCD_CMD_CASET);
    lcd_write_data(4,
                   UPPER8(x0), LOWER8(x0),
                   UPPER8(x1), LOWER8(x1));

    // Set row address (Y)
    lcd_write_cmd(LCD_CMD_RASET);
    lcd_write_data(4,
                   UPPER8(y0), LOWER8(y0),
                   UPPER8(y1), LOWER8(y1));

    // Prepare to write to RAM
    lcd_write_cmd(LCD_CMD_RAMWR);
}

//
//  Send pixel data to the display
//
//  All display RAM updates come through this function. This function is responsible for
//  setting the correct window in the display RAM and writing the pixel data to it. It also
//  handles the vertical scrolling by adjusting the y-coordinate based on the current scroll
//  offset (lcd_y_offset).
//
//  The pixel data is expected to be in RGB565 format, which is a 16-bit value with the
//  red component in the upper 5 bits, the green component in the middle 6 bits, and the
//  blue component in the lower 5 bits.

void lcd_blit(uint16_t *pixels, uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    lcd_acquire();

    if (y >= lcd_scroll_top && y < HEIGHT - lcd_scroll_bottom)
    {
        // Adjust y for vertical scroll offset and wrap within memory height
        uint16_t y_virtual = (lcd_y_offset + y) % lcd_memory_scroll_height;
        uint16_t y_end = lcd_scroll_top + y_virtual + height - 1;
        if (y_end >= lcd_scroll_top + lcd_memory_scroll_height)
        {
            y_end = lcd_scroll_top + lcd_memory_scroll_height - 1;
        }
        lcd_set_window(x, lcd_scroll_top + y_virtual, x + width - 1, y_end);
    }
    else
    {
        // No vertical scrolling, use the actual y-coordinate
        lcd_set_window(x, y, x + width - 1, y + height - 1);
    }

    lcd_write16_buf((uint16_t *)pixels, width * height);
    lcd_release();
}

// Draw a solid rectangle on the display
void lcd_solid_rectangle(uint16_t colour, uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    static uint16_t pixels[WIDTH];

    for (uint16_t row = 0; row < height; row++)
    {
        for (uint16_t i = 0; i < width; i++)
        {
            pixels[i] = colour;
        }
        lcd_blit(pixels, x, y + row, width, 1);
    }
}

//
//  Scrolling area of the display
//
//  This forum post provides a good explanation of how scrolling on the ST7789P display works:
//      https://forum.arduino.cc/t/st7735s-scrolling/564506
//
//  These functions (lcd_define_scrolling, lcd_scroll_up, and lcd_scroll_down) configure and
//  set the vertical scrolling area of the display, but it is the responsibility of lcd_blit()
//  to ensure that the pixel data is written to the correct location in the display RAM.
//

void lcd_define_scrolling(uint16_t top_fixed_area, uint16_t bottom_fixed_area)
{
    uint16_t scroll_area = HEIGHT - (top_fixed_area + bottom_fixed_area);
    if (scroll_area == 0 || scroll_area > FRAME_HEIGHT)
    {
        // Invalid scrolling area, reset to full screen
        top_fixed_area = 0;
        bottom_fixed_area = 0;
        scroll_area = FRAME_HEIGHT;
    }
    
    lcd_scroll_top = top_fixed_area;
    lcd_memory_scroll_height = FRAME_HEIGHT - (top_fixed_area + bottom_fixed_area);
    lcd_scroll_bottom = bottom_fixed_area;

    lcd_acquire();
    lcd_write_cmd(LCD_CMD_VSCRDEF);
    lcd_write_data(6,
                   UPPER8(lcd_scroll_top),
                   LOWER8(lcd_scroll_top),
                   UPPER8(scroll_area),
                   LOWER8(scroll_area),
                   UPPER8(lcd_scroll_bottom),
                   LOWER8(lcd_scroll_bottom));
    lcd_release();

    lcd_scroll_reset(); // Reset the scroll area to the top
}

void lcd_scroll_reset()
{
    // Clear the scrolling area by filling it with the background colour
    lcd_y_offset = 0; // Reset the scroll offset
    uint16_t scroll_area_start = lcd_scroll_top + lcd_y_offset;

    lcd_acquire();
    lcd_write_cmd(LCD_CMD_VSCSAD); // Sets where in display RAM the scroll area starts
    lcd_write_data(2, UPPER8(scroll_area_start), LOWER8(scroll_area_start));
    lcd_release();
}

void lcd_scroll_clear()
{
    lcd_scroll_reset(); // Reset the scroll area to the top

    // Clear the scrolling area
    lcd_solid_rectangle(background, 0, lcd_scroll_top, WIDTH, lcd_memory_scroll_height);
}

// Scroll the screen up one line (make space at the bottom)
void lcd_scroll_up()
{
    // Ensure the scroll height is non-zero to avoid division by zero
    if (lcd_memory_scroll_height == 0) {
        return; // Exit early if the scroll height is invalid
    }
    // This will rotate the content in the scroll area up by one line
    lcd_y_offset = (lcd_y_offset + GLYPH_HEIGHT) % lcd_memory_scroll_height;
    uint16_t scroll_area_start = lcd_scroll_top + lcd_y_offset;

    lcd_acquire();
    lcd_write_cmd(LCD_CMD_VSCSAD); // Sets where in display RAM the scroll area starts
    lcd_write_data(2, UPPER8(scroll_area_start), LOWER8(scroll_area_start));
    lcd_release();

    // Clear the new line at the bottom
    lcd_solid_rectangle(background, 0, HEIGHT - GLYPH_HEIGHT, WIDTH, GLYPH_HEIGHT);
}

// Scroll the screen down one line (making space at the top)
void lcd_scroll_down()
{
    // Ensure lcd_memory_scroll_height is non-zero to avoid division by zero
    if (lcd_memory_scroll_height == 0) {
        return; // Safely exit if the scroll height is zero
    }
    // This will rotate the content in the scroll area down by one line
    lcd_y_offset = (lcd_y_offset - GLYPH_HEIGHT + lcd_memory_scroll_height) % lcd_memory_scroll_height;
    uint16_t scroll_area_start = lcd_scroll_top + lcd_y_offset;

    lcd_acquire();
    lcd_write_cmd(LCD_CMD_VSCSAD); // Sets where in display RAM the scroll area starts
    lcd_write_data(2, UPPER8(scroll_area_start), LOWER8(scroll_area_start));
    lcd_release();

    // Clear the new line at the top
    lcd_solid_rectangle(background, 0, lcd_scroll_top, WIDTH, GLYPH_HEIGHT);
}

//
// Text drawing functions
//

// Clear the entire screen
void lcd_clear_screen()
{
    lcd_scroll_reset(); // Reset the scrolling area to the top
    lcd_solid_rectangle(background, 0, 0, WIDTH, FRAME_HEIGHT);
}

// Draw a character at the specified position
void lcd_putc(uint8_t column, uint8_t row, uint8_t c)
{
    const uint8_t *glyph = &font->glyphs[c * GLYPH_HEIGHT];
    uint16_t *buffer = char_buffer;

    if (font->width == 8)
    {
        for (uint8_t i = 0; i < GLYPH_HEIGHT; i++, glyph++)
        {
            if (i < GLYPH_HEIGHT - 1)
            {
                // Fill the row with the glyph data
                *(buffer++) = (*glyph & 0x80) ? foreground : background;
                *(buffer++) = (*glyph & 0x40) || (bold && (*glyph & 0x80)) ? foreground : background;
                *(buffer++) = (*glyph & 0x20) || (bold && (*glyph & 0x40)) ? foreground : background;
                *(buffer++) = (*glyph & 0x10) || (bold && (*glyph & 0x20)) ? foreground : background;
                *(buffer++) = (*glyph & 0x08) || (bold && (*glyph & 0x10)) ? foreground : background;
                *(buffer++) = (*glyph & 0x04) || (bold && (*glyph & 0x08)) ? foreground : background;
                *(buffer++) = (*glyph & 0x02) || (bold && (*glyph & 0x04)) ? foreground : background;
                *(buffer++) = (*glyph & 0x01) || (bold && (*glyph & 0x02)) ? foreground : background;
            }
            else
            {
                // The last row is where the underscore is drawn, but if no underscore is set, fill with glyph data
                *(buffer++) = (*glyph & 0x80) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x40) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x20) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x10) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x08) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x04) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x02) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x01) || underscore ? foreground : background;
            }
        }
    }
    else
    {
        for (uint8_t i = 0; i < GLYPH_HEIGHT; i++, glyph++)
        {
            if (i < GLYPH_HEIGHT - 1)
            {
                // Fill the row with the glyph data
                *(buffer++) = (*glyph & 0x10) ? foreground : background;
                *(buffer++) = (*glyph & 0x08) ? foreground : background;
                *(buffer++) = (*glyph & 0x04) ? foreground : background;
                *(buffer++) = (*glyph & 0x02) ? foreground : background;
                *(buffer++) = (*glyph & 0x01) ? foreground : background;
            }
            else
            {
                // The last row is where the underscore is drawn, but if no underscore is set, fill with glyph data
                *(buffer++) = (*glyph & 0x10) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x08) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x04) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x02) || underscore ? foreground : background;
                *(buffer++) = (*glyph & 0x01) || underscore ? foreground : background;
            }
        }
    }

    lcd_blit(char_buffer, column * font->width, row * GLYPH_HEIGHT, font->width, GLYPH_HEIGHT);
}

//
// The cursor
//
// A performance cheat: The cursor is drawn as a solid line at the bottom of the
// character cell. The cursor is positioned here since the printable glyphs
// do not extend to that row (on purpose). Drawing and erasing the cursor does
// not corrupt the glyphs.
//
// Except for the box drawing glyphs who do extend into that row. Disable the
// cursor when printing these if you want to see the box drawing glyphs
// uncorrupted.

static uint8_t cursor_column = 0;  // cursor x position for drawing
static uint8_t cursor_row = 0;     // cursor y position for drawing
static bool cursor_enabled = true; // cursor visibility state

// Enable or disable the cursor
void lcd_enable_cursor(bool cursor_on)
{
    // Cursor visibility is not implemented, but we can toggle the state
    cursor_enabled = cursor_on;
}

// Check if the cursor is enabled
bool lcd_cursor_enabled()
{
    // Return the current cursor visibility state
    return cursor_enabled;
}

// Move the cursor to the specified position
// This function updates the cursor position and ensures it is within the bounds of the display.
void lcd_move_cursor(uint8_t column, uint8_t row)
{
    uint8_t max_col = lcd_get_columns() - 1;
    // Move the cursor to the specified position
    cursor_column = column;
    cursor_row = row;

    // Ensure the cursor position is within bounds
    if (cursor_column > max_col)
        cursor_column = max_col;
    if (cursor_row > MAX_ROW)
        cursor_row = MAX_ROW;
}

// Draw the cursor at the current position
void lcd_draw_cursor()
{
    if (cursor_enabled)
    {
        lcd_solid_rectangle(foreground, cursor_column * font->width, ((cursor_row + 1) * GLYPH_HEIGHT) - 1, font->width, 1);
    }
}

// Erase the cursor at the current position
void lcd_erase_cursor()
{
    if (cursor_enabled)
    {
        lcd_solid_rectangle(background, cursor_column * font->width, ((cursor_row + 1) * GLYPH_HEIGHT) - 1, font->width, 1);
    }
}

//
//  Display control functions
//

// Reset the LCD display
void lcd_reset()
{
    // Blip the reset pin to reset the LCD controller
    gpio_put(LCD_RST, 0);
    sleep_us(20); // 20µs reset pulse (10µs minimum)

    gpio_put(LCD_RST, 1);
    sleep_ms(120); // 5ms required after reset, but 120ms needed before sleep out command
}

// Turn on the LCD display
void lcd_display_on()
{
    lcd_acquire();
    lcd_write_cmd(LCD_CMD_DISPON);
    lcd_release();
}

// Turn off the LCD display
void lcd_display_off()
{
    lcd_acquire();
    lcd_write_cmd(LCD_CMD_DISPOFF);
    lcd_release();
}

//
//  Background processing
//
//  Handle background tasks such as blinking the cursor
//

// Blink the cursor at regular intervals
bool on_cursor_timer(repeating_timer_t *rt)
{
    static bool cursor_visible = false;

    if (!lcd_available() || !lcd_cursor_enabled())
    {
        return true; // if the SPI bus is not available or cursor is disabled, do not toggle cursor
    }

    if (cursor_visible)
    {
        lcd_erase_cursor();
    }
    else
    {
        lcd_draw_cursor();
    }

    cursor_visible = !cursor_visible; // Toggle cursor visibility
    return true;                      // Keep the timer running
}

// Initialize the LCD display
void lcd_init()
{
    if (lcd_initialised)
    {
        return; // already initialized
    }

    // initialise GPIO
    gpio_init(LCD_SCL);
    gpio_init(LCD_SDI);
    gpio_init(LCD_SDO);
    gpio_init(LCD_CSX);
    gpio_init(LCD_DCX);
    gpio_init(LCD_RST);

    gpio_set_dir(LCD_SCL, GPIO_OUT);
    gpio_set_dir(LCD_SDI, GPIO_OUT);
    gpio_set_dir(LCD_CSX, GPIO_OUT);
    gpio_set_dir(LCD_DCX, GPIO_OUT);
    gpio_set_dir(LCD_RST, GPIO_OUT);

    // initialise 4-wire SPI
    spi_init(LCD_SPI, LCD_BAUDRATE);
    gpio_set_function(LCD_SCL, GPIO_FUNC_SPI);
    gpio_set_function(LCD_SDI, GPIO_FUNC_SPI);
    gpio_set_function(LCD_SDO, GPIO_FUNC_SPI);

    gpio_put(LCD_CSX, 1);
    gpio_put(LCD_RST, 1);

    lcd_reset(); // reset the LCD controller

    lcd_write_cmd(LCD_CMD_SWRESET); // reset the commands and parameters to their S/W Reset default values
    sleep_ms(10);                   // required to wait at least 5ms

    lcd_write_cmd(LCD_CMD_COLMOD); // pixel format set
    lcd_write_data(1, 0x55);       // 16 bit/pixel (RGB565)

    lcd_write_cmd(LCD_CMD_MADCTL); // memory access control
    lcd_write_data(1, 0x48);       // BGR colour filter panel, top to bottom, left to right

    lcd_write_cmd(LCD_CMD_INVON); // display inversion on

    lcd_write_cmd(LCD_CMD_EMS); // entry mode set
    lcd_write_data(1, 0xC6);    // normal display, 16-bit (RGB) to 18-bit (rgb) colour
                                //   conversion: r(0) = b(0) = G(0)

    lcd_write_cmd(LCD_CMD_VSCRDEF); // vertical scroll definition
    lcd_write_data(6,
                   0x00, 0x00, // top fixed area of 0 pixels
                   0x01, 0x40, // scroll area height of 320 pixels
                   0x00, 0x00  // bottom fixed area of 0 pixels
    );

    lcd_write_cmd(LCD_CMD_SLPOUT); // sleep out
    sleep_ms(10);                  // required to wait at least 5ms

    // Prevent the blinking cursor from interfering with other operations
    sem_init(&lcd_sem, 1, 1);

    // Clear the screen
    lcd_clear_screen();

    // Now that the display is initialized, display RAM garbage is cleared,
    // turn on the display
    lcd_display_on();

    // Blink the cursor every second (500 ms on, 500 ms off)
    add_repeating_timer_ms(500, on_cursor_timer, NULL, &cursor_timer);

    lcd_initialised = true; // Set the initialised flag
}