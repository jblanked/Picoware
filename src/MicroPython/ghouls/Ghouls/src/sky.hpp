#pragma once
#include "pico-game-engine/engine/draw.hpp"
#include "general.hpp"

typedef enum
{
    SKY_SUNNY,  // clear/bright sky
    SKY_CLOUDY, // overcast sky
    SKY_DARK    // stormy/night sky
} SkyType;

class Sky
{
public:
    Sky();
    ~Sky();

    void render(Draw *draw);                   // Render the sky using the provided Draw object
    void setSky(gradient_color_t skyGradient); // Change the sky's gradient colors
    void setSkyType(SkyType skyType);          // Change the sky type
    void tick();                               // advance the sky's internal time

private:
    gradient_color_t gradient;
    uint32_t time;
    uint16_t bandColors[SKY_MAX_BANDS]; // cached gradient band colors
    uint8_t bandCount = 0;              // number of cached bands

    void computeBands(); // cache the gradient band colors
    uint16_t makeRGB565(uint8_t r, uint8_t g, uint8_t b);
};