#include "../../internal/system/keyboard.hpp"

namespace Picoware
{
    // Define the keyboard layout structure
    struct KeyLayout
    {
        char normal;
        char shifted;
        uint8_t width; // Width in units (1 = normal key, 2 = double width, etc.)
    };

    // Define keyboard rows
    static const KeyLayout row1[] = {
        {'1', '!', 1}, {'2', '@', 1}, {'3', '#', 1}, {'4', '$', 1}, {'5', '%', 1}, {'6', '^', 1}, {'7', '&', 1}, {'8', '*', 1}, {'9', '(', 1}, {'0', ')', 1}, {'-', '_', 1}, {'=', '+', 1}, {'\b', '\b', 2} // Backspace (special)
    };

    static const KeyLayout row2[] = {
        {'q', 'Q', 1}, {'w', 'W', 1}, {'e', 'E', 1}, {'r', 'R', 1}, {'t', 'T', 1}, {'y', 'Y', 1}, {'u', 'U', 1}, {'i', 'I', 1}, {'o', 'O', 1}, {'p', 'P', 1}, {'[', '{', 1}, {']', '}', 1}, {'\\', '|', 1}, {'?', '?', 1} // ? is a special function key
    };

    static const KeyLayout row3[] = {
        {'\x01', '\x01', 2}, // Caps Lock (special)
        {'a', 'A', 1},
        {'s', 'S', 1},
        {'d', 'D', 1},
        {'f', 'F', 1},
        {'g', 'G', 1},
        {'h', 'H', 1},
        {'j', 'J', 1},
        {'k', 'K', 1},
        {'l', 'L', 1},
        {';', ':', 1},
        {'\'', '"', 1},
        {'\r', '\r', 2} // Enter (special)
    };

    static const KeyLayout row4[] = {
        {'\x02', '\x02', 3}, // Shift (special)
        {'z', 'Z', 1},
        {'x', 'X', 1},
        {'c', 'C', 1},
        {'v', 'V', 1},
        {'b', 'B', 1},
        {'n', 'N', 1},
        {'m', 'M', 1},
        {',', '<', 1},
        {'.', '>', 1},
        {'/', '?', 1},
        {'\x02', '\x02', 2} // Right Shift (special)
    };

    static const KeyLayout row5[] = {
        {' ', ' ', 8},      // Space bar
        {'\x03', '\x03', 4} // Save (special)
    };

    static const KeyLayout *rows[] = {row1, row2, row3, row4, row5};
    static const uint8_t rowSizes[] = {13, 14, 13, 12, 2};
    static const uint8_t numRows = 5;

    // Key dimensions
    static const uint8_t keyWidth = 20;
    static const uint8_t keyHeight = 25;
    static const uint8_t keySpacing = 2;
    static const uint8_t textboxHeight = 30;

    Keyboard::Keyboard(
        Draw *draw,
        InputManager *inputManager,
        uint16_t textColor,
        uint16_t backgroundColor,
        uint16_t selectedColor,
        std::function<void(const String &)> onSaveCallback)
        : display(draw), inputManager(inputManager),
          isShiftPressed(false), isCapsLockOn(false),
          currentKey(BUTTON_NONE), textColor(textColor),
          backgroundColor(backgroundColor), selectedColor(selectedColor),
          dpadInput(BUTTON_NONE), response(""),
          onSaveCallback(onSaveCallback),
          justStopped(false)
    {
        // Initialize cursor position to top-left key
        cursorRow = 0;
        cursorCol = 0;
        lastInputTime = 0;
        inputDelay = 200; // milliseconds
    }

    Keyboard::~Keyboard()
    {
        // Destructor implementation
    }

    void Keyboard::drawKey(uint8_t row, uint8_t col, bool isSelected)
    {
        if (row >= numRows || col >= rowSizes[row])
            return;

        const KeyLayout &key = rows[row][col];

        // Calculate key position
        uint16_t xPos = 5; // Start margin
        for (uint8_t i = 0; i < col; i++)
        {
            xPos += rows[row][i].width * keyWidth + keySpacing;
        }
        uint16_t yPos = textboxHeight + 5 + row * (keyHeight + keySpacing);

        // Calculate key size
        uint16_t width = key.width * keyWidth + (key.width - 1) * keySpacing;
        uint16_t height = keyHeight;

        // Draw key background
        uint16_t bgColor = isSelected ? selectedColor : backgroundColor;
        display->fillRect(Vector(xPos, yPos), Vector(width, height), bgColor);

        // Draw key border
        display->drawRect(Vector(xPos, yPos), Vector(width, height), textColor);

        // Determine what character to display
        char displayChar = key.normal;
        bool shouldCapitalize = false;

        if (key.normal >= 'a' && key.normal <= 'z')
        {
            shouldCapitalize = (isShiftPressed && !isCapsLockOn) || (!isShiftPressed && isCapsLockOn);
            displayChar = shouldCapitalize ? key.shifted : key.normal;
        }
        else if (isShiftPressed && key.normal != key.shifted)
        {
            displayChar = key.shifted;
        }

        // Draw key label
        String keyLabel = "";
        switch (key.normal)
        {
        case '\b':
            keyLabel = "BCK";
            break;
        case '\x01':
            keyLabel = isCapsLockOn ? "CAPS*" : "CAPS";
            break;
        case '\x02':
            keyLabel = isShiftPressed ? "SHFT*" : "SHFT";
            break;
        case '\r':
            keyLabel = "ENT";
            break;
        case ' ':
            keyLabel = "SPACE";
            break;
        case '\x03':
            keyLabel = "SAVE";
            break;
        case '?':
            if (row == 1 && col == 13)
            {
                keyLabel = "CLR"; // Clear function
            }
            break;
        default:
            keyLabel = String(displayChar);
            break;
        }

        // Center the text
        uint16_t textX = xPos + width / 2 - keyLabel.length() * 3;
        uint16_t textY = yPos + height / 2 - 4;

        display->text(Vector(textX, textY), keyLabel.c_str(), textColor, 1);
    }

