#include "../gui/draw.hpp"
#include "../system/drivers/lcd.h"
#include "../system/drivers/font.h"
#include <string.h>
#include "hardware/dma.h"

// Static buffer definitions
uint8_t Draw::frontBuffer[320 * 320];
uint8_t Draw::backBuffer[320 * 320];
uint16_t Draw::paletteBuffer[256];
static int dma_channel = -1;
static bool dma_initialized = false;

Draw::Draw(uint16_t foregroundColor, uint16_t backgroundColor) : bufferSwapped(false), cursor(0, 0), font(1), size(320, 320), textBackground(backgroundColor), textForeground(foregroundColor), useBackgroundTextColor(false)
{
    lcd_init();
    lcd_set_background(backgroundColor);
    lcd_set_underscore(false);
    lcd_enable_cursor(false);

    // Initialize DMA for SPI transfers
    if (!dma_initialized)
    {
        dma_channel = dma_claim_unused_channel(true);
        dma_initialized = true;
    }

    // init palette
    for (int i = 0; i < 256; i++)
    {
        // Extract RGB332 components
        uint8_t r3 = (i >> 5) & 0x07; // 3 bits for red
        uint8_t g3 = (i >> 2) & 0x07; // 3 bits for green
        uint8_t b2 = i & 0x03;        // 2 bits for blue

        // Convert to 8-bit RGB
        uint8_t r8 = (r3 * 255) / 7; // Scale 3-bit to 8-bit
        uint8_t g8 = (g3 * 255) / 7; // Scale 3-bit to 8-bit
        uint8_t b8 = (b2 * 255) / 3; // Scale 2-bit to 8-bit

        // Convert to RGB565 for the palette
        paletteBuffer[i] = color565(r8, g8, b8);
    }

    // Clear both buffers
    int bufferSize = size.x * size.y;
    memset(frontBuffer, 0, bufferSize);
    memset(backBuffer, 0, bufferSize);
}

Draw::~Draw()
{
    // Clean up DMA resources
    if (dma_initialized && dma_channel >= 0)
    {
        dma_channel_unclaim(dma_channel);
        dma_initialized = false;
        dma_channel = -1;
    }
}

void Draw::background(uint16_t color)
{
    lcd_set_background(color);
}

void Draw::clear(Vector position, Vector size, uint16_t color)
{
    // Calculate the clipping boundaries
    int x = position.x;
    int y = position.y;
    int width = size.x;
    int height = size.y;

    // Adjust for left and top boundaries
    if (x < 0)
    {
        width += x; // Reduce width by the negative offset
        x = 0;
    }
    if (y < 0)
    {
        height += y; // Reduce height by the negative offset
        y = 0;
    }

    // Adjust for right and bottom boundaries
    if (x + width > this->size.x)
    {
        width = this->size.x - x;
    }
    if (y + height > this->size.y)
    {
        height = this->size.y - y;
    }

    // Ensure width and height are positive before drawing
    if (width > 0 && height > 0)
    {
        this->fillRect(Vector(x, y), Vector(width, height), color);
    }
}

void Draw::clearBuffer(uint8_t colorIndex)
{
    int bufferSize = size.x * size.y;
    memset(backBuffer, colorIndex, bufferSize);
}

void Draw::clearBothBuffers(uint8_t colorIndex)
{
    int bufferSize = size.x * size.y;
    memset(backBuffer, colorIndex, bufferSize);
    memset(frontBuffer, colorIndex, bufferSize);
}

void Draw::color(uint16_t color)
{
    lcd_set_foreground(color);
    this->textForeground = color;
}

uint8_t Draw::color332(uint16_t color)
{
    return ((color & 0xE000) >> 8) | ((color & 0x0700) >> 6) | ((color & 0x0018) >> 3);
}

uint16_t Draw::color565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

