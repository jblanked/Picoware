#include "lcd.h"
#include "../lcd/lcd_config.h"

#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif

void lcd_blit_gb(const uint8_t *pixels, uint_fast8_t line, int gb_width, int gb_height)
{
#ifdef LCD_MP_BLIT
    // Center 288px (144*2) vertically on a 320px screen: 16px top offset
    LCD_MP_BLIT(0, line * 2 + 16, gb_width * 2, 1, pixels);
    LCD_MP_BLIT(0, line * 2 + 16 + 1, gb_width * 2, 1, pixels);
#endif
}

void lcd_char(uint16_t x, uint16_t y, char c, uint16_t color)
{
#ifdef LCD_MP_CHAR
    LCD_MP_CHAR(x, y, c, color, FONT_DEFAULT);
#endif
}

void lcd_string(uint16_t x, uint16_t y, const char *str, uint16_t color)
{
#ifdef LCD_MP_TEXT
    LCD_MP_TEXT(x, y, str, color, FONT_DEFAULT);
#endif
}

void lcd_swap_gb(void)
{
#ifdef LCD_MP_SWAP_REGION
    /* Swap only the Game Boy screen area: 320x288 (160*2 x 144*2) centred
       at y=16 on the 320x320 display. Width=320 fits lcd_line_buffer exactly;
       DO NOT use LCD_MP_WIDTH*2 — that is the full display size, not the GB size. */
    LCD_MP_SWAP_REGION(0, 16, 320, 288);
#elif defined(LCD_MP_SWAP)
    LCD_MP_SWAP();
#endif
}

void lcd_clear_gb(void)
{
#ifdef LCD_MP_CLEAR
    LCD_MP_CLEAR(0x0000); // Clear to black (RGB565)
#endif
}