#include "../../internal/gui/toggle.hpp"

namespace Picoware
{
    Toggle::Toggle(Draw *draw, Vector position, Vector size, const char *text, bool initialState,
                   uint16_t foregroundColor, uint16_t backgroundColor,
                   uint16_t onColor, uint16_t borderColor, uint16_t borderWidth)
        : display(draw), position(position), size(size), text(text),
          state(initialState), foregroundColor(foregroundColor), backgroundColor(backgroundColor),
          onColor(onColor), borderColor(borderColor), borderWidth(borderWidth)
    {
        this->clear();
    }

    Toggle::~Toggle()
    {
        // nothing to do
    }

    void Toggle::clear()
    {
        display->clear(position, size, backgroundColor);
        display->swap();
    }

    void Toggle::draw()
    {
        display->clear(position, size, backgroundColor);
        display->drawLine(Vector(position.x, position.y + size.y - borderWidth), Vector(position.x + size.x, position.y + size.y - borderWidth), borderColor);
        display->text(Vector(position.x + 5, position.y + size.y / 2 - 8), text, foregroundColor);

        int toggleWidth = 30;
        int toggleHeight = 16;
        int toggleX = position.x + size.x - toggleWidth - 5;
        int toggleY = position.y + (size.y - toggleHeight) / 2;
        int knobRadius = 6;

        if (state)
        {
            display->fillRect(Vector(toggleX, toggleY), Vector(toggleWidth, toggleHeight), onColor);
            display->fillCircle(Vector(toggleX + toggleWidth - knobRadius - 2, toggleY + toggleHeight / 2), knobRadius, backgroundColor);
        }
        else
        {
            display->fillRect(Vector(toggleX, toggleY), Vector(toggleWidth, toggleHeight), borderColor);
            display->fillCircle(Vector(toggleX + knobRadius + 2, toggleY + toggleHeight / 2), knobRadius, backgroundColor);
        }

        this->display->swap();
    }

    void Toggle::setState(bool newState)
    {
        state = newState;
        draw();
    }

    void Toggle::toggle()
    {
        setState(!state);
    }
}