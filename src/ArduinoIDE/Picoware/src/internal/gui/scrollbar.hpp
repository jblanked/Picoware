#pragma once
#include "../../internal/gui/draw.hpp"

namespace Picoware
{
    class ScrollBar
    {
    public:
        ScrollBar(Draw *draw, Vector position, Vector size, uint16_t outlineColor = TFT_BLACK, uint16_t fillColor = TFT_WHITE);
        ~ScrollBar();
        //
        void clear();
        void draw();
        //
        void setAll(Vector newPosition, Vector newSize, uint16_t newOutlineColor, uint16_t newFillColor, bool shouldDraw = false, bool shouldClear = false);
        void setPosition(Vector newPosition, bool shouldDraw = false, bool shouldClear = false);
        void setSize(Vector newSize, bool shouldDraw = false, bool shouldClear = false);
        void setOutlineColor(uint16_t newColor, bool shouldDraw = false, bool shouldClear = false);
        void setFillColor(uint16_t newColor, bool shouldDraw = false, bool shouldClear = false);
        //
        Vector getPosition() const { return position; }
        Vector getSize() const { return size; }
        uint16_t getOutlineColor() const { return outlineColor; }
        uint16_t getFillColor() const { return fillColor; }

    private:
        Draw *display;
        Vector position;
        Vector size;
        uint16_t outlineColor;
        uint16_t fillColor;
    };
}