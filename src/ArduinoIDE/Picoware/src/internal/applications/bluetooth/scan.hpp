#pragma once
#include "../../../internal/gui/alert.hpp"
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/system.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/system/bluetooth.hpp"
#if ENABLE_CLASSIC != 0
using namespace Picoware;
static Menu *bluetoothScan = nullptr;
static Alert *bluetoothScanAlert = nullptr;
static Bluetooth *bluetoothScanner = nullptr;
static void scan_restart()
{
    // we currently need to restart the system to reset the Bluetooth state fully
    // this will be implemented in the Bluetooth class in the future
    System systemInfo = System();
    systemInfo.reboot();
}
static bool bluetoothScanStart(ViewManager *viewManager)
{
    if (bluetoothScan != nullptr)
    {
        delete bluetoothScan;
        bluetoothScan = nullptr;
    }
    if (bluetoothScanAlert != nullptr)
    {
        delete bluetoothScanAlert;
        bluetoothScanAlert = nullptr;
    }
    if (bluetoothScanner != nullptr)
    {
        delete bluetoothScanner;
        bluetoothScanner = nullptr;
    }

    auto draw = viewManager->getDraw();

    // if bluetooth isn't available, return
    if (!viewManager->getBoard().hasBluetooth)
    {
        bluetoothScanAlert = new Alert(draw, "Bluetooth not available on your board.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        bluetoothScanAlert->draw();
        delay(2000);
        return false;
    }

    auto LED = viewManager->getLED();

    draw->text(Vector(5, 5), "Scanning...");
    draw->swap();

    bluetoothScanner = new Bluetooth();
    bluetoothScanner->begin();
    LED.on();
    auto devices = bluetoothScanner->scan();
    LED.off();

    bluetoothScan = new Menu(
        viewManager->getDraw(),            // draw instance
        "Bluetooth Scan",                  // title
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
        bluetoothScanAlert = new Alert(draw, "Error parsing Bluetooth scan results.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        bluetoothScanAlert->draw();
        delay(3000);
        // viewManager->back();
        scan_restart();
        return false;
    }
    auto bluetoothScanResults = doc["devices"].as<JsonArray>();
    int bluetoothScanCount = bluetoothScanResults.size();
    if (bluetoothScanCount == 0)
    {
        bluetoothScanAlert = new Alert(draw, "No Bluetooth devices found.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        bluetoothScanAlert->draw();
        delay(3000);
        // viewManager->back();
        scan_restart();
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
                bluetoothScan->addItem(deviceName);
            }
        }
    }
    bluetoothScan->setSelected(0);
    bluetoothScan->draw();

    return true;
}

static void bluetoothScanRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        bluetoothScan->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        bluetoothScan->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
        switch (bluetoothScan->getSelectedIndex())
        {
            // maybe we can connect to the selected device?
            // send to the loading view, then connect
        }
        inputManager->reset(true);
    default:
        break;
    }
}

static void bluetoothScanStop(ViewManager *viewManager)
{
    if (bluetoothScan != nullptr)
    {
        delete bluetoothScan;
        bluetoothScan = nullptr;
    }
    if (bluetoothScanAlert != nullptr)
    {
        delete bluetoothScanAlert;
        bluetoothScanAlert = nullptr;
    }
    if (bluetoothScanner != nullptr)
    {
        delete bluetoothScanner;
        bluetoothScanner = nullptr;
    }

    scan_restart();
}

const PROGMEM View bluetoothClassicScanView = View("Bluetooth Classic Scan", bluetoothScanRun, bluetoothScanStart, bluetoothScanStop);
#endif // ENABLE_CLASSIC != 0