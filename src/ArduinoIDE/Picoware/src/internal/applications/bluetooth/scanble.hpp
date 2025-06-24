#pragma once
#include "../../../internal/gui/alert.hpp"
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/system.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/system/bluetooth.hpp"
#if ENABLE_CLASSIC != 0
using namespace Picoware;
static Menu *bluetoothScanBLE = nullptr;
static Alert *bluetoothScanBLEAlert = nullptr;
static Bluetooth *bluetoothScannerBLE = nullptr;
static void scanBLErestart()
{
    // we currently need to restart the system to reset the Bluetooth state fully
    // this will be implemented in the Bluetooth class in the future
    System systemInfo = System();
    systemInfo.reboot();
}
static bool bluetoothScanBLEStart(ViewManager *viewManager)
{
    if (bluetoothScanBLE != nullptr)
    {
        delete bluetoothScanBLE;
        bluetoothScanBLE = nullptr;
    }
    if (bluetoothScanBLEAlert != nullptr)
    {
        delete bluetoothScanBLEAlert;
        bluetoothScanBLEAlert = nullptr;
    }
    if (bluetoothScannerBLE != nullptr)
    {
        delete bluetoothScannerBLE;
        bluetoothScannerBLE = nullptr;
    }

    auto draw = viewManager->getDraw();

    // if bluetooth isn't available, return
    if (!viewManager->getBoard().hasBluetooth)
    {
        bluetoothScanBLEAlert = new Alert(draw, "Bluetooth not available on your board.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        bluetoothScanBLEAlert->draw();
        delay(2000);
        return false;
    }

    auto LED = viewManager->getLED();

    draw->text(Vector(5, 5), "Scanning...");
    draw->swap();

    bluetoothScannerBLE = new Bluetooth();
    bluetoothScannerBLE->beginBLE();
    LED.on();
    auto devices = bluetoothScannerBLE->scanBLE();
    LED.off();

    bluetoothScanBLE = new Menu(
        viewManager->getDraw(),            // draw instance
        "Bluetooth Scan BLE",              // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    JsonDocument doc;
    auto err = deserializeJson(doc, devices);
    if (err)
    {
        bluetoothScanBLEAlert = new Alert(draw, "Error parsing Bluetooth scan results.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        bluetoothScanBLEAlert->draw();
        delay(3000);
        // viewManager->back();
        scanBLErestart();
        return false;
    }
    auto bluetoothScanResults = doc["devices"].as<JsonArray>();
    int bluetoothScanCount = bluetoothScanResults.size();
    if (bluetoothScanCount == 0)
    {
        bluetoothScanBLEAlert = new Alert(draw, "No Bluetooth devices found.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        bluetoothScanBLEAlert->draw();
        delay(3000);
        // viewManager->back();
        scanBLErestart();
        return false;
    }
    for (int i = 0; i < bluetoothScanCount; i++)
    {
        JsonVariant device = bluetoothScanResults[i];
        if (!device.isNull())
        {
            const char *deviceName = device.as<const char *>();
            if (deviceName != nullptr && strlen(deviceName) > 0)
            {
                bluetoothScanBLE->addItem(deviceName);
            }
        }
    }
    bluetoothScanBLE->setSelected(0);
    bluetoothScanBLE->draw();
    return true;
}

static void bluetoothScanBLERun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        bluetoothScanBLE->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        bluetoothScanBLE->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
        switch (bluetoothScanBLE->getSelectedIndex())
        {
            // maybe we can connect to the selected device?
            // send to the loading view, then connect
        }
        inputManager->reset(true);
    default:
        break;
    }
}

static void bluetoothScanBLEStop(ViewManager *viewManager)
{
    if (bluetoothScanBLE != nullptr)
    {
        delete bluetoothScanBLE;
        bluetoothScanBLE = nullptr;
    }
    if (bluetoothScanBLEAlert != nullptr)
    {
        delete bluetoothScanBLEAlert;
        bluetoothScanBLEAlert = nullptr;
    }
    if (bluetoothScannerBLE != nullptr)
    {
        delete bluetoothScannerBLE;
        bluetoothScannerBLE = nullptr;
    }
    scanBLErestart();
}

const PROGMEM View bluetoothBLEScanView = View("Bluetooth BLE Scan", bluetoothScanBLERun, bluetoothScanBLEStart, bluetoothScanBLEStop);
#endif // ENABLE_CLASSIC != 0