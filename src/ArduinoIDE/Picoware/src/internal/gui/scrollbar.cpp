#include "../../internal/gui/scrollbar.hpp"

namespace Picoware
{
    ScrollBar::ScrollBar(Draw *draw, Vector position, Vector size, uint16_t outlineColor, uint16_t fillColor)
        : display(draw), position(position), size(size), outlineColor(outlineColor), fillColor(fillColor)
    {
        this->draw();
    }

    ScrollBar::~ScrollBar()
    {
        // Destructor
    }

    void ScrollBar::clear()
    {
        this->display->clear(position, size, fillColor);
    }

    void ScrollBar::draw()
    {
        this->display->drawRect(position, size, outlineColor);
        this->display->fillRect(Vector(position.x + 1, position.y + 1), Vector(size.x - 2, size.y - 2), fillColor);
    }

    void ScrollBar::setAll(Vector newPosition, Vector newSize, uint16_t newOutlineColor, uint16_t newFillColor, bool shouldDraw, bool shouldClear)
    {
        if (shouldClear)
        {
            this->clear();
        }
        this->position = newPosition;
        this->size = newSize;
        this->outlineColor = newOutlineColor;
        this->fillColor = newFillColor;
        if (shouldDraw)
        {
            this->draw();
        }
    }

    void ScrollBar::setPosition(Vector newPosition, bool shouldDraw, bool shouldClear)
    {
        if (shouldClear)
        {
            this->clear();
        }
        this->position = newPosition;
        if (shouldDraw)
        {
            this->draw();
        }
    }

    void ScrollBar::setSize(Vector newSize, bool shouldDraw, bool shouldClear)
    {
        if (shouldClear)
        {
            this->clear();
        }
        this->size = newSize;
        if (shouldDraw)
        {
            this->draw();
        }
    }

    void ScrollBar::setOutlineColor(uint16_t newColor, bool shouldDraw, bool shouldClear)
    {
        if (shouldClear)
        {
            this->clear();
        }
        this->outlineColor = newColor;
        if (shouldDraw)
        {
            this->draw();
        }
    }

    void ScrollBar::setFillColor(uint16_t newColor, bool shouldDraw, bool shouldClear)
    {
        if (shouldClear)
        {
            this->clear();
        }
        this->fillColor = newColor;
        if (shouldDraw)
        {
            this->draw();
        }
    }
}