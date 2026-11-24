#include "draw.hpp"
#include ENGINE_LCD_INCLUDE
#include <math.h>

Draw::Draw() : currentFontSize(ENGINE_FONT_DEFAULT), currentTextColor(0x0000)
#ifdef ENGINE_USE_PSRAM
               ,
               psramTextureRow(nullptr), psramTextureRowCapacity(0)
#endif
{
#ifdef ENGINE_LCD_INIT
    ENGINE_LCD_INIT();
#endif
}

Draw::~Draw()
{
#ifdef ENGINE_USE_PSRAM
    if (psramTextureRow)
        ENGINE_MEM_FREE(psramTextureRow);
#endif
#ifdef ENGINE_LCD_DEINIT
    ENGINE_LCD_DEINIT();
#endif
}

void Draw::circle(Vector position, uint16_t r, uint16_t color)
{
    ENGINE_LCD_CIRCLE(position.x, position.y, r, color);
}

void Draw::circle(uint16_t x, uint16_t y, uint16_t r, uint16_t color)
{
    ENGINE_LCD_CIRCLE(x, y, r, color);
}

void Draw::fillCircle(Vector position, uint16_t r, uint16_t color)
{
    ENGINE_LCD_FILL_CIRCLE(position.x, position.y, r, color);
}

void Draw::fillCircle(uint16_t x, uint16_t y, uint16_t r, uint16_t color)
{
    ENGINE_LCD_FILL_CIRCLE(x, y, r, color);
}

void Draw::fillPolygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    ENGINE_LCD_FILL_POLYGON(x, y, count, color);
}

void Draw::fillPolygonAlpha(uint16_t x[], uint16_t y[], int count, uint16_t color, uint8_t alpha)
{
#ifdef ENGINE_LCD_FILL_POLYGON_ALPHA
    ENGINE_LCD_FILL_POLYGON_ALPHA(x, y, count, color, alpha);
#else
    (void)alpha;
    ENGINE_LCD_FILL_POLYGON(x, y, count, color);
#endif
}

void Draw::fillRectangle(Vector position, Vector size, uint16_t color)
{
    ENGINE_LCD_FILL_RECTANGLE(position.x, position.y, size.x, size.y, color);
}

void Draw::fillRectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    ENGINE_LCD_FILL_RECTANGLE(x, y, width, height, color);
}

Vector Draw::getDisplaySize() const noexcept
{
    return Vector(ENGINE_LCD_WIDTH, ENGINE_LCD_HEIGHT);
}

void Draw::fillScreen(uint16_t color)
{
    ENGINE_LCD_CLEAR(color);
}

void Draw::fillTriangle(Vector p1, Vector p2, Vector p3, uint16_t color)
{
    ENGINE_LCD_FILL_TRIANGLE(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, color);
}

void Draw::fillTriangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color)
{
    ENGINE_LCD_FILL_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
}

void Draw::fillTriangleAlpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color, uint8_t alpha)
{
#ifdef ENGINE_LCD_FILL_TRIANGLE_ALPHA
    ENGINE_LCD_FILL_TRIANGLE_ALPHA(x1, y1, x2, y2, x3, y3, color, alpha);
#else
    (void)alpha;
    ENGINE_LCD_FILL_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
#endif
}

