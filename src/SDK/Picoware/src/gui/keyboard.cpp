#include "../gui/keyboard.hpp"
#include "pico/time.h"
#include <vector>
#define millis() (to_ms_since_boot(get_absolute_time()))

// Define the keyboard layout structure
struct KeyLayout
{
    char normal;
    char shifted;
    uint8_t width; // Width in units (1 = normal key, 2 = double width, etc.)
};

// Define keyboard rows
static const KeyLayout row1[] = {
    {'1', '!', 1}, {'2', '@', 1}, {'3', '#', 1}, {'4', '$', 1}, {'5', '%', 1}, {'6', '^', 1}, {'7', '&', 1}, {'8', '*', 1}, {'9', '(', 1}, {'0', ')', 1}, {'-', '_', 1}, {'=', '+', 1}, {'\b', '\b', 1} // Backspace (special)
};

static const KeyLayout row2[] = {
    {'q', 'Q', 1}, {'w', 'W', 1}, {'e', 'E', 1}, {'r', 'R', 1}, {'t', 'T', 1}, {'y', 'Y', 1}, {'u', 'U', 1}, {'i', 'I', 1}, {'o', 'O', 1}, {'p', 'P', 1}, {'[', '{', 1}, {']', '}', 1}, {'?', '?', 1} // ? is a special function key (CLR)
};

static const KeyLayout row3[] = {
    {'\x01', '\x01', 1}, // Caps Lock (special)
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
    {'\r', '\r', 1} // Enter (special)
};

static const KeyLayout row4[] = {
    {'\x02', '\x02', 1}, // Shift (special)
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
    {'\\', '|', 1},
    {'\x02', '\x02', 1} // Right Shift (special)
};

static const KeyLayout row5[] = {
    {' ', ' ', 6},      // Space bar
    {'\x03', '\x03', 2} // Save (special)
};

static const KeyLayout *rows[] = {row1, row2, row3, row4, row5};
static const uint8_t rowSizes[] = {13, 13, 13, 13, 2};
static const uint8_t numRows = 5;

// Key dimensions
static const uint8_t keyWidth = 22;
static const uint8_t keyHeight = 35;
static const uint8_t keySpacing = 1;
static const uint8_t textboxHeight = 45;