void Draw::drawCircle(Vector position, int16_t r, uint16_t color)
{
    if (r <= 0)
        return;

    int16_t x = 0;
    int16_t y = r;
    int16_t d = 3 - 2 * r;

    while (x <= y)
    {
        // Draw 8 symmetric points
        this->drawPixel(Vector(position.x + x, position.y + y), color);
        this->drawPixel(Vector(position.x - x, position.y + y), color);
        this->drawPixel(Vector(position.x + x, position.y - y), color);
        this->drawPixel(Vector(position.x - x, position.y - y), color);
        this->drawPixel(Vector(position.x + y, position.y + x), color);
        this->drawPixel(Vector(position.x - y, position.y + x), color);
        this->drawPixel(Vector(position.x + y, position.y - x), color);
        this->drawPixel(Vector(position.x - y, position.y - x), color);

        if (d < 0)
        {
            d += 4 * x + 6;
        }
        else
        {
            d += 4 * (x - y) + 10;
            y--;
        }
        x++;
    }
}

void Draw::drawLine(Vector position, Vector size, uint16_t color)
{
    int x = (int)position.x;
    int y = (int)position.y;
    int length = (int)size.x;

    // Draw a horizontal line from x to x + length at y coordinate
    for (int i = 0; i < length; i++)
    {
        int currentX = x + i;
        if (currentX >= 0 && currentX < this->size.x && y >= 0 && y < this->size.y)
        {
            this->drawPixel(Vector(currentX, y), color);
        }
    }
}

void Draw::drawLineCustom(Vector point1, Vector point2, uint16_t color)
{
    int x1 = (int)point1.x;
    int y1 = (int)point1.y;
    int x2 = (int)point2.x;
    int y2 = (int)point2.y;

    // Bresenham's line algorithm
    int dx = abs(x2 - x1);
    int dy = abs(y2 - y1);
    int sx = (x1 < x2) ? 1 : -1;
    int sy = (y1 < y2) ? 1 : -1;
    int err = dx - dy;

    while (true)
    {
        // Draw pixel if within bounds
        if (x1 >= 0 && x1 < this->size.x && y1 >= 0 && y1 < this->size.y)
        {
            this->drawPixel(Vector(x1, y1), color);
        }

        // Check if we've reached the end point
        if (x1 == x2 && y1 == y2)
            break;

        int e2 = 2 * err;
        if (e2 > -dy)
        {
            err -= dy;
            x1 += sx;
        }
        if (e2 < dx)
        {
            err += dx;
            y1 += sy;
        }
    }
}

void Draw::drawPixel(Vector position, uint16_t color)
{
    uint8_t colorIndex = color332(color);
    int bufferIndex = (int)(position.y * size.x + position.x);
    backBuffer[bufferIndex] = colorIndex;
}

void Draw::drawRect(Vector position, Vector size, uint16_t color)
{
    if (size.x <= 0 || size.y <= 0)
        return;

    // Top edge (horizontal line)
    this->drawLine(position, Vector(size.x, 0), color);

    // Bottom edge (horizontal line)
    this->drawLine(Vector(position.x, position.y + size.y - 1), Vector(size.x, 0), color);

    // Left edge (vertical line using individual pixels)
    for (int y = 0; y < size.y; y++)
    {
        Vector pixelPos = Vector(position.x, position.y + y);
        if (pixelPos.x >= 0 && pixelPos.x < this->size.x && pixelPos.y >= 0 && pixelPos.y < this->size.y)
        {
            this->drawPixel(pixelPos, color);
        }
    }

    // Right edge (vertical line using individual pixels)
    for (int y = 0; y < size.y; y++)
    {
        Vector pixelPos = Vector(position.x + size.x - 1, position.y + y);
        if (pixelPos.x >= 0 && pixelPos.x < this->size.x && pixelPos.y >= 0 && pixelPos.y < this->size.y)
        {
            this->drawPixel(pixelPos, color);
        }
    }
}

void Draw::fillCircle(Vector position, int16_t r, uint16_t color)
{
    if (r <= 0)
        return;

    int16_t x = 0;
    int16_t y = r;
    int16_t d = 1 - r;

    while (x <= y)
    {
        // Draw horizontal lines to fill the circle
        // Draw lines for the main circle quadrants
        this->drawLine(Vector(position.x - y, position.y + x), Vector(2 * y, 0), color);
        this->drawLine(Vector(position.x - y, position.y - x), Vector(2 * y, 0), color);

        if (x != y)
        {
            this->drawLine(Vector(position.x - x, position.y + y), Vector(2 * x, 0), color);
            this->drawLine(Vector(position.x - x, position.y - y), Vector(2 * x, 0), color);
        }

        if (d < 0)
        {
            d += 2 * x + 3;
        }
        else
        {
            d += 2 * (x - y) + 5;
            y--;
        }
        x++;
    }
}

