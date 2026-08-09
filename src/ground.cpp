#include "ground.hpp"

Ground::Ground() : gradient{}, time(0)
{
    memset(&gradient, 0, sizeof(gradient_color_t));
}

Ground::~Ground()
{
    // nothing to do...
}

void Ground::computeBands()
{
    const uint16_t groundHeight = (uint16_t)ENGINE_LCD_HEIGHT - GROUND_HORIZON_HEIGHT;

    const int drdy = ((gradient.layerR - gradient.horizR) * FIXED_POINT_SCALE) / groundHeight;
    const int dgdy = ((gradient.layerG - gradient.horizG) * FIXED_POINT_SCALE) / groundHeight;
    const int dbdy = ((gradient.layerB - gradient.horizB) * FIXED_POINT_SCALE) / groundHeight;

    int r = gradient.horizR * FIXED_POINT_SCALE;
    int g = gradient.horizG * FIXED_POINT_SCALE;
    int b = gradient.horizB * FIXED_POINT_SCALE;

    bandCount = 0;
    for (int y = 0; y < groundHeight; y += GROUND_ROWS)
    {
        bandColors[bandCount++] = makeRGB565(r >> 8, g >> 8, b >> 8);

        r += drdy * GROUND_ROWS;
        g += dgdy * GROUND_ROWS;
        b += dbdy * GROUND_ROWS;
    }
}

uint16_t Ground::makeRGB565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
}

void Ground::render(Draw *draw)
{
    if (bandCount == 0)
        computeBands();

    const uint16_t groundHeight = (uint16_t)ENGINE_LCD_HEIGHT - GROUND_HORIZON_HEIGHT;
    for (int y = 0, i = 0; i < bandCount; i++, y += GROUND_ROWS)
    {
        int height = (y + GROUND_ROWS < groundHeight) ? GROUND_ROWS : groundHeight - y;
        draw->fillRectangle(0, GROUND_HORIZON_HEIGHT + y, ENGINE_LCD_WIDTH, height, bandColors[i]);
    }
}

void Ground::setGround(gradient_color_t groundGradient)
{
    this->gradient = groundGradient;
    computeBands();
}

void Ground::setGroundType(GroundType groundType)
{
    switch (groundType)
    {
    case GROUND_GRASS:
        this->gradient = {
            .horizR = 80,
            .horizG = 110,
            .horizB = 50,
            .layerR = 30,
            .layerG = 55,
            .layerB = 15,
        };
        break;
    case GROUND_DIRT:
        this->gradient = {
            .horizR = 200,
            .horizG = 140,
            .horizB = 70,
            .layerR = 140,
            .layerG = 90,
            .layerB = 40,
        };
        break;
    case GROUND_DARK:
        this->gradient = {
            .horizR = 60,
            .horizG = 45,
            .horizB = 25,
            .layerR = 22,
            .layerG = 16,
            .layerB = 8,
        };
        break;
    default:
        break;
    };
    computeBands();
}

void Ground::tick()
{
    time++;
}