void Draw::fillTexturedTriangle(const Vector vertices[3], const float uv[6], const uint16_t *texture, uint16_t texture_width, uint16_t texture_height, uint16_t tint, uint32_t texture_psram_address)
{
#ifdef ENGINE_USE_PSRAM
    const bool texture_in_psram = !texture && texture_psram_address != 0xFFFFFFFFu;
#else
    const bool texture_in_psram = false;
    (void)texture_psram_address;
#endif
    if (!vertices || !uv || (!texture && !texture_in_psram) || texture_width == 0 || texture_height == 0)
        return;

#ifdef ENGINE_LCD_TEXTURED_TRIANGLE
    if (texture)
    {
        ENGINE_LCD_TEXTURED_TRIANGLE(
            vertices[0].x, vertices[0].y, uv[0], uv[1],
            vertices[1].x, vertices[1].y, uv[2], uv[3],
            vertices[2].x, vertices[2].y, uv[4], uv[5],
            texture, texture_width, texture_height, tint);
        return;
    }
#endif
    const float area = (vertices[1].x - vertices[0].x) * (vertices[2].y - vertices[0].y) -
                       (vertices[1].y - vertices[0].y) * (vertices[2].x - vertices[0].x);
    if (fabsf(area) < 0.000001f)
        return;

#ifdef ENGINE_USE_PSRAM
    if (texture_in_psram && texture_width > psramTextureRowCapacity)
    {
        uint16_t *replacement = static_cast<uint16_t *>(ENGINE_MEM_MALLOC(
            static_cast<size_t>(texture_width) * sizeof(uint16_t)));
        if (!replacement)
        {
            fillTriangle(vertices[0], vertices[1], vertices[2], tint);
            return;
        }
        if (psramTextureRow)
            ENGINE_MEM_FREE(psramTextureRow);
        psramTextureRow = replacement;
        psramTextureRowCapacity = texture_width;
    }
    uint16_t cached_texture_row = 0xFFFFu;
#endif

    const Vector screen = getDisplaySize();
    int min_x = static_cast<int>(floorf(fminf(vertices[0].x, fminf(vertices[1].x, vertices[2].x))));
    int max_x = static_cast<int>(ceilf(fmaxf(vertices[0].x, fmaxf(vertices[1].x, vertices[2].x))));
    int min_y = static_cast<int>(floorf(fminf(vertices[0].y, fminf(vertices[1].y, vertices[2].y))));
    int max_y = static_cast<int>(ceilf(fmaxf(vertices[0].y, fmaxf(vertices[1].y, vertices[2].y))));
    if (min_x < 0)
        min_x = 0;
    if (min_y < 0)
        min_y = 0;
    if (max_x >= static_cast<int>(screen.x))
        max_x = static_cast<int>(screen.x) - 1;
    if (max_y >= static_cast<int>(screen.y))
        max_y = static_cast<int>(screen.y) - 1;

    for (int y = min_y; y <= max_y; ++y)
    {
        for (int x = min_x; x <= max_x; ++x)
        {
            const float px = x + 0.5f;
            const float py = y + 0.5f;
            const float w0 = ((vertices[1].x - px) * (vertices[2].y - py) -
                              (vertices[1].y - py) * (vertices[2].x - px)) /
                             area;
            const float w1 = ((vertices[2].x - px) * (vertices[0].y - py) -
                              (vertices[2].y - py) * (vertices[0].x - px)) /
                             area;
            const float w2 = 1.0f - w0 - w1;
            if (w0 < 0.0f || w1 < 0.0f || w2 < 0.0f)
                continue;

            const float inverse_depth = w0 * vertices[0].z + w1 * vertices[1].z + w2 * vertices[2].z;
            if (inverse_depth <= 0.0f)
                continue;
            const float u = (w0 * uv[0] * vertices[0].z +
                             w1 * uv[2] * vertices[1].z +
                             w2 * uv[4] * vertices[2].z) /
                            inverse_depth;
            const float v = (w0 * uv[1] * vertices[0].z +
                             w1 * uv[3] * vertices[1].z +
                             w2 * uv[5] * vertices[2].z) /
                            inverse_depth;
            if (!isfinite(u) || !isfinite(v))
                continue;
            int texture_x = static_cast<int>(u * texture_width);
            int texture_y = static_cast<int>(v * texture_height);
            if (texture_x < 0)
                texture_x = 0;
            else if (texture_x >= texture_width)
                texture_x = texture_width - 1;
            if (texture_y < 0)
                texture_y = 0;
            else if (texture_y >= texture_height)
                texture_y = texture_height - 1;
            uint16_t sample;
            if (texture)
            {
                const size_t texture_index = static_cast<size_t>(texture_y) * texture_width + texture_x;
                sample = texture[texture_index];
            }
#ifdef ENGINE_USE_PSRAM
            else
            {
                if (cached_texture_row != texture_y)
                {
                    const uint32_t row_offset = static_cast<uint32_t>(texture_y) * texture_width * sizeof(uint16_t);
                    ENGINE_PSRAM_READ(texture_psram_address + row_offset, psramTextureRow,
                                      static_cast<size_t>(texture_width) * sizeof(uint16_t));
                    cached_texture_row = static_cast<uint16_t>(texture_y);
                }
                sample = psramTextureRow[texture_x];
            }
#else
            else
            {
                continue;
            }
#endif
            const uint16_t red = ((sample >> 11) & 0x1F) * ((tint >> 11) & 0x1F) / 0x1F;
            const uint16_t green = ((sample >> 5) & 0x3F) * ((tint >> 5) & 0x3F) / 0x3F;
            const uint16_t blue = (sample & 0x1F) * (tint & 0x1F) / 0x1F;
            pixel(static_cast<uint16_t>(x), static_cast<uint16_t>(y),
                  static_cast<uint16_t>((red << 11) | (green << 5) | blue));
        }
    }
}

