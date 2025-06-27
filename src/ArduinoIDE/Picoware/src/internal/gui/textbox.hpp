#pragma once
#include "../../internal/gui/draw.hpp"
#include "../../internal/gui/scrollbar.hpp"

namespace Picoware
{
    class TextBox
    {
    public:
        TextBox(
            Draw *draw,
            uint16_t y,
            uint16_t height,
            uint16_t foregroundColor = TFT_BLACK,
            uint16_t backgroundColor = TFT_WHITE,
            bool showScrollBar = true);
        ~TextBox();
        //
        void clear();
        //
        void scrollDown() { setCurrentLine(currentLine + 1); }
        void scrollUp() { setCurrentLine(currentLine - 1); }
        void setBackgroundColor(uint16_t color);
        void setCurrentLine(uint32_t line);
        void setForegroundColor(uint16_t color);
        void setCurrentText(const char *text) { currentText = text; }
        void setText(const char *text);
        //
        uint32_t getCurrentLine() const noexcept { return currentLine; }
        const char *getCurrentText() const noexcept { return currentText; }
        uint16_t getLinesPerScreen() const noexcept { return linesPerScreen; }
        Vector getTextPositionStart() const noexcept { return position; }
        Vector getTextPositionEnd() const noexcept { return this->display->getCursor(); }
        uint32_t getTextHeight() const noexcept { return totalLines == 0 ? 0 : (totalLines - 1) * 18; } // 12 pixel spacing + 6x6 pixel font
        uint32_t getTotalLines() const noexcept { return totalLines; }
        //
        uint16_t getBackgroundColor() const noexcept { return backgroundColor; }
        uint16_t getForegroundColor() const noexcept { return foregroundColor; }

    private:
        void setScrollBarPosition(); // Helper function to set the scrollbar position
        void setScrollBarSize();     // Helper function to set the scrollbar size
        //
        Draw *display;              // Pointer to the display
        ScrollBar *scrollBar;       // Pointer to the scrollbar
        uint32_t currentLine;       // Current line the cursor is on
        const char *currentText;    // current text in the text box
        Vector position;            // Position of the text box
        Vector size;                // Size of the text box
        uint16_t foregroundColor;   // Foreground color of the text box (words)
        uint16_t backgroundColor;   // Background color of the text box
        uint16_t charactersPerLine; // Number of characters that fit in one line
        uint16_t linesPerScreen;    // Number of lines that fit in the text box
        uint32_t totalLines;        // Total number of lines in the text box
        bool showScrollBar;         // Whether to show the scrollbar
    };
}