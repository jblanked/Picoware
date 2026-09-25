#include <string.h>
#include <stdarg.h>

#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"

#include "lcd.h"
#include "st7789_lcd.pio.h"

// PIO configuration
#define LCD_PIO pio1
static uint lcd_pio_sm = 0;
static uint lcd_pio_offset = 0;

static bool lcd_initialised = false; // flag to indicate if the LCD is initialised

static uint16_t lcd_scroll_top = 0;                      // top fixed area for vertical scrolling
static uint16_t lcd_memory_scroll_height = FRAME_HEIGHT; // scroll area height
static uint16_t lcd_scroll_bottom = 0;                   // bottom fixed area for vertical scrolling
static uint16_t lcd_y_offset = 0;                        // offset for vertical scrolling

// Text drawing - simplified for MicroPython extension (no font support needed)
static semaphore_t lcd_sem;

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
// Low-level PIO SPI functions
//

// Helper to set DC and CS pins together
static inline void lcd_set_dc_cs(bool dc, bool cs)
{
    gpio_put_masked((1u << LCD_DCX) | (1u << LCD_CSX), !!dc << LCD_DCX | !!cs << LCD_CSX);
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

// Send 16-bit data (half-word)
void lcd_write16_data(uint8_t len, ...)
{
    va_list args;
    va_start(args, len);

    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(1, 0); // DC=1 (data), CS=0 (active)

    for (uint8_t i = 0; i < len; i++)
    {
        uint16_t data = va_arg(args, int);
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, data >> 8);   // High byte first
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, data & 0xff); // Low byte
    }

    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(0, 1); // CS=1 (inactive)
    va_end(args);
}

void lcd_write16_buf(const uint16_t *buffer, size_t len)
{
    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(1, 0); // DC=1 (data), CS=0 (active)

    for (size_t i = 0; i < len; i++)
    {
        uint16_t color = buffer[i];
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, color >> 8);   // High byte first
        st7789_lcd_put(LCD_PIO, lcd_pio_sm, color & 0xff); // Low byte
    }

    st7789_lcd_wait_idle(LCD_PIO, lcd_pio_sm);
    lcd_set_dc_cs(0, 1); // CS=1 (inactive)
}

//
//  ST7365P LCD controller functions
//

// Select the target of the pixel data in the display RAM that will follow
void lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
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
        uint16_t y_start = lcd_scroll_top + y_virtual;
        uint16_t y_end = y_start + height - 1;
        uint16_t y_limit = lcd_scroll_top + lcd_memory_scroll_height - 1;
        if (y_end >= y_limit)
        {
            y_end = y_limit;
        }
        uint16_t actual_height = y_end - y_start + 1;
        lcd_set_window(x, y_start, x + width - 1, y_end);
        lcd_write16_buf((uint16_t *)pixels, (size_t)width * actual_height);
    }
    else
    {
        // No vertical scrolling, use the actual y-coordinate
        lcd_set_window(x, y, x + width - 1, y + height - 1);
        lcd_write16_buf((uint16_t *)pixels, (size_t)width * height);
    }
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

// Text drawing functions (simplified for MicroPython extension)
void lcd_clear_screen()
{
    lcd_solid_rectangle(0x0000, 0, 0, WIDTH, FRAME_HEIGHT);
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

// Initialize the LCD display
void lcd_init()
{
    if (lcd_initialised)
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

    // Calculate clock divider - target ~75MHz SPI clock
    // PIO runs at 2 instructions per bit, so we need sys_clk / (75MHz * 2)
    float clkdiv = (float)clock_get_hz(clk_sys) / (float)(LCD_BAUDRATE * 2);
    if (clkdiv < 1.0f)
        clkdiv = 1.0f;

    st7789_lcd_program_init(LCD_PIO, lcd_pio_sm, lcd_pio_offset, LCD_SDI, LCD_SCL, clkdiv);

    // Set initial pin states
    lcd_set_dc_cs(0, 1); // CS high (inactive)
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
    lcd_memory_scroll_height = 320;

    lcd_write_cmd(LCD_CMD_SLPOUT); // sleep out
    sleep_ms(10);                  // required to wait at least 5ms

    // Prevent issues with other operations
    sem_init(&lcd_sem, 1, 1);

    // Clear the screen
    lcd_clear_screen();

    // Now that the display is initialized, display RAM garbage is cleared,
    // turn on the display
    lcd_display_on();

    lcd_initialised = true; // Set the initialised flag
}
