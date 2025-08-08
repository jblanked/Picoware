#include "../system/input.hpp"
#include "../system/drivers/keyboard.h"

Input::Input()
    : lastButton(-1),
      elapsedTime(0), debounce(0.05f),
      wasPressed(false)
{
    keyboard_init(onKeyAvailableCallback);
    this->debounce = 0.01f;
    this->lastButton = -1;
    this->elapsedTime = 0;
    this->wasPressed = false;
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
    // called when a key is available
    // nothing to do here for now
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

void Input::reset()
{
    this->elapsedTime = 0;
    this->wasPressed = false;
    this->lastButton = -1;
}

void Input::run()
{
    bool currentlyPressed = false;

    if (this->isPressed())
    {
        this->lastButton = this->read();
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
