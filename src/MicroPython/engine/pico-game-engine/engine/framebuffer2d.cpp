#include "framebuffer2d.hpp"

#include "layer2d.hpp"

#include "../../../font/font_mp.h"

#include <string.h>

namespace
{
constexpr uint8_t TRANSPARENT = 0xE3;

int16_t clamp(int16_t value, int16_t minimum, int16_t maximum)
{
    return value < minimum ? minimum : (value > maximum ? maximum : value);
}
}

FrameBuffer2D::FrameBuffer2D(uint16_t width, uint16_t height) : height(height), pixels(nullptr), width(width)
{
    pixels = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(static_cast<size_t>(width) * height));
    if (pixels != nullptr)
    {
        memset(pixels, 0, static_cast<size_t>(width) * height);
    }
}

FrameBuffer2D::~FrameBuffer2D()
{
    ENGINE_MEM_FREE(pixels);
}

void FrameBuffer2D::blit(Draw *draw) const
{
    if (draw == nullptr || pixels == nullptr)
    {
        return;
    }
    draw->image(0, 0, pixels, width, height);
}

void FrameBuffer2D::circle(int16_t x, int16_t y, uint16_t radius, uint16_t color, bool filled)
{
    if (radius == 0 || pixels == nullptr)
    {
        return;
    }

    int32_t current_x = 0;
    int32_t current_y = radius;
    int32_t decision = 3 - (2 * radius);
    const uint8_t color_index = color565To332(color);

    while (current_x <= current_y)
    {
        if (filled)
        {
            line(x - current_x, y - current_y, x + current_x, y - current_y, color);
            line(x - current_y, y - current_x, x + current_y, y - current_x, color);
            line(x - current_y, y + current_x, x + current_y, y + current_x, color);
            line(x - current_x, y + current_y, x + current_x, y + current_y, color);
        }
        else
        {
            pixel(x + current_x, y + current_y, color_index);
            pixel(x - current_x, y + current_y, color_index);
            pixel(x + current_x, y - current_y, color_index);
            pixel(x - current_x, y - current_y, color_index);
            pixel(x + current_y, y + current_x, color_index);
            pixel(x - current_y, y + current_x, color_index);
            pixel(x + current_y, y - current_x, color_index);
            pixel(x - current_y, y - current_x, color_index);
        }

        if (decision < 0)
        {
            decision += (4 * current_x) + 6;
        }
        else
        {
            decision += (4 * (current_x - current_y)) + 10;
            --current_y;
        }
        ++current_x;
    }
}

void FrameBuffer2D::clear(uint16_t color)
{
    if (pixels != nullptr)
    {
        memset(pixels, color565To332(color), static_cast<size_t>(width) * height);
    }
}

uint8_t FrameBuffer2D::color565To332(uint16_t color)
{
    uint8_t result = static_cast<uint8_t>(((color >> 8) & 0xE0) | ((color >> 6) & 0x1C) | ((color >> 3) & 0x03));
    return result == TRANSPARENT ? static_cast<uint8_t>(TRANSPARENT - 1) : result;
}

void FrameBuffer2D::fillRectangle(int16_t x, int16_t y, uint16_t rectangle_width, uint16_t rectangle_height, uint16_t color)
{
    if (pixels == nullptr || rectangle_width == 0 || rectangle_height == 0)
    {
        return;
    }

    int16_t left = clamp(x, 0, width);
    int16_t top = clamp(y, 0, height);
    int16_t right = clamp(static_cast<int32_t>(x) + rectangle_width, 0, width);
    int16_t bottom = clamp(static_cast<int32_t>(y) + rectangle_height, 0, height);
    if (left >= right || top >= bottom)
    {
        return;
    }

    const uint8_t color_index = color565To332(color);
    for (int16_t row = top; row < bottom; ++row)
    {
        memset(pixels + (row * width) + left, color_index, right - left);
    }
}

void FrameBuffer2D::image(int16_t x, int16_t y, uint16_t image_width, uint16_t image_height, const uint8_t *source)
{
    if (pixels == nullptr || source == nullptr)
    {
        return;
    }

    int16_t left = clamp(x, 0, width);
    int16_t top = clamp(y, 0, height);
    int16_t right = clamp(static_cast<int32_t>(x) + image_width, 0, width);
    int16_t bottom = clamp(static_cast<int32_t>(y) + image_height, 0, height);
    if (left >= right || top >= bottom)
    {
        return;
    }

    for (int16_t row = top; row < bottom; ++row)
    {
        const uint8_t *source_row = source + (static_cast<size_t>(row - y) * image_width) + (left - x);
        uint8_t *destination_row = pixels + (row * width) + left;
        for (int16_t column = left; column < right; ++column)
        {
            uint8_t value = *source_row++;
            if (value != TRANSPARENT)
            {
                *destination_row = value;
            }
            ++destination_row;
        }
    }
}