void Draw::fillRect(Vector position, Vector size, uint16_t color)
{
    if (size.x <= 0 || size.y <= 0)
        return;

    // Clip to screen bounds
    int x = (int)position.x;
    int y = (int)position.y;
    int width = (int)size.x;
    int height = (int)size.y;

    // Adjust for left and top boundaries
    if (x < 0)
    {
        width += x;
        x = 0;
    }
    if (y < 0)
    {
        height += y;
        y = 0;
    }

    // Adjust for right and bottom boundaries
    if (x + width > this->size.x)
    {
        width = this->size.x - x;
    }
    if (y + height > this->size.y)
    {
        height = this->size.y - y;
    }

    // Only draw if there's something to draw
    if (width > 0 && height > 0)
    {
        for (int py = y; py < y + height; py++)
        {
            for (int px = x; px < x + width; px++)
            {
                this->drawPixel(Vector(px, py), color);
            }
        }
    }
}

void Draw::fillScreen(uint16_t color)
{
    this->fillRect(Vector(0, 0), Vector(this->size.x, this->size.y), color);
}

Vector Draw::getCursor()
{
    return this->cursor;
}

Vector Draw::getFontSize()
{
    if (this->font <= 1)
    {
        return Vector(8, 10); // 8x10 font
    }
    else
    {
        return Vector(5, 10); // 5x10 font
    }
}

uint16_t Draw::getPaletteColor(uint8_t index)
{
    if (paletteBuffer)
    {
        return paletteBuffer[index];
    }
    return 0;
}

void Draw::image(Vector position, const uint8_t *bitmap, Vector size, const uint16_t *palette, bool imageCheck, bool invert)
{
    if (!imageCheck || (imageCheck &&
                        bitmap != nullptr &&
                        position.x >= 0 &&
                        position.y >= 0 &&
                        position.x + size.x <= this->size.x &&
                        position.y + size.y <= this->size.y &&
                        size.x > 0 &&
                        size.y > 0))
    {
        uint8_t pixel;
        uint16_t color;
        for (int y = 0; y < size.y; y++)
        {
            for (int x = 0; x < size.x; x++)
            {
                pixel = bitmap[static_cast<int>(y * size.x + x)];
                color = palette != nullptr ? palette[pixel] : paletteBuffer[pixel];
                if (invert)
                {
                    if (color == TFT_WHITE)
                    {
                        color = TFT_BLACK;
                    }
                    else if (color == TFT_BLACK)
                    {
                        color = TFT_WHITE;
                    }
                }
                this->drawPixel(Vector(position.x + x, position.y + y), color);
            }
        }
    }
}

void Draw::image(Vector position, Image *image, bool imageCheck)
{
    const uint8_t *data = image->getData();
    Vector size = image->getSize();
    if (!imageCheck || (imageCheck && data != nullptr &&
                        position.x < this->size.x &&
                        position.y < this->size.y &&
                        size.x > 0 &&
                        size.y > 0))
    {
        this->image(position, data, size, nullptr, false);
    }
}

void Draw::imageBitmap(Vector position, const uint8_t *bitmap, Vector size, uint16_t color, bool invert)
{
    if (bitmap != nullptr && position.x < this->size.x && position.y < this->size.y && size.x > 0 && size.y > 0)
    {
        // 1-bit packed bitmaps
        int16_t byteWidth = (size.x + 7) / 8;
        uint8_t byte = 0;

        for (int y = 0; y < size.y; y++)
        {
            for (int x = 0; x < size.x; x++)
            {
                // Get the bit for this pixel
                if (x & 7)
                {
                    byte <<= 1;
                }
                else
                {
                    byte = bitmap[y * byteWidth + x / 8];
                }

                bool pixelSet = (byte & 0x80) != 0;
                bool shouldDraw;

                if (invert)
                {
                    shouldDraw = !pixelSet;
                }
                else
                {
                    shouldDraw = pixelSet;
                }

                if (shouldDraw)
                {
                    this->drawPixel(Vector(position.x + x, position.y + y), color);
                }
            }
        }
    }
}

