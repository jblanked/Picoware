#pragma once
#include <stdint.h>
#include LCD_INCLUDE

static inline void lcd_blit_mask_bmp(int16_t x, int16_t y, uint16_t width, uint16_t height,
                                     const uint8_t *pixels, const uint8_t *mask)
{
    if (!pixels || !mask || !width || !height) return;
    const int sx = x < 0 ? -(int32_t)x : 0, sy = y < 0 ? -(int32_t)y : 0;
    const int dx = x < 0 ? 0 : x, dy = y < 0 ? 0 : y;
    int w = (int)width - sx, h = (int)height - sy;
    if (dx + w > LCD_MP_WIDTH) w = LCD_MP_WIDTH - dx;
    if (dy + h > LCD_MP_HEIGHT) h = LCD_MP_HEIGHT - dy;
    for (int row = 0; row < h; ++row)
    {
        const uint32_t offset = (uint32_t)(sy + row) * width + sx;
        int col = 0;
        while (col < w)
        {
            while (col < w && !(mask[(offset + col) >> 3] & (0x80u >> ((offset + col) & 7)))) ++col;
            int start = col;
            while (col < w && (mask[(offset + col) >> 3] & (0x80u >> ((offset + col) & 7)))) ++col;
            if (start < col) LCD_MP_BLIT(dx + start, dy + row, col - start, 1, pixels + offset + start);
        }
    }
}
