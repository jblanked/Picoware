#include "../../internal/gui/textbox.hpp"

namespace Picoware
{
    TextBox::TextBox(Draw *draw, uint16_t y, uint16_t height, uint16_t foregroundColor, uint16_t backgroundColor)
        : display(draw), foregroundColor(foregroundColor), backgroundColor(backgroundColor),
          charactersPerLine(0), linesPerScreen(0), totalLines(0), currentLine(-1)
    {
        currentText = "";
        position = Vector(0, y);
        size = Vector(draw->getSize().x, height);
        display->clear(position, size, backgroundColor);
        scrollBar = new ScrollBar(display, Vector(0, 0), Vector(0, 0), foregroundColor, backgroundColor);
        // font is 2, textSize is 1
        auto board = display->getBoard();
        if (board.boardType == BOARD_TYPE_VGM || board.boardType == BOARD_TYPE_JBLANKED)
        {
            charactersPerLine = 52; // width is 320
            linesPerScreen = 20;    // height is 240
        }
        else if (board.boardType == BOARD_TYPE_PICO_CALC)
        {
            charactersPerLine = 52; // width is 320
            linesPerScreen = 26;    // height is 320
        }
        this->display->swap();
    }

    TextBox::~TextBox()
    {
        delete scrollBar;
    }

    void TextBox::clear()
    {
        display->clear(position, size, backgroundColor);
        scrollBar->clear();
        totalLines = 0;
        setScrollBarSize();
        setScrollBarPosition();
        this->display->swap();
    }

    void TextBox::setCurrentLine(uint32_t line)
    {
        if (line > (totalLines - 1))
            return;

        currentLine = line;
        this->setText(currentText);
    }

    void TextBox::setText(const char *text)
    {
        display->clear(position, size, backgroundColor);
        scrollBar->clear();
        this->currentText = text;
        Vector cursorPos = Vector(position.x + 1, position.y + 1); // 1 pixel padding
        auto len = strlen(text);
        if (len == 0)
        {
            totalLines = 0;
            setScrollBarSize();
            setScrollBarPosition();
            return;
        }

        // First pass: Count total lines to properly set up scrollbar
        size_t lineStart = 0;   // Start index of current line
        size_t lineLength = 0;  // Current length of line
        size_t wordStart = 0;   // Start index of current word
        size_t wordLength = 0;  // Length of current word
        size_t i = 0;           // Current position in text
        totalLines = 1;         // Start with one line
        size_t lineCounter = 0; // To keep track of which line we're currently processing

        // First loop: Just count total lines
        while (i < len)
        {
            // Check for newline character first
            if (text[i] == '\n')
            {
                totalLines++;
                lineStart = i + 1; // Start after the newline
                lineLength = 0;
                i++; // Move past the newline
                continue;
            }

            // Skip leading spaces at beginning of a line
            if (lineLength == 0)
            {
                while (i < len && text[i] == ' ')
                {
                    i++;
                }
                lineStart = i;
            }

            // Find the length of the current word
            wordStart = i;
            wordLength = 0;
            while (i < len && text[i] != ' ' && text[i] != '\n')
            {
                wordLength++;
                i++;
            }

            // Check if this word will fit on the current line
            if (lineLength + wordLength > charactersPerLine && lineLength > 0)
            {
                // Word doesn't fit, start a new line
                totalLines++;
                lineStart = wordStart;
                lineLength = 0;

                // Count the word on the new line
                lineLength += wordLength;
            }
            else
            {
                // Word fits, add it to the current line
                lineLength += wordLength;

                // Add space after word (if not at the end of text)
                if (i < len && text[i] == ' ')
                {
                    lineLength++;
                    i++; // Move past the space
                }

                wordLength = 0; // Reset for next word
            }
        }

        // Reset for second pass - rendering
        lineStart = 0;
        lineLength = 0;
        wordStart = 0;
        wordLength = 0;
        i = 0;
        lineCounter = 0;

        if (currentLine == -1)
        {
            // initialize currentLine to the total number of lines
            currentLine = totalLines;
        }

        // Calculate the first visible line - implement proper scrolling behavior
        uint32_t firstVisibleLine = 0;
        if (currentLine > linesPerScreen)
        {
            firstVisibleLine = currentLine - linesPerScreen;
        }

        // Second loop: Render only visible lines (from firstVisibleLine to firstVisibleLine + linesPerScreen)
        while (i < len)
        {
            // Check for newline character first
            if (text[i] == '\n')
            {
                // Move to the next line
                lineCounter++;
                lineLength = 0;
                i++; // Move past the newline

                // Prepare cursor for next line if it's in view
                if (lineCounter >= firstVisibleLine && lineCounter < firstVisibleLine + linesPerScreen)
                {
                    cursorPos.x = position.x + 1;                                         // Reset x position
                    cursorPos.y = position.y + 1 + (lineCounter - firstVisibleLine) * 12; // Position based on line number
                }
                continue;
            }

            // Skip leading spaces at beginning of a line
            if (lineLength == 0)
            {
                while (i < len && text[i] == ' ')
                {
                    i++;
                }
                lineStart = i;
            }

            // Find the length of the current word
            wordStart = i;
            wordLength = 0;
            while (i < len && text[i] != ' ' && text[i] != '\n')
            {
                wordLength++;
                i++;
            }

            // Check if this word will fit on the current line
            if (lineLength + wordLength > charactersPerLine && lineLength > 0)
            {
                // Word doesn't fit, start a new line
                lineCounter++;
                lineStart = wordStart;
                lineLength = 0;

                // Only render if this line is in view
                if (lineCounter >= firstVisibleLine && lineCounter < firstVisibleLine + linesPerScreen)
                {
                    cursorPos.x = position.x + 1;
                    cursorPos.y = position.y + 1 + (lineCounter - firstVisibleLine) * 12; // Position based on line number

                    // Draw the word on the new line
                    for (size_t j = wordStart; j < i; j++)
                    {
                        display->text(cursorPos, text[j], foregroundColor);
                        cursorPos.x = this->display->getCursor().x; // Update cursor position
                    }
                }
                lineLength += wordLength;
            }
            else
            {
                // Word fits, add it to the current line
                if (lineCounter >= firstVisibleLine && lineCounter < firstVisibleLine + linesPerScreen)
                {
                    // If this is the first word of a visible line, set the y position appropriately
                    if (lineLength == 0)
                    {
                        cursorPos.x = position.x + 1;
                        cursorPos.y = position.y + 1 + (lineCounter - firstVisibleLine) * 12; // Position based on line number
                    }

                    for (size_t j = wordStart; j < i; j++)
                    {
                        display->text(cursorPos, text[j], foregroundColor);
                        cursorPos.x = this->display->getCursor().x; // Update cursor position
                    }
                }
                lineLength += wordLength;

                // Add space after word (if not at the end of text)
                if (i < len && text[i] == ' ')
                {
                    if (lineCounter >= firstVisibleLine && lineCounter < firstVisibleLine + linesPerScreen)
                    {
                        display->text(cursorPos, ' ', foregroundColor);
                        cursorPos.x = this->display->getCursor().x;
                    }
                    lineLength++;
                    i++; // Move past the space
                }

                wordLength = 0; // Reset for next word
            }

            // If we've rendered all visible lines and the next line is out of view, we can stop
            if (lineCounter >= firstVisibleLine + linesPerScreen)
                break;
        }

        // Update scrollbar
        setScrollBarSize();
        setScrollBarPosition();
        scrollBar->draw();
        this->display->swap();
    }