void FrameBuffer2D::imageOpaque(int16_t x, int16_t y, uint16_t image_width, uint16_t image_height, const uint8_t *source)
{
    if (pixels == nullptr || source == nullptr)
    {
        return;
    }

    int16_t left = clamp(x, 0, width);
    int16_t top = clamp(y, 0, height);
    int16_t right = clamp(static_cast<int32_t>(x) + image_width, 0, width);
    int16_t bottom = clamp(static_cast<int32_t>(y) + image_height, 0, height);
    if (left >= right || top >= bottom)
    {
        return;
    }

    for (int16_t row = top; row < bottom; ++row)
    {
        const uint8_t *source_row = source + (static_cast<size_t>(row - y) * image_width) + (left - x);
        uint8_t *destination_row = pixels + (row * width) + left;
        memcpy(destination_row, source_row, right - left);
    }
}

void FrameBuffer2D::line(int16_t x1, int16_t y1, int16_t x2, int16_t y2, uint16_t color)
{
    const uint8_t color_index = color565To332(color);
    int16_t delta_x = static_cast<int16_t>(x2 > x1 ? x2 - x1 : x1 - x2);
    int16_t step_x = x1 < x2 ? 1 : -1;
    int16_t delta_y = static_cast<int16_t>(-(y2 > y1 ? y2 - y1 : y1 - y2));
    int16_t step_y = y1 < y2 ? 1 : -1;
    int16_t error = delta_x + delta_y;

    while (true)
    {
        pixel(x1, y1, color_index);
        if (x1 == x2 && y1 == y2)
        {
            break;
        }
        int16_t double_error = static_cast<int16_t>(2 * error);
        if (double_error >= delta_y)
        {
            error += delta_y;
            x1 += step_x;
        }
        if (double_error <= delta_x)
        {
            error += delta_x;
            y1 += step_y;
        }
    }
}

void FrameBuffer2D::operator delete(void *pointer) noexcept
{
    ENGINE_MEM_FREE(pointer);
}

void *FrameBuffer2D::operator new(size_t size)
{
    return ENGINE_MEM_MALLOC(size);
}

void FrameBuffer2D::pixel(int16_t x, int16_t y, uint8_t color)
{
    if (pixels != nullptr && x >= 0 && y >= 0 && x < width && y < height)
    {
        pixels[(y * width) + x] = color;
    }
}

void FrameBuffer2D::render(const Layer2D &layer)
{
    layer.renderTo(*this);
}

void FrameBuffer2D::text(int16_t x, int16_t y, const char *value, uint16_t color, FontSize font)
{
    if (value == nullptr || pixels == nullptr)
    {
        return;
    }

    FontTable table = font_get_table(font);
    const uint8_t bytes_per_row = static_cast<uint8_t>((table.width + 7) / 8);
    const uint8_t color_index = color565To332(color);
    int16_t cursor_x = x;
    int16_t cursor_y = y;
    for (const char *character = value; *character != '\0'; ++character)
    {
        if (*character == '\n')
        {
            cursor_x = x;
            cursor_y += table.height;
            continue;
        }
        if (*character == ' ')
        {
            cursor_x += static_cast<int16_t>(table.width + 1);
            continue;
        }

        const uint8_t *glyph = font_get_character(font, *character);
        if (glyph != nullptr)
        {
            for (uint8_t row = 0; row < table.height; ++row)
            {
                for (uint8_t column = 0; column < table.width; ++column)
                {
                    if (glyph[row * bytes_per_row + (column / 8)] & (1 << (7 - (column % 8))))
                    {
                        pixel(cursor_x + column, cursor_y + row, color_index);
                    }
                }
            }
        }
        cursor_x += static_cast<int16_t>(table.width + 1);
        if (cursor_x + table.width >= width)
        {
            cursor_x = x;
            cursor_y += table.height;
        }
        if (cursor_y >= height)
        {
            break;
        }
    }
}