Keyboard::Keyboard(
    Draw *draw,
    Input *inputManager,
    uint16_t textColor,
    uint16_t backgroundColor,
    uint16_t selectedColor,
    std::function<void(const std::string &)> onSaveCallback)
    : display(draw), inputManager(inputManager),
      isShiftPressed(false), isCapsLockOn(false),
      currentKey(BUTTON_NONE), textColor(textColor),
      backgroundColor(backgroundColor), selectedColor(selectedColor),
      dpadInput(BUTTON_NONE), response(""),
      onSaveCallback(onSaveCallback), isSavePressed(false),
      justStopped(false)
{
    // Initialize cursor position to top-left key
    cursorRow = 0;
    cursorCol = 0;
    lastInputTime = 0;
    inputDelay = 10; // milliseconds
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

    // Calculate total row width for centering
    uint16_t totalRowWidth = 0;
    for (uint8_t i = 0; i < rowSizes[row]; i++)
    {
        totalRowWidth += rows[row][i].width * keyWidth + (i > 0 ? keySpacing : 0);
    }

    // Calculate starting X position for centering
    uint16_t startX = (320 - totalRowWidth) / 2;

    // Calculate key position
    uint16_t xPos = startX;
    for (uint8_t i = 0; i < col; i++)
    {
        xPos += rows[row][i].width * keyWidth + keySpacing;
    }
    uint16_t yPos = textboxHeight + 10 + row * (keyHeight + keySpacing);

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
    std::string keyLabel = "";
    switch (key.normal)
    {
    case '\b':
        keyLabel = "DEL";
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
        if (row == 1 && col == 12)
        {
            keyLabel = "CLR"; // Clear function
        }
        break;
    default:
        keyLabel = std::string(1, displayChar);
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
    uint16_t keyboardHeight = numRows * (keyHeight + keySpacing) + 20;
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

    // Draw response text with word wrapping
    std::string displayText = response;
    uint16_t maxCharsPerLine = (display->getSize().x - 10) / 6; // Approximate character width
    uint16_t maxLines = (textboxHeight - 10) / 10;              // Approximate line height

    // Split text into lines if needed
    std::vector<std::string> lines;
    std::string currentLine = "";

    for (size_t i = 0; i < displayText.length(); i++)
    {
        if (displayText[i] == '\n')
        {
            lines.push_back(currentLine);
            currentLine = "";
        }
        else if (currentLine.length() >= maxCharsPerLine)
        {
            lines.push_back(currentLine);
            currentLine = displayText[i];
        }
        else
        {
            currentLine += displayText[i];
        }
    }
    if (!currentLine.empty())
    {
        lines.push_back(currentLine);
    }

    // Show only the last few lines that fit
    size_t startLine = lines.size() > maxLines ? lines.size() - maxLines : 0;

    for (size_t i = startLine; i < lines.size(); i++)
    {
        uint16_t yPos = 8 + (i - startLine) * 10;
        display->text(Vector(5, yPos), lines[i].c_str(), textColor, 1);
    }

    // Draw cursor
    std::string lastLine = lines.empty() ? "" : lines.back();
    uint16_t cursorX = 5 + lastLine.length() * 6;
    uint16_t cursorY = 8 + (lines.size() > 0 ? (std::min(lines.size(), (size_t)maxLines) - 1) * 10 : 0);

    if (millis() % 1000 < 500)
    { // Blinking cursor
        display->text(Vector(cursorX, cursorY), "_", textColor, 1);
    }
}

void Keyboard::handleInput()
{
    /* Keyboard layout
     * 1 2 3 4 5 6 7 8 9 0 - = DEL
     * Q W E R T Y U I O P [ ] CLR
     * Caps A S D F G H J K L ; ' Enter
     * Shift Z X C V B N M , . / \ Shift
     *         Space       Save
     */
    if (millis() - lastInputTime < inputDelay)
        return;

    switch (dpadInput)
    {
    case BUTTON_SPACE:
        setCursorPosition(4, 0);
        processKeyPress();
        lastInputTime = millis();
        break;
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
    case BUTTON_1:
        setCursorPosition(0, 0);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_2:
        setCursorPosition(0, 1);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_3:
        setCursorPosition(0, 2);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_4:
        setCursorPosition(0, 3);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_5:
        setCursorPosition(0, 4);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_6:
        setCursorPosition(0, 5);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_7:
        setCursorPosition(0, 6);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_8:
        setCursorPosition(0, 7);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_9:
        setCursorPosition(0, 8);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_0:
        setCursorPosition(0, 9);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_A:
        setCursorPosition(2, 1);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_B:
        setCursorPosition(3, 5);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_C:
        setCursorPosition(3, 3);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_D:
        setCursorPosition(2, 3);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_E:
        setCursorPosition(1, 2);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_F:
        setCursorPosition(2, 4);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_G:
        setCursorPosition(2, 5);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_H:
        setCursorPosition(2, 6);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_I:
        setCursorPosition(1, 7);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_J:
        setCursorPosition(2, 7);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_K:
        setCursorPosition(2, 8);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_L:
        setCursorPosition(2, 9);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_M:
        setCursorPosition(3, 7);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_N:
        setCursorPosition(3, 6);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_O:
        setCursorPosition(1, 8);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_P:
        setCursorPosition(1, 9);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_Q:
        setCursorPosition(1, 0);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_R:
        setCursorPosition(1, 3);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_S:
        setCursorPosition(2, 2);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_T:
        setCursorPosition(1, 4);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_U:
        setCursorPosition(1, 6);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_V:
        setCursorPosition(3, 4);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_W:
        setCursorPosition(1, 1);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_X:
        setCursorPosition(3, 2);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_Y:
        setCursorPosition(1, 5);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_Z:
        setCursorPosition(3, 1);
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_BACKSPACE:
        setCursorPosition(0, 12); // Backspace key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_SHIFT:
        setCursorPosition(3, 0); // Shift key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_CAPS_LOCK:
        setCursorPosition(2, 0); // Caps Lock key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_PERIOD:
        setCursorPosition(3, 9); // Period key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_COMMA:
        setCursorPosition(3, 8); // Comma key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_SEMICOLON:
        setCursorPosition(2, 10); // Semicolon key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_MINUS:
        setCursorPosition(0, 10); // Minus key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_EQUAL:
        setCursorPosition(0, 11); // Equal key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_LEFT_BRACKET:
        setCursorPosition(1, 10); // Left bracket key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_RIGHT_BRACKET:
        setCursorPosition(1, 11); // Right bracket key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_SLASH:
        setCursorPosition(3, 10); // Slash key
        processKeyPress();
        lastInputTime = millis();
        break;
    case BUTTON_BACKSLASH:
        setCursorPosition(3, 11); // Backslash key
        processKeyPress();
        lastInputTime = millis();
        break;
    default:
        break;
    }
}

void Keyboard::processKeyPress()
{
    if (cursorRow >= numRows || cursorCol >= rowSizes[cursorRow])
        return;

    const KeyLayout &key = rows[cursorRow][cursorCol];
    currentKey = key.normal;
    switch (currentKey)
    {
    case '\b': // Backspace
        if (response.length() > 0)
        {
            response.pop_back();
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
        isSavePressed = true;
        break;

    case '?': // Special function
        if (cursorRow == 1 && cursorCol == 12)
        {
            // Clear function
            response = "";
        }
        break;

    default:
        // Regular character
        if (currentKey >= 'a' && currentKey <= 'z')
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

        // Reset shift after character entry
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
    isSavePressed = false;
}

void Keyboard::run(bool swap)
{
    if (justStopped)
    {
        justStopped = false;
        return;
    }

    dpadInput = inputManager->getLastButton();

    handleInput();
    drawTextbox();
    drawKeyboard();

    if (swap)
    {
        display->swap();
    }
}

void Keyboard::setCursorPosition(uint8_t row, uint8_t col)
{
    if (row < numRows && col < rowSizes[row])
    {
        cursorRow = row;
        cursorCol = col;
    }
}
