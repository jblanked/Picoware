#pragma once
#include "../../internal/gui/draw.hpp"

namespace Picoware
{
    class Loading
    {
    public:
        Loading(Draw *draw, uint16_t spinnerColor = TFT_BLACK, uint16_t backgroundColor = TFT_WHITE);
        //
        void animate();
        void stop();
        //
        void setText(const char *text) { currentText = text; }
        //
        uint16_t getTimeElapsed() { return timeElapsed; }

    private:
        void clear();
        void drawSpinner();
        uint16_t fadeColor(uint16_t color, uint8_t opacity);
        //
        Draw *display;
        uint16_t spinnerColor;
        uint16_t spinnerPosition;
        uint16_t backgroundColor;
        uint16_t timeElapsed;
        uint16_t timeStart;
        bool animating = false;
        const char *currentText = "Loading...";
    };
}