    void Keyboard::drawKeyboard()
    {
        // Clear keyboard area
        uint16_t keyboardHeight = numRows * (keyHeight + keySpacing) + 10;
        display->fillRect(Vector(0, textboxHeight),
                          Vector(display->getSize().x, keyboardHeight), backgroundColor);

        // Draw all keys
        for (uint8_t row = 0; row < numRows; row++)
        {
            for (uint8_t col = 0; col < rowSizes[row]; col++)
            {
                bool isSelected = (row == cursorRow && col == cursorCol);
                drawKey(row, col, isSelected);
            }
        }
    }

    void Keyboard::drawTextbox()
    {
        // Clear textbox area
        display->fillRect(Vector(0, 0), Vector(display->getSize().x, textboxHeight), backgroundColor);

        // Draw textbox border
        display->drawRect(Vector(2, 2), Vector(display->getSize().x - 4, textboxHeight - 4), textColor);

        // Draw response text
        String displayText = response;
        uint16_t maxChars = (display->getSize().x - 10) / 6; // Approximate character width

        if (displayText.length() > maxChars)
        {
            displayText = displayText.substring(displayText.length() - maxChars);
        }

        display->text(Vector(5, 8), displayText.c_str(), textColor, 1);

        // Draw cursor
        uint16_t cursorX = 5 + displayText.length() * 6;
        if (millis() % 1000 < 500)
        { // Blinking cursor
            display->text(Vector(cursorX, 8), "_", textColor, 1);
        }
    }

    void Keyboard::handleInput()
    {
        if (millis() - lastInputTime < inputDelay)
            return;

        switch (dpadInput)
        {
        case BUTTON_UP:
            if (cursorRow > 0)
            {
                cursorRow--;
                if (cursorCol >= rowSizes[cursorRow])
                {
                    cursorCol = rowSizes[cursorRow] - 1;
                }
            }
            lastInputTime = millis();
            break;

        case BUTTON_DOWN:
            if (cursorRow < numRows - 1)
            {
                cursorRow++;
                if (cursorCol >= rowSizes[cursorRow])
                {
                    cursorCol = rowSizes[cursorRow] - 1;
                }
            }
            lastInputTime = millis();
            break;

        case BUTTON_LEFT:
            if (cursorCol > 0)
            {
                cursorCol--;
            }
            else if (cursorRow > 0)
            {
                // Wrap to end of previous row
                cursorRow--;
                cursorCol = rowSizes[cursorRow] - 1;
            }
            lastInputTime = millis();
            break;

        case BUTTON_RIGHT:
            if (cursorCol < rowSizes[cursorRow] - 1)
            {
                cursorCol++;
            }
            else if (cursorRow < numRows - 1)
            {
                // Wrap to start of next row
                cursorRow++;
                cursorCol = 0;
            }
            lastInputTime = millis();
            break;

        case BUTTON_CENTER:
            processKeyPress();
            lastInputTime = millis();
            break;
        default:
            // No input or unhandled input
            break;
        }
    }

    void Keyboard::processKeyPress()
    {
        if (cursorRow >= numRows || cursorCol >= rowSizes[cursorRow])
            return;

        const KeyLayout &key = rows[cursorRow][cursorCol];
        char keyChar = key.normal;

        switch (keyChar)
        {
        case '\b': // Backspace
            if (response.length() > 0)
            {
                response.remove(response.length() - 1);
            }
            break;

        case '\x01': // Caps Lock
            isCapsLockOn = !isCapsLockOn;
            break;

        case '\x02': // Shift
            isShiftPressed = !isShiftPressed;
            break;

        case '\r': // Enter
            response += '\n';
            break;

        case ' ': // Space
            response += ' ';
            break;

        case '\x03': // Save
            if (onSaveCallback)
            {
                onSaveCallback(response);
            }
            break;

        case '?': // Special function
            if (cursorRow == 1 && cursorCol == 13)
            {
                // Clear function
                response = "";
            }
            break;

        default:
            // Regular character
            if (keyChar >= 'a' && keyChar <= 'z')
            {
                // Handle letter case
                bool shouldCapitalize = (isShiftPressed && !isCapsLockOn) ||
                                        (!isShiftPressed && isCapsLockOn);
                response += shouldCapitalize ? key.shifted : key.normal;
            }
            else if (isShiftPressed && key.normal != key.shifted)
            {
                // Handle shifted special characters
                response += key.shifted;
            }
            else
            {
                // Normal character
                response += key.normal;
            }

            // Reset shift after character entry (like on real keyboards)
            if (isShiftPressed)
            {
                isShiftPressed = false;
            }
            break;
        }
    }

    void Keyboard::reset()
    {
        justStopped = true;
        cursorRow = 0;
        cursorCol = 0;
        isShiftPressed = false;
        isCapsLockOn = false;
        response = "";
        lastInputTime = 0;
        onSaveCallback = nullptr;
    }

    void Keyboard::run()
    {
        if (justStopped)
        {
            justStopped = false;
            return;
        }

        dpadInput = inputManager->getInput();

        handleInput();
        drawTextbox();
        drawKeyboard();

        display->swap();
    }
}