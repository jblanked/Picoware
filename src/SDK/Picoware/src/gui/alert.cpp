#pragma once
#include "../gui/alert.hpp"
#include <string.h>

Alert::Alert(Draw *draw, const char *text, uint16_t textColor, uint16_t backgroundColor)
    : display(draw), text(text),
      textColor(textColor), backgroundColor(backgroundColor)
{
    // nothing to do
}
Alert::~Alert()
{
    // nothing to do
}

void Alert::clear()
{
    display->clear(Vector(0, 0), display->getSize(), backgroundColor);
    display->swap();
}

void Alert::draw(const char *title)
{
    auto size = display->getSize();

    // Draw Title
    display->text(Vector(size.x / 2 - 15, 0), title, textColor);

    // Draw Border
    display->drawRect(Vector(20, 20), Vector(size.x - 40, size.y - 40), textColor);

    // Draw Text (within the border - non-centered)
    int line = 0;
    const char *p = text;
    while (*p)
    {
        // find the next line break or end of string
        const char *nextLine = strchr(p, '\n');
        if (nextLine == nullptr)
        {
            // no more newlines, draw the rest of the text
            display->text(Vector(30, 30 + line * 18), p, textColor);
            break;
        }

        // create temporary buffer without the newline
        char lineBuffer[256];
        size_t lineLength = nextLine - p;
        strncpy(lineBuffer, p, lineLength);
        lineBuffer[lineLength] = '\0';

        // draw the line
        display->text(Vector(30, 30 + line * 18), lineBuffer, textColor);

        // move to the next line
        p = nextLine + 1;
        line++;
    }

    display->swap();
}
