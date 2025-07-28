#pragma once
#include "draw.hpp"

namespace Picoware
{
    class Desktop
    {
    public:
        Desktop(Draw *draw, uint16_t textColor = TFT_BLACK, uint16_t backgroundColor = TFT_WHITE);
        ~Desktop();
        //
        void clear();
        void draw(const uint8_t *animationFrame, Vector animationSize, const uint16_t *palette = nullptr);
        //
        uint16_t getBackgroundColor() const { return backgroundColor; }
        uint16_t getTextColor() const { return textColor; }
        //
        void setBackgroundColor(uint16_t color) { backgroundColor = color; }
        void setTextColor(uint16_t color) { textColor = color; }
        void setTime(const char *time) { rtcTime = time; }

    private:
        void drawHeader();
        Draw *display;
        uint16_t textColor;
        uint16_t backgroundColor;
        bool darkMode;
        bool hasBattery;
        bool hasBluetooth;
        bool hasWiFi;
        const char *boardName;
        const char *rtcTime;
    };
}