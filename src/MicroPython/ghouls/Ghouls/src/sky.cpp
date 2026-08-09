#include "sky.hpp"

Sky::Sky() : gradient{}, time(0)
{
    memset(&gradient, 0, sizeof(gradient_color_t));
}

Sky::~Sky()
{
    // nothing to do...
}

void Sky::computeBands()
{
    const int drdy = ((gradient.horizR - gradient.layerR) * FIXED_POINT_SCALE) / SKY_HORIZON_HEIGHT;
    const int dgdy = ((gradient.horizG - gradient.layerG) * FIXED_POINT_SCALE) / SKY_HORIZON_HEIGHT;
    const int dbdy = ((gradient.horizB - gradient.layerB) * FIXED_POINT_SCALE) / SKY_HORIZON_HEIGHT;

    int r = gradient.layerR * FIXED_POINT_SCALE;
    int g = gradient.layerG * FIXED_POINT_SCALE;
    int b = gradient.layerB * FIXED_POINT_SCALE;

    bandCount = 0;
    for (int y = 0; y < SKY_HORIZON_HEIGHT; y += SKY_HORIZON_ROWS)
    {
        bandColors[bandCount++] = makeRGB565(r >> 8, g >> 8, b >> 8);

        r += drdy * SKY_HORIZON_ROWS;
        g += dgdy * SKY_HORIZON_ROWS;
        b += dbdy * SKY_HORIZON_ROWS;
    }
}

uint16_t Sky::makeRGB565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
}

void Sky::render(Draw *draw)
{
    if (bandCount == 0)
        computeBands();

    for (int y = 0, i = 0; i < bandCount; i++, y += SKY_HORIZON_ROWS)
    {
        int height = (y + SKY_HORIZON_ROWS < SKY_HORIZON_HEIGHT) ? SKY_HORIZON_ROWS : SKY_HORIZON_HEIGHT - y;
        draw->fillRectangle(0, y, ENGINE_LCD_WIDTH, height, bandColors[i]);
    }
}

void Sky::setSky(gradient_color_t skyGradient)
{
    this->gradient = skyGradient;
    computeBands();
}

void Sky::setSkyType(SkyType skyType)
{
    switch (skyType)
    {
    case SKY_SUNNY:
        this->gradient = {
            .horizR = 180,
            .horizG = 220,
            .horizB = 255,
            .layerR = 100,
            .layerG = 160,
            .layerB = 255,
        };
        break;
    case SKY_CLOUDY:
        this->gradient = {
            .horizR = 130,
            .horizG = 140,
            .horizB = 150,
            .layerR = 60,
            .layerG = 70,
            .layerB = 90,
        };
        break;
    case SKY_DARK:
        this->gradient = {
            .horizR = 40,
            .horizG = 50,
            .horizB = 120,
            .layerR = 10,
            .layerG = 15,
            .layerB = 50,
        };
        break;
    default:
        break;
    };
    computeBands();
}

void Sky::tick()
{
    time++;
}