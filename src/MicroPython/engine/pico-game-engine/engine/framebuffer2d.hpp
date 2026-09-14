#pragma once

#include "draw.hpp"

class Layer2D;

class FrameBuffer2D
{
public:
    FrameBuffer2D(uint16_t width, uint16_t height);
    ~FrameBuffer2D();

    void blit(Draw *draw) const;
    void clear(uint16_t color);
    // Match object lifetime to the GC-owned pixel storage explicitly.
    void operator delete(void *pointer) noexcept;
    void *operator new(size_t size);
    void render(const Layer2D &layer);

private:
    void circle(int16_t x, int16_t y, uint16_t radius, uint16_t color, bool filled);
    static uint8_t color565To332(uint16_t color);
    void fillRectangle(int16_t x, int16_t y, uint16_t width, uint16_t height, uint16_t color);
    void image(int16_t x, int16_t y, uint16_t width, uint16_t height, const uint8_t *pixels);
    void imageOpaque(int16_t x, int16_t y, uint16_t width, uint16_t height, const uint8_t *pixels);
    void line(int16_t x1, int16_t y1, int16_t x2, int16_t y2, uint16_t color);
    void pixel(int16_t x, int16_t y, uint8_t color);
    void text(int16_t x, int16_t y, const char *value, uint16_t color, FontSize font);

    uint16_t height;
    uint8_t *pixels;
    uint16_t width;

    friend class Layer2D;
};