    void TextBox::setForegroundColor(uint16_t color)
    {
        foregroundColor = color;
        display->color(color);
    }

    void TextBox::setBackgroundColor(uint16_t color)
    {
        backgroundColor = color;
        display->background(color);
    }

    void TextBox::setScrollBarSize()
    {
        float contentHeight = getTextHeight();
        float viewHeight = size.y;
        float barHeight;

        if (contentHeight <= viewHeight || contentHeight <= 0.0f)
            barHeight = viewHeight - 2; // 1 pixel padding (+1 pixel for the scrollbar)
        else
            barHeight = viewHeight * (viewHeight / contentHeight);

        // enforce minimum scrollbar height
        const float minBarHeight = 12.0f;
        if (barHeight < minBarHeight)
            barHeight = minBarHeight;

        // fixed width for scrollbar
        const float barWidth = 6.0f;
        scrollBar->setSize(Vector(barWidth, barHeight));
    }

    void TextBox::setScrollBarPosition()
    {
        Vector barSize = scrollBar->getSize();
        float barHeight = barSize.y;
        float barWidth = barSize.x;

        // Calculate the proper scroll position based on current line and total lines
        float scrollRatio = 0.0f;
        if (totalLines > linesPerScreen && totalLines > 0)
        {
            // Ensure we don't start scrolling until after linesPerScreen
            if (currentLine <= linesPerScreen)
                scrollRatio = 0.0f;
            else
                scrollRatio = float(currentLine - linesPerScreen) / float(totalLines - linesPerScreen);
        }

        // maximum vertical movement for scrollbar thumb
        float maxOffset = size.y - barHeight - 2; // Account for padding
        float barOffsetY = scrollRatio * maxOffset;

        float barX = position.x + size.x - barWidth - 1; // 1 pixel padding
        float barY = position.y + barOffsetY + 1;        // 1 pixel padding

        scrollBar->setPosition(Vector(barX, barY));
    }
}