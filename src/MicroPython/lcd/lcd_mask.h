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

static inline void lcd_blit_mask_bmp_scaled(int16_t dst_x, int16_t dst_y, uint16_t dst_w, uint16_t dst_h,
                                            uint16_t src_w, uint16_t src_h, const uint8_t *pixels, const uint8_t *mask)
{
    if (!pixels || !mask || !dst_w || !dst_h || !src_w || !src_h) return;
    if (src_w == dst_w && src_h == dst_h)
    {
        lcd_blit_mask_bmp(dst_x, dst_y, dst_w, dst_h, pixels, mask);
        return;
    }
    const int ox = dst_x < 0 ? -(int32_t)dst_x : 0, oy = dst_y < 0 ? -(int32_t)dst_y : 0;
    const int dx = dst_x < 0 ? 0 : dst_x, dy = dst_y < 0 ? 0 : dst_y;
    int w = (int)dst_w - ox, h = (int)dst_h - oy;
    if (dx + w > LCD_MP_WIDTH) w = LCD_MP_WIDTH - dx;
    if (dy + h > LCD_MP_HEIGHT) h = LCD_MP_HEIGHT - dy;
    if (w <= 0 || h <= 0) return;
    for (int row = 0; row < h; ++row)
    {
        const uint32_t offset = ((uint32_t)row + oy) * src_h / dst_h * src_w;
        uint32_t numerator = (uint32_t)ox * src_w;
        for (int col = 0; col < w; ++col)
        {
            const uint32_t pixel = offset + numerator / dst_w;
            numerator += src_w;
            if (mask[pixel >> 3] & (0x80u >> (pixel & 7)))
                LCD_MP_BLIT(dx + col, dy + row, 1, 1, pixels + pixel);
        }
    }
}
