#include "../../internal/system/input.hpp"
#include "../../internal/system/pico-calc/keyboard.h"
#include <string.h>
namespace Picoware
{
    // Constructor
    PicoCalcKeyboard::PicoCalcKeyboard()
    {
        keyboard_init(onKeyAvailableCallback);
    }

    // Static callback function for C interface
    void PicoCalcKeyboard::onKeyAvailableCallback()
    {
        // This callback is called when a key becomes available
        // You can add custom handling here if needed
    }

    // Check if a key is available (non-blocking)
    bool PicoCalcKeyboard::available()
    {
        return keyboard_key_available();
    }

    int PicoCalcKeyboard::charToButton(char key)
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
        case KEY_ESC:
        case KEY_DEL:
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
        default:
            return BUTTON_NONE;
        };
    }

    // Read a key (blocking - waits for key if none available)
    char PicoCalcKeyboard::read()
    {
        return keyboard_get_key();
    }

    // Read a key (non-blocking - returns 0 if no key available)
    char PicoCalcKeyboard::readNonBlocking()
    {
        if (keyboard_key_available())
        {
            return keyboard_get_key();
        }
        return 0; // No key available
    }

    // Read a key and convert it to a button assignment
    int PicoCalcKeyboard::readToButton()
    {
        char key = readNonBlocking();
        if (key == 0)
        {
            return BUTTON_NONE; // No key available
        }
        return charToButton(key);
    }

    HW504::HW504(int x_pin, int y_pin, int button_pin, int orientation)
    {
        this->x_axis = x_pin;
        this->y_axis = y_pin;
        this->button = button_pin;
        this->orientation = orientation;
        pinMode(this->x_axis, INPUT);
        pinMode(this->y_axis, INPUT);
        pinMode(this->button, INPUT_PULLUP);
    }

    Vector HW504::axes()
    {
        Vector v;
        v.x = analogRead(this->x_axis);
        v.y = analogRead(this->y_axis);

        switch (this->orientation)
        {
        case HW_ORIENTATION_NORMAL:
            break;
        case HW_ORIENTATION_90:
            v = Vector(v.y, 1023 - v.x);
            break;
        case HW_ORIENTATION_180:
            v = Vector(1023 - v.x, 1023 - v.y);
            break;
        case HW_ORIENTATION_270:
            v = Vector(1023 - v.y, v.x);
            break;
        default:
            break;
        }
        return v;
    }

    int HW504::_button()
    {
        return digitalRead(this->button);
    }

    int HW504::_x_axis()
    {
        Vector v = this->axes();
        return v.x;
    }

    int HW504::_y_axis()
    {
        Vector v = this->axes();
        return v.y;
    }

    bool HW504::value(int button)
    {
        switch (button)
        {
        case HW_LEFT_BUTTON:
            return this->_x_axis() < 100;
        case HW_RIGHT_BUTTON:
            return this->_x_axis() > 1000;
        case HW_UP_BUTTON:
            return this->_y_axis() < 100;
        case HW_DOWN_BUTTON:
            return this->_y_axis() > 1000;
        case HW_CENTER_BUTTON:
            return this->_button() == LOW;
        default:
            return false;
        }
    }

    ButtonUART::ButtonUART(float debounce)
    {
        this->serial = new SerialPIO(0, 1);
        this->serial->begin(115200);
        this->debounce = debounce;
        this->startTime = millis();
        this->lastButton = -1; // Initialize to -1
    }

    void ButtonUART::run()
    {
        if (millis() - this->startTime > this->debounce)
        {
            this->lastButton = -1;
            this->startTime = millis();
            // Check if data is available to read
            if (this->serial->available() > 0)
            {
                // Read the incoming byte as a character
                char incomingChar = this->serial->read();
                switch ((int)incomingChar)
                {
                case 48:
                    this->lastButton = BUTTON_UP;
                    break;
                case 49:
                    this->lastButton = BUTTON_DOWN;
                    break;
                case 50:
                    this->lastButton = BUTTON_LEFT;
                    break;
                case 51:
                    this->lastButton = BUTTON_RIGHT;
                    break;
                case 52:
                    this->lastButton = BUTTON_CENTER;
                    break;
                case 53:
                    this->lastButton = BUTTON_BACK;
                    break;
                case 54:
                    this->lastButton = BUTTON_START;
                    break;
                default:
                    this->lastButton = -1;
                    break;
                }
            }
        }
    }

    Input::Input()
        : pin(-1), lastButton(-1), buttonAssignment(-1),
          elapsedTime(0), debounce(0.05f),
          wasPressed(false), hw(nullptr), bt(nullptr), keyboard(nullptr)
    {
    }

    Input::Input(uint8_t pin, uint8_t button, float debounce)
    {
        this->pin = pin;
        this->buttonAssignment = button;
        this->debounce = debounce;
        this->lastButton = -1;
        this->elapsedTime = 0;
        this->wasPressed = false;
        this->hw = nullptr;
        this->bt = nullptr;
        this->keyboard = nullptr;
        pinMode(this->pin, INPUT_PULLUP);
    }

    Input::Input(HW504 *hw, uint8_t button)
    {
        this->pin = -1;
        this->buttonAssignment = button;
        this->debounce = 0.05f;
        this->lastButton = -1;
        this->elapsedTime = 0;
        this->wasPressed = false;
        this->hw = hw;
        this->bt = nullptr;
        this->keyboard = nullptr;
    }

    Input::Input(ButtonUART *bt)
    {
        this->pin = -1;
        this->buttonAssignment = BUTTON_UART;
        this->debounce = 0.05f;
        this->lastButton = -1;
        this->elapsedTime = 0;
        this->wasPressed = false;
        this->bt = bt;
        this->hw = nullptr;
        this->keyboard = nullptr;
    }

    Input::Input(PicoCalcKeyboard *keyboard)
    {
        this->pin = -1;
        this->buttonAssignment = BUTTON_PICO_CALC;
        this->debounce = 0.05f;
        this->lastButton = -1;
        this->elapsedTime = 0;
        this->wasPressed = false;
        this->keyboard = keyboard;
        this->hw = nullptr;
        this->bt = nullptr;
    }

    bool Input::isPressed()
    {
        if (this->hw)
            return this->hw->value(this->buttonAssignment);
        if (this->bt)
            return this->bt->lastButton != -1; // Check if UART has valid button
        if (this->pin != -1)
            return digitalRead(this->pin) == LOW;
        if (this->keyboard)
            return this->keyboard->available(); // Check if a key is available
        return false;
    }

    bool Input::isHeld(uint8_t duration)
    {
        return this->isPressed() && this->elapsedTime >= duration;
    }

    void Input::reset()
    {
        this->elapsedTime = 0;
        this->wasPressed = false;
        this->lastButton = -1;
        if (this->bt)
        {
            this->bt->lastButton = -1;
            this->bt->startTime = millis();
        }
        else if (!this->hw || this->keyboard)
        {
            this->startTime = millis();
        }
    }

    void Input::run()
    {
        bool currentlyPressed = false;

        if (this->bt)
        {
            this->bt->run();
            currentlyPressed = (this->bt->lastButton != -1);
            if (currentlyPressed)
            {
                this->lastButton = this->bt->lastButton;
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
        else if (this->hw)
        {
            currentlyPressed = this->hw->value(this->buttonAssignment);
            if (currentlyPressed)
            {
                this->lastButton = this->buttonAssignment;
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
        else if (this->keyboard)
        {
            if (this->keyboard->available())
            {
                this->lastButton = this->keyboard->readToButton();
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
        else if (this->pin != -1 && millis() - this->startTime > this->debounce)
        {
            this->startTime = millis();
            currentlyPressed = (digitalRead(this->pin) == LOW);
            if (currentlyPressed)
            {
                this->lastButton = this->buttonAssignment;
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
    }

    Input::operator bool() const
    {
        if (this->hw)
            return this->hw != nullptr;
        if (this->bt)
            return this->bt != nullptr;
        if (this->keyboard)
            return this->keyboard != nullptr;
        return this->pin != -1;
    }
}