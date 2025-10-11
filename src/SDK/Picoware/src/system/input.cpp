#include "../system/input.hpp"
#include "../system/drivers/keyboard.h"
#include "../system/buttons.hpp"
#include <cstdio>

Input::Input()
    : lastButton(-1),
      elapsedTime(0), debounce(0.01f),
      wasPressed(false)
{
    keyboard_init();
    keyboard_set_key_available_callback([]()
                                        { Input::onKeyAvailableCallback(); });
    keyboard_set_background_poll(true);
}

int Input::charToButton(char key) const noexcept
{
    /* later I'll add more, but currently
    Picoware only uses these */
    switch (key)
    {
    case '\n':
    case '\r':
        return BUTTON_CENTER;
    case KEY_LEFT:
        return BUTTON_LEFT;
    case KEY_RIGHT:
        return BUTTON_RIGHT;
    case KEY_UP:
        return BUTTON_UP;
    case KEY_DOWN:
        return BUTTON_DOWN;
    case KEY_DEL:
        return BUTTON_BACKSPACE;
    case KEY_ESC:
    case 0x08:
    case 0x7F:
        return BUTTON_BACK;
    case 0x20:
        return BUTTON_SPACE;
    // Alphabet A-Z/a-z
    case 'a':
    case 'A':
        return BUTTON_A;
    case 'b':
    case 'B':
        return BUTTON_B;
    case 'c':
    case 'C':
        return BUTTON_C;
    case 'd':
    case 'D':
        return BUTTON_D;
    case 'e':
    case 'E':
        return BUTTON_E;
    case 'f':
    case 'F':
        return BUTTON_F;
    case 'g':
    case 'G':
        return BUTTON_G;
    case 'h':
    case 'H':
        return BUTTON_H;
    case 'i':
    case 'I':
        return BUTTON_I;
    case 'j':
    case 'J':
        return BUTTON_J;
    case 'k':
    case 'K':
        return BUTTON_K;
    case 'l':
    case 'L':
        return BUTTON_L;
    case 'm':
    case 'M':
        return BUTTON_M;
    case 'n':
    case 'N':
        return BUTTON_N;
    case 'o':
    case 'O':
        return BUTTON_O;
    case 'p':
    case 'P':
        return BUTTON_P;
    case 'q':
    case 'Q':
        return BUTTON_Q;
    case 'r':
    case 'R':
        return BUTTON_R;
    case 's':
    case 'S':
        return BUTTON_S;
    case 't':
    case 'T':
        return BUTTON_T;
    case 'u':
    case 'U':
        return BUTTON_U;
    case 'v':
    case 'V':
        return BUTTON_V;
    case 'w':
    case 'W':
        return BUTTON_W;
    case 'x':
    case 'X':
        return BUTTON_X;
    case 'y':
    case 'Y':
        return BUTTON_Y;
    case 'z':
    case 'Z':
        return BUTTON_Z;
    // Numbers 0-9
    case '0':
        return BUTTON_0;
    case '1':
        return BUTTON_1;
    case '2':
        return BUTTON_2;
    case '3':
        return BUTTON_3;
    case '4':
        return BUTTON_4;
    case '5':
        return BUTTON_5;
    case '6':
        return BUTTON_6;
    case '7':
        return BUTTON_7;
    case '8':
        return BUTTON_8;
    case '9':
        return BUTTON_9;
    // Special characters
    case KEY_MOD_SHL:
    case KEY_MOD_SHR:
        return BUTTON_SHIFT;
    case KEY_CAPS_LOCK:
        return BUTTON_CAPS_LOCK;
    case '.':
        return BUTTON_PERIOD;
    case ',':
        return BUTTON_COMMA;
    case ';':
        return BUTTON_SEMICOLON;
    case '-':
        return BUTTON_MINUS;
    case '=':
        return BUTTON_EQUAL;
    case '[':
        return BUTTON_LEFT_BRACKET;
    case ']':
        return BUTTON_RIGHT_BRACKET;
    case '/':
        return BUTTON_SLASH;
    case '\\':
        return BUTTON_BACKSLASH;
    default:
        return BUTTON_NONE;
    };
}

bool Input::isPressed()
{
    return keyboard_key_available();
}

bool Input::isHeld(uint8_t duration)
{
    return this->wasPressed && this->elapsedTime >= duration;
}

void Input::onKeyAvailableCallback()
{
    // nothing to do here yet
}

char Input::read()
{
    return keyboard_get_key();
}

char Input::readNonBlocking()
{
    if (keyboard_key_available())
    {
        return keyboard_get_key();
    }
    return 0; // No key available
}

void Input::reset(bool shouldDelay, int delayMs)
{
    this->elapsedTime = 0;
    this->wasPressed = false;
    this->lastButton = -1;
    if (shouldDelay)
    {
        // sleep_ms(delayMs);
    }
}

void Input::run()
{
    if (this->isPressed())
    {
        this->lastButton = this->charToButton(this->read());
        this->elapsedTime++;
        this->wasPressed = true;
    }
    else
    {
        this->lastButton = -1;
        this->wasPressed = false;
        this->elapsedTime = 0;
    }
}
