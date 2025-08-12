#pragma once
#include "../gui/draw.hpp"

class Alert
{
public:
    Alert(Draw *draw, const char *text, uint16_t textColor = TFT_BLACK, uint16_t backgroundColor = TFT_WHITE);
    ~Alert();
    void clear();
    void draw(const char *title = "Alert");
    uint16_t getTextColor() const noexcept { return textColor; }
    uint16_t getBackgroundColor() const noexcept { return backgroundColor; }
    void setText(const char *text) { this->text = text; }

private:
    Draw *display;
    uint16_t textColor;
    uint16_t backgroundColor;
    const char *text;
};