void Draw::image(Vector position, const uint8_t *bitmap, Vector size)
{
    ENGINE_LCD_BLIT(position.x, position.y, size.x, size.y, bitmap);
}

void Draw::image(Vector position, const uint16_t *bitmap, Vector size)
{
    ENGINE_LCD_BLIT_16BIT(position.x, position.y, size.x, size.y, bitmap);
}

void Draw::image(uint16_t x, uint16_t y, const uint8_t *bitmap, uint16_t width, uint16_t height)
{
    ENGINE_LCD_BLIT(x, y, width, height, bitmap);
}

void Draw::image(uint16_t x, uint16_t y, const uint16_t *bitmap, uint16_t width, uint16_t height)
{
    ENGINE_LCD_BLIT_16BIT(x, y, width, height, bitmap);
}

void Draw::imageMasked(int16_t x, int16_t y, uint16_t dst_w, uint16_t dst_h,
                       uint16_t src_w, uint16_t src_h, const uint8_t *bitmap, const uint8_t *mask)
{
#ifdef ENGINE_LCD_BLIT_MASK
    ENGINE_LCD_BLIT_MASK(x, y, dst_w, dst_h, src_w, src_h, bitmap, mask);
#else
    (void)x;
    (void)y;
    (void)dst_w;
    (void)dst_h;
    (void)src_w;
    (void)src_h;
    (void)bitmap;
    (void)mask;
#endif
}

void Draw::line(Vector position, Vector size, uint16_t color)
{
    ENGINE_LCD_LINE(position.x, position.y, size.x, size.y, color);
}

void Draw::line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    ENGINE_LCD_LINE(x1, y1, x2, y2, color);
}

void Draw::pixel(Vector position, uint16_t color)
{
    ENGINE_LCD_PIXEL(position.x, position.y, color);
}

void Draw::pixel(uint16_t x, uint16_t y, uint16_t color)
{
    ENGINE_LCD_PIXEL(x, y, color);
}

void Draw::polygon(uint16_t x[], uint16_t y[], int count, uint16_t color)
{
    ENGINE_LCD_POLYGON(x, y, count, color);
}

void Draw::rectangle(Vector position, Vector size, uint16_t color)
{
    ENGINE_LCD_RECTANGLE(position.x, position.y, size.x, size.y, color);
}

void Draw::rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    ENGINE_LCD_RECTANGLE(x, y, width, height, color);
}

void Draw::setColor(uint16_t color)
{
    currentTextColor = color;
}

void Draw::setFont(ENGINE_FONT_SIZE size)
{
    currentFontSize = size;
}

void Draw::swap()
{
#ifdef ENGINE_LCD_SWAP
    ENGINE_LCD_SWAP();
#endif
}

void Draw::text(Vector position, const char *text)
{
    ENGINE_LCD_TEXT(position.x, position.y, text, currentTextColor, currentFontSize);
}

void Draw::text(uint16_t x, uint16_t y, const char *text)
{
    ENGINE_LCD_TEXT(x, y, text, currentTextColor, currentFontSize);
}

void Draw::text(Vector position, const char *text, uint16_t color, ENGINE_FONT_SIZE font)
{
    ENGINE_LCD_TEXT(position.x, position.y, text, color, font);
}

void Draw::text(uint16_t x, uint16_t y, const char *text, uint16_t color, ENGINE_FONT_SIZE font)
{
    ENGINE_LCD_TEXT(x, y, text, color, font);
}

void Draw::triangle(Vector p1, Vector p2, Vector p3, uint16_t color)
{
    ENGINE_LCD_TRIANGLE(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, color);
}

void Draw::triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color)
{
    ENGINE_LCD_TRIANGLE(x1, y1, x2, y2, x3, y3, color);
}
