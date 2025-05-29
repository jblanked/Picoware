#pragma once
#include "../../../internal/system/bluetooth.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#if ENABLE_CLASSIC != 0
using namespace Picoware;
static Bluetooth *bluetoothKeyboard = nullptr;
static void keyboardStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        viewManager->back();
        return;
    }
    if (bluetoothKeyboard != nullptr)
    {
        delete bluetoothKeyboard;
        bluetoothKeyboard = nullptr;
    }
    auto draw = viewManager->getDraw();
    draw->text(Vector(5, 5), "Running Bluetooth Keyboard...");
    draw->text(Vector(5, 20), "Type in your text then press SAVE.");
    draw->text(Vector(5, 35), "Press BACK to exit.");
    draw->swap();
    bluetoothKeyboard = new Bluetooth();
    bluetoothKeyboard->beginKeyboardBLE("Picoware Keyboard");
    delay(2000); // Give some time for the keyboard to initialize and user to read the instructions
    // Set up save callback to send the response to the keyboard
    viewManager->getKeyboard()->setSaveCallback([](const String &response)
                                                { bluetoothKeyboard->keyboardPrint(response.c_str()); });
}

static void keyboardRun(ViewManager *viewManager)
{
    viewManager->getKeyboard()->run();
}

static void keyboardStop(ViewManager *viewManager)
{
    if (bluetoothKeyboard != nullptr)
    {
        bluetoothKeyboard->stopKeyboardBLE();
        delete bluetoothKeyboard;
        bluetoothKeyboard = nullptr;
    }
    if (viewManager->getKeyboard() != nullptr)
    {
        viewManager->getKeyboard()->reset();
    }
}

const PROGMEM View bluetoothKeyboardView = View("Bluetooth BLE Keyboard", keyboardRun, keyboardStart, keyboardStop);
#endif // ENABLE_CLASSIC != 0