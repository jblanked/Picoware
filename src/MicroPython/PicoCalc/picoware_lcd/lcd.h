/*
Author: Blair Leduc
License: MIT License
Source: https://github.com/BlairLeduc/picocalc-text-starter
*/

#pragma once

#include "pico/stdlib.h"

#define LCD_SPI (spi1) // SPI interface for the LCD display

// Raspberry Pi Pico board GPIO pins
#define LCD_SCL (10) // serial clock (SCL)
#define LCD_SDI (11) // serial data in (SDI)
#define LCD_SDO (12) // serial data out (SDO)
#define LCD_CSX (13) // chip select (CSX)
#define LCD_DCX (14) // data/command (D/CX)
#define LCD_RST (15) // reset (RESET)

// LCD interface definitions
// According to the ST7789P datasheet, the maximum SPI clock speed is 62.5 MHz.
// However, the controller can handle 75 MHz in practice.
#define LCD_BAUDRATE (75000000) // 75 MHz SPI clock speed

// LCD command definitions
#define LCD_CMD_NOP (0x00)     // no operation
#define LCD_CMD_SWRESET (0x01) // software reset
#define LCD_CMD_SLPIN (0x10)   // sleep in
#define LCD_CMD_SLPOUT (0x11)  // sleep out
#define LCD_CMD_INVOFF (0x20)  // display inversion off
#define LCD_CMD_INVON (0x21)   // display inversion on
#define LCD_CMD_DISPOFF (0x28) // display off
#define LCD_CMD_DISPON (0x29)  // display on
#define LCD_CMD_CASET (0x2A)   // column address set
#define LCD_CMD_RASET (0x2B)   // row address set
#define LCD_CMD_RAMWR (0x2C)   // memory write
#define LCD_CMD_RAMRD (0x2E)   // memory read
#define LCD_CMD_VSCRDEF (0x33) // vertical scroll definition
#define LCD_CMD_MADCTL (0x36)  // memory access control
#define LCD_CMD_VSCSAD (0x37)  // vertical scroll start address of RAM
#define LCD_CMD_COLMOD (0x3A)  // pixel format set
#define LCD_CMD_IFMODE (0xB0)  // interface mode control
#define LCD_CMD_FRMCTR1 (0xB1) // frame rate control (in normal mode)
#define LCD_CMD_FRMCTR2 (0xB2) // frame rate control (in idle mode)
#define LCD_CMD_FRMCTR3 (0xB3) // frame rate control (in partial mode)
#define LCD_CMD_DIC (0xB4)     // display inversion control
#define LCD_CMD_DFC (0xB6)     // display function control
#define LCD_CMD_EMS (0xB7)     // entry mode set
#define LCD_CMD_MODESEL (0xB9) // mode set
#define LCD_CMD_PWR1 (0xC0)    // power control 1
#define LCD_CMD_PWR2 (0xC1)    // power control 2
#define LCD_CMD_PWR3 (0xC2)    // power control 3
#define LCD_CMD_VCMPCTL (0xC5) // VCOM control
#define LCD_CMD_PGC (0xE0)     // positive gamma control
#define LCD_CMD_NGC (0xE1)     // negative gamma control
#define LCD_CMD_DGC1 (0xE2)    // driver gamma control 1
#define LCD_CMD_DGC2 (0xE3)    // driver gamma control
#define LCD_CMD_DOCA (0xE8)    // driver output control
#define LCD_CMD_E9 (0xE9)      // Manufacturer command
#define LCD_CMD_F0 (0xF0)      // Manufacturer command
#define LCD_CMD_F7 (0xF7)      // Manufacturer command

// LCD display parameters
#define WIDTH (320)                  // pixels across the LCD
#define HEIGHT (320)                 // pixels down the LCD
#define FRAME_HEIGHT (480)           // frame memory height in pixels
#define ROWS (HEIGHT / GLYPH_HEIGHT) // number of lines that fit on the LCD
#define MAX_ROW (ROWS - 1)           // maximum row index (0-based)

// Handy macros
#define RGB(r, g, b) ((uint16_t)(((r) >> 3) << 11 | ((g) >> 2) << 5 | ((b) >> 3)))
#define UPPER8(x) ((x) >> 8)   // upper byte of a 16-bit value
#define LOWER8(x) ((x) & 0xFF) // lower byte of a 16-bit value

// Function prototypes

#ifdef __cplusplus
extern "C"
{
#endif

    // colour and display state functions
    void lcd_set_foreground(uint16_t colour);
    void lcd_set_background(uint16_t colour);
    void lcd_set_reverse(bool reverse_on);
    void lcd_set_underscore(bool underscore_on);
    void lcd_set_bold(bool bold_on);
    uint8_t lcd_get_columns(void);
    uint8_t lcd_get_glyph_width(void);

    // Display control functions
    void lcd_reset(void);
    bool lcd_available(void);
    void lcd_acquire(void);
    void lcd_release(void);
    void lcd_display_on(void);
    void lcd_display_off(void);

    // Low-level SPI functions
    void lcd_write_cmd(uint8_t cmd);
    void lcd_write_data(uint8_t len, ...);
    void lcd_write16_data(uint8_t len, ...);
    void lcd_write16_buf(const uint16_t *buffer, size_t len);

    // Display window and drawing functions
    void lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);
    void lcd_blit(uint16_t *pixels, uint16_t x, uint16_t y, uint16_t width, uint16_t height);
    void lcd_solid_rectangle(uint16_t colour, uint16_t x, uint16_t y, uint16_t width, uint16_t height);

    // Scrolling functions
    void lcd_define_scrolling(uint16_t top_fixed_area, uint16_t bottom_fixed_area);
    void lcd_scroll_reset();
    void lcd_scroll_clear();
    void lcd_scroll_up(void);
    void lcd_scroll_down(void);

    // Character and cursor functions
    void lcd_putc(uint8_t column, uint8_t row, uint8_t c);
    void lcd_move_cursor(uint8_t x, uint8_t y);
    void lcd_draw_cursor(void);
    void lcd_erase_cursor(void);
    void lcd_enable_cursor(bool cursor_on);
    bool lcd_cursor_enabled(void);

    // Initialization
    void lcd_clear_screen(void);
    void lcd_init(void);

#ifdef __cplusplus
}
#endif
