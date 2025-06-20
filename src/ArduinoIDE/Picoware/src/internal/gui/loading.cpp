#include "../../internal/gui/loading.hpp"

namespace Picoware
{
    Loading::Loading(Draw *draw, uint16_t spinnerColor, uint16_t backgroundColor)
        : display(draw), spinnerColor(spinnerColor), backgroundColor(backgroundColor)
    {
        spinnerPosition = 0;
        timeElapsed = 0;
        timeStart = 0;
        animating = false;
    }
    void Loading::animate()
    {
        if (!animating)
        {
            animating = true;
            timeStart = millis();
        }
        clear();
        drawSpinner();
        display->text(Vector(130, 20), currentText, spinnerColor);
        timeElapsed = millis() - timeStart;
        spinnerPosition = (spinnerPosition + 10) % 360; // Rotate by 10 degrees each frame
        display->swap();
    }

    void Loading::clear()
    {
        auto board = display->getBoard();
        display->clear(
            Vector(0, 0),
            Vector(board.width, board.height),
            backgroundColor);
    }

    void Loading::stop()
    {
        clear();
        display->swap();
        animating = false;
        timeElapsed = 0;
        timeStart = 0;
    }

    void Loading::drawSpinner()
    {
        // Get the screen dimensions for positioning
        auto board = display->getBoard();
        int centerX = board.width / 2;
        int centerY = board.height / 2;
        int radius = 20; // spinner radius
        int span = 280;  // degrees of arc
        int step = 5;    // degrees between segments

        int startAngle = spinnerPosition;
        // draw only along the circle edge as short line‐segments
        for (int offset = 0; offset < span; offset += step)
        {
            int angle = (startAngle + offset) % 360;
            int nextAngle = (angle + step) % 360;
            float rad = PI / 180.0f;

            // compute two successive points on the circumference
            int x1 = centerX + int(radius * cos(angle * rad));
            int y1 = centerY + int(radius * sin(angle * rad));
            int x2 = centerX + int(radius * cos(nextAngle * rad));
            int y2 = centerY + int(radius * sin(nextAngle * rad));

            // fade out trailing segments
            uint8_t opacity = 255 - ((offset * 200) / span);
            uint16_t color = fadeColor(spinnerColor, opacity);

            // draw just the edge segment
            display->drawLine(Vector(x1, y1), Vector(x2, y2), color);
        }

        // draw time elapsed in milliseconds
        display->text(Vector(5, board.height - 20), "Time Elapsed:");
        char timeStr[16];
        int seconds = timeElapsed / 10000;
        if (seconds < 60)
        {
            if (seconds <= 1)
            {
                snprintf(timeStr, sizeof(timeStr), "%u second", seconds);
            }
            else
            {
                snprintf(timeStr, sizeof(timeStr), "%u seconds", seconds);
            }
        }
        else
        {
            snprintf(timeStr, sizeof(timeStr), "%u minutes", seconds / 60);
        }
        display->text(Vector(230, board.height - 20), timeStr, spinnerColor);
    }

    // Helper function to adjust color opacity
    uint16_t Loading::fadeColor(uint16_t color, uint8_t opacity)
    {
        if (opacity >= 255)
            return color;

        // Extract RGB components
        uint8_t r = (color >> 11) & 0x1F;
        uint8_t g = (color >> 5) & 0x3F;
        uint8_t b = color & 0x1F;

        // Apply opacity
        r = (r * opacity) / 255;
        g = (g * opacity) / 255;
        b = (b * opacity) / 255;

        // Recombine
        return (r << 11) | (g << 5) | b;
    }
}