#include "flipper.hpp"

void furi_hal_random_fill_buf(void *buffer, size_t len)
{
    uint8_t *buf = (uint8_t *)buffer;
    for (size_t i = 0; i < len; i++)
    {
        buf[i] = (uint8_t)random(256);
    }
}

void canvas_clear(Canvas *canvas, uint16_t color)
{
    canvas->clear(Picoware::Vector(0, 0), canvas->getSize(), color);
}

size_t canvas_current_font_height(const Canvas *canvas)
{
    return 8;
}

void canvas_draw_box(Canvas *canvas, int32_t x, int32_t y, size_t width, size_t height, uint16_t color)
{
    canvas->display->drawRect(x, y, width, height, color);
}

void canvas_draw_dot(Canvas *canvas, int32_t x, int32_t y, uint16_t color)
{
    canvas->display->drawPixel(x, y, color);
}

void canvas_draw_frame(Canvas *canvas, int32_t x, int32_t y, int32_t w, int32_t h, uint16_t color)
{
    canvas->display->drawRect(x, y, w, h, color);
}

void canvas_draw_icon(Canvas *canvas, int32_t x, int32_t y, const uint8_t *icon, int32_t w, int32_t h, uint16_t color)
{
    canvas->display->drawBitmap(x, y, icon, w, h, color);
}

void canvas_draw_line(Canvas *canvas, int32_t x1, int32_t y1, int32_t x2, int32_t y2, uint16_t color)
{
    canvas->display->drawLine(x1, y1, x2, y2, color);
}

void canvas_draw_rframe(Canvas *canvas, int32_t x, int32_t y, size_t width, size_t height, size_t radius, uint16_t color)
{
    canvas->display->drawRoundRect(x, y, width, height, radius, color);
}

void canvas_draw_str(Canvas *canvas, int32_t x, int32_t y, const char *str, uint16_t color)
{
    canvas->text(Picoware::Vector(x, y), str, color);
}

void canvas_draw_str_aligned(Canvas *canvas, int32_t x, int32_t y, int32_t align_x, int32_t align_y, const char *str, uint16_t color)
{
    canvas->text(Picoware::Vector(x, y), str, color);
}

size_t canvas_height(Canvas *canvas)
{
    return canvas->getSize().y;
}

void canvas_set_bitmap_mode(Canvas *canvas, bool alpha)
{
    // nothing to do
}

void canvas_set_color(Canvas *canvas, FlipperColor color)
{
    // nothing to do
}

void canvas_set_font(Canvas *canvas, FlipperFont font)
{
    // nothing to do
}

uint16_t canvas_string_width(Canvas *canvas, const char *str)
{
    // width in pixels.
    return strlen(str) * 8;
}

size_t canvas_width(Canvas *canvas)
{
    return canvas->getSize().x;
}