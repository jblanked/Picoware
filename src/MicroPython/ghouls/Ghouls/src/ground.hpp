#pragma once
#include "pico-game-engine/engine/draw.hpp"
#include "general.hpp"

typedef enum
{
    GROUND_GRASS, // green grassy ground
    GROUND_DIRT,  // muddy/earthy ground
    GROUND_DARK   // stormy/night ground
} GroundType;

class Ground
{
public:
    Ground();
    ~Ground();

    void render(Draw *draw);                         // Render the ground using the provided Draw object
    void setGround(gradient_color_t groundGradient); // Change the ground's gradient colors
    void setGroundType(GroundType groundType);       // Change the ground type
    void tick();                                     // advance the ground's internal time

private:
    gradient_color_t gradient;
    uint32_t time;
    uint16_t bandColors[GROUND_MAX_BANDS]; // cached gradient band colors
    uint8_t bandCount = 0;                 // number of cached bands

    void computeBands(); // cache the gradient band colors
    uint16_t makeRGB565(uint8_t r, uint8_t g, uint8_t b);
};