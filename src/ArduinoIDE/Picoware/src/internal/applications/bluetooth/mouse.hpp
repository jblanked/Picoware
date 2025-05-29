#pragma once
#include "../../../internal/system/bluetooth.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#if ENABLE_CLASSIC != 0
using namespace Picoware;
static Bluetooth *bluetoothMouse = nullptr;
static void mouseStart(ViewManager *viewManager)
{
    if (bluetoothMouse != nullptr)
    {
        delete bluetoothMouse;
        bluetoothMouse = nullptr;
    }
    auto draw = viewManager->getDraw();
    draw->text(Vector(5, 5), "Running Bluetooth Mouse...");
    draw->text(Vector(5, 20), "Press any button to move the mouse.");
    draw->text(Vector(5, 35), "Press CENTER to switch speed (1, 5, 10, or 20)");
    draw->text(Vector(5, 50), "Press BACK to exit.");
    draw->swap();
    bluetoothMouse = new Bluetooth();
    bluetoothMouse->beginMouseBLE("Picoware Mouse");
}

static void mouseRun(ViewManager *viewManager)
{
    static uint8_t speed = 5; // Default speed for mouse movement
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        bluetoothMouse->moveMouse(0, -speed);
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        bluetoothMouse->moveMouse(0, speed);
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        bluetoothMouse->moveMouse(-speed, 0);
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
        bluetoothMouse->moveMouse(speed, 0);
        inputManager->reset(true);
        break;
    case BUTTON_CENTER:
        // speed options 1, 5, 10, 20
        if (speed == 1)
        {
            speed = 5;
        }
        else if (speed == 5)
        {
            speed = 10;
        }
        else if (speed == 10)
        {
            speed = 20;
        }
        else
        {
            speed = 1;
        }
        inputManager->reset(true);
        break;
    default:
        break;
    }
}

static void mouseStop(ViewManager *viewManager)
{
    if (bluetoothMouse != nullptr)
    {
        bluetoothMouse->stopMouseBLE();
        delete bluetoothMouse;
        bluetoothMouse = nullptr;
    }
}

const PROGMEM View bluetoothMouseView = View("Bluetooth BLE Mouse", mouseRun, mouseStart, mouseStop);
#endif // ENABLE_CLASSIC != 0