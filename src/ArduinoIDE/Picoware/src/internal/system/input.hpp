#pragma once
#include "Arduino.h"
#include "../../internal/gui/vector.hpp"
#include "../../internal/boards.hpp"
#include "../../internal/system/buttons.hpp"
namespace Picoware
{
    class HW504
    {
    public:
        int x_axis;
        int y_axis;
        int orientation;
        int button;

        HW504(int x_pin = 26, int y_pin = 27, int button_pin = 21, int orientation = HW_ORIENTATION_NORMAL);
        Vector axes();                             // Read the raw ADC values from both axes and transform them based on the current orientation.
        bool value(int button = HW_CENTER_BUTTON); // Return the state of a button based on the transformed x,y axis values.

    private:
        int _button(); // Read the button value from the joystick
        int _x_axis(); // Return the transformed x-axis value
        int _y_axis(); // Return the transformed y-axis value
    };

    class ButtonUART
    {
    public:
        ButtonUART(float debounce = 0.05f);
        void run();
        int lastButton;
        unsigned long startTime;

    private:
        SerialPIO *serial;
        float debounce;
    };

    class Input
    {
    public:
        Input();
        Input(uint8_t pin, uint8_t button, float debounce = 0.05f);
        Input(HW504 *hw, uint8_t button);
        Input(ButtonUART *bt);
        //
        ButtonUART *getButtonUART() const noexcept { return this->bt; }
        uint8_t getButtonAssignment() const noexcept { return this->buttonAssignment; }
        int getLastButton() const noexcept { return this->lastButton; }
        uint8_t getPin() const noexcept { return this->pin; }
        HW504 *getJoystick() const noexcept { return this->hw; }
        //
        bool isPressed();
        bool isHeld(uint8_t duration = 3);
        void reset();
        void run();
        //
        operator bool() const;

    private:
        uint8_t pin;
        uint8_t buttonAssignment;
        int lastButton;
        float debounce;
        unsigned long startTime;
        float elapsedTime;
        bool wasPressed;
        HW504 *hw;
        ButtonUART *bt;
    };

}