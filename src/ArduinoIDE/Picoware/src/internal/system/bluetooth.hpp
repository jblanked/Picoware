#pragma once
#if ENABLE_CLASSIC != 0
#include <Arduino.h>
#include <BluetoothHCI.h>
#include <MouseBLE.h>
#include <KeyboardBLE.h>
namespace Picoware
{
    class Bluetooth
    {
    public:
        Bluetooth() : hci()
        {
        }
        void begin();
        void beginBLE();
        void beginKeyboardBLE(const char *name = "Picoware Keyboard");
        void beginMouseBLE(const char *name = "Picoware Mouse");
        void keyboardPrint(const char *text);
        void moveMouse(int x, int y, int wheel = 0);
        String scan();    // search for classic Bluetooth devices
        String scanBLE(); // search for BLE devices
        void stopKeyboardBLE();
        void stopMouseBLE();

    private:
        BluetoothHCI hci; // Bluetooth HCI object for managing connections
    };
}
#endif