#pragma once
#include "../gui/draw.hpp"

class Toggle
{
public:
    Toggle(Draw *draw, Vector position, Vector size, const char *text, bool initialState = false,
           uint16_t foregroundColor = TFT_BLACK, uint16_t backgroundColor = TFT_WHITE,
           uint16_t onColor = TFT_BLUE, uint16_t borderColor = TFT_BLACK, uint16_t borderWidth = 2);
    ~Toggle();
    void clear();
    void draw();
    bool getState() const { return state; }
    void setState(bool state);
    void toggle();

private:
    Draw *display;
    Vector position;
    Vector size;
    bool state;
    uint16_t foregroundColor;
    uint16_t backgroundColor;
    uint16_t onColor;
    uint16_t borderColor;
    uint16_t borderWidth;
    const char *text;
};