void Draw::imageColor(Vector position, const uint8_t *bitmap, Vector size, uint16_t color, bool invert, uint8_t transparentColor)
{
    if (bitmap != nullptr && position.x < this->size.x && position.y < this->size.y && size.x > 0 && size.y > 0)
    {
        uint8_t pixel;
        bool shouldDraw;
        for (int y = 0; y < size.y; y++)
        {
            for (int x = 0; x < size.x; x++)
            {
                pixel = bitmap[static_cast<int>(y * size.x + x)];

                if (invert)
                {
                    shouldDraw = (pixel == transparentColor);
                }
                else
                {
                    shouldDraw = (pixel != transparentColor);
                }

                if (shouldDraw)
                {
                    this->drawPixel(Vector(position.x + x, position.y + y), color);
                }
            }
        }
    }
}

void Draw::renderChar(Vector position, char c, uint16_t color)
{
    const font_t *currentFont = (this->font <= 1) ? &font_8x10 : &font_5x10;
    Vector fontSize = this->getFontSize();

    // Get the glyph data for this character
    int charIndex = (unsigned char)c;
    const uint8_t *glyph = &currentFont->glyphs[charIndex * GLYPH_HEIGHT];

    // Render each row of the character
    for (int row = 0; row < GLYPH_HEIGHT; row++)
    {
        uint8_t glyphRow = glyph[row];

        if (currentFont->width == 8)
        {
            // 8-pixel wide font (8x10)
            for (int col = 0; col < 8; col++)
            {
                uint8_t bitMask = 0x80 >> col; // Start from leftmost bit

                if ((glyphRow & bitMask) != 0)
                {
                    this->drawPixel(Vector(position.x + col, position.y + row), color);
                }
                else if (useBackgroundTextColor)
                {
                    this->drawPixel(Vector(position.x + col, position.y + row), textBackground);
                }
            }
        }
        else
        {
            // 5-pixel wide font (5x10)
            uint8_t bitMasks[5] = {0x10, 0x08, 0x04, 0x02, 0x01};
            for (int col = 0; col < 5; col++)
            {

                if ((glyphRow & bitMasks[col]) != 0)
                {
                    this->drawPixel(Vector(position.x + col, position.y + row), color);
                }
                else if (useBackgroundTextColor)
                {
                    this->drawPixel(Vector(position.x + col, position.y + row), textBackground);
                }
            }
        }
    }
}

void Draw::setCursor(Vector position)
{
    this->cursor = position;
}

void Draw::setFont(int font)
{
    if (font <= 1)
    {
        lcd_set_font(&font_8x10);
        this->font = 1; // 8x10 font
    }
    else
    {
        lcd_set_font(&font_5x10);
        this->font = 2; // 5x10 font
    }
}

void Draw::setPaletteColor(uint8_t index, uint16_t color)
{
    if (paletteBuffer)
    {
        paletteBuffer[index] = color;
    }
}

void Draw::swap(bool copyFrameBuffer, bool copyPalette)
{
    int bufferSize = size.x * size.y;

    if (copyFrameBuffer)
    {
        // Copy back buffer to front buffer
        memcpy(frontBuffer, backBuffer, bufferSize);
    }
    else
    {
        // Fast buffer swap using 32-bit operations
        uint32_t *src32 = (uint32_t *)backBuffer;
        uint32_t *dst32 = (uint32_t *)frontBuffer;
        int words = bufferSize / 4;

        for (int i = 0; i < words; i++)
        {
            uint32_t temp = dst32[i];
            dst32[i] = src32[i];
            src32[i] = temp;
        }

        // Handle remaining bytes
        int remaining = bufferSize % 4;
        if (remaining > 0)
        {
            int start = words * 4;
            for (int i = 0; i < remaining; i++)
            {
                uint8_t temp = frontBuffer[start + i];
                frontBuffer[start + i] = backBuffer[start + i];
                backBuffer[start + i] = temp;
            }
        }

        bufferSwapped = !bufferSwapped;
    }

    swapOptimized();

    // Clear back buffer for next frame to prevent artifacts
    clearBuffer(0);

    if (copyPalette)
    {
        // nothing to do yet..
    }
}

void Draw::swapOptimized()
{
    const int lineSize = size.x;

    uint16_t lineBuffer[lineSize];

    for (int y = 0; y < size.y; y++)
    {
        // Convert one line from 8-bit to 16-bit
        for (int x = 0; x < lineSize; x++)
        {
            int bufferIndex = y * lineSize + x;
            lineBuffer[x] = paletteBuffer[frontBuffer[bufferIndex]];
        }
        // Send to LCD - each line is sent immediately
        lcd_blit(lineBuffer, 0, y, lineSize, 1);
    }
}

void Draw::swapRegion(Vector position, Vector size)
{
    // Fast region-only swap for UI updates
    const int lineSize = this->size.x;
    uint16_t lineBuffer[lineSize];

    // Clamp region to screen bounds
    int startY = (position.y < 0) ? 0 : position.y;
    int endY = (position.y + size.y > this->size.y) ? this->size.y : (position.y + size.y);
    int startX = (position.x < 0) ? 0 : position.x;
    int endX = (position.x + size.x > this->size.x) ? this->size.x : (position.x + size.x);

    // Swap buffers in the region first
    for (int y = startY; y < endY; y++)
    {
        for (int x = startX; x < endX; x++)
        {
            int bufferIndex = y * lineSize + x;
            uint8_t temp = frontBuffer[bufferIndex];
            frontBuffer[bufferIndex] = backBuffer[bufferIndex];
            backBuffer[bufferIndex] = temp;
        }
    }

    // Update only the affected lines on the display
    for (int y = startY; y < endY; y++)
    {
        // Convert entire line
        for (int x = 0; x < lineSize; x++)
        {
            int bufferIndex = y * lineSize + x;
            lineBuffer[x] = paletteBuffer[frontBuffer[bufferIndex]];
        }
        // Send to LCD
        lcd_blit(lineBuffer, 0, y, lineSize, 1);
    }
}

void Draw::text(Vector position, const char text)
{
    this->setCursor(position);

    if (text == '\n')
    {
        Vector fontSize = this->getFontSize();
        this->setCursor(Vector(0, this->cursor.y + fontSize.y));
        return;
    }

    this->renderChar(this->cursor, text, textForeground);

    // Calculate next cursor position with word wrapping
    Vector fontSize = this->getFontSize();
    Vector nextPosition = Vector(this->cursor.x + fontSize.x, this->cursor.y);

    // Check if we need to wrap to next line
    if (nextPosition.x + fontSize.x > this->size.x)
    {
        // Wrap to next line
        nextPosition = Vector(0, this->cursor.y + fontSize.y);
    }

    this->setCursor(nextPosition);
}

void Draw::text(Vector position, const char text, uint16_t color)
{
    this->setCursor(position);

    if (text == '\n')
    {
        Vector fontSize = this->getFontSize();
        this->setCursor(Vector(0, this->cursor.y + fontSize.y));
        return;
    }

    this->renderChar(this->cursor, text, color);

    // Calculate next cursor position with word wrapping
    Vector fontSize = this->getFontSize();
    Vector nextPosition = Vector(this->cursor.x + fontSize.x, this->cursor.y);

    // Check if we need to wrap to next line
    if (nextPosition.x + fontSize.x > this->size.x)
    {
        // Wrap to next line
        nextPosition = Vector(0, this->cursor.y + fontSize.y);
    }

    this->setCursor(nextPosition);
}

void Draw::text(Vector position, const char *text)
{
    this->setCursor(position);
    uint16_t len = strlen(text);
    uint16_t n = 0;
    while (n < len)
    {
        this->text(cursor, text[n]);
        n++;
    }
}

void Draw::text(Vector position, const char *text, uint16_t color, int font)
{
    this->setCursor(position);
    this->setFont(font);
    this->color(color);
    uint16_t len = strlen(text);
    uint16_t n = 0;
    while (n < len)
    {
        this->text(cursor, text[n]);
        n++;
    }
}
