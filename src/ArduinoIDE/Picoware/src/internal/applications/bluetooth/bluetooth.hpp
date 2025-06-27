#pragma once
#include "../../../internal/boards.hpp"
#include "../../../internal/gui/draw.hpp"
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/bluetooth/keyboard.hpp"
#include "../../../internal/applications/bluetooth/mouse.hpp"
#include "../../../internal/applications/bluetooth/scan.hpp"
#include "../../../internal/applications/bluetooth/scanble.hpp"
using namespace Picoware;
static Menu *bluetooth = nullptr;
static uint8_t bluetoothIndex = 0; // Index for the Bluetooth menu
static bool bluetoothStart(ViewManager *viewManager)
{
    if (bluetooth != nullptr)
    {
        delete bluetooth;
        bluetooth = nullptr;
    }

    bluetooth = new Menu(
        viewManager->getDraw(),            // draw instance
        "Bluetooth",                       // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    bluetooth->addItem("Classic Scan");
    bluetooth->addItem("BLE Scan");
    bluetooth->addItem("BLE Keyboard");
    bluetooth->addItem("BLE Mouse");
    bluetooth->setSelected(bluetoothIndex);
    bluetooth->draw();
    return true;
}

static void bluetoothRun(ViewManager *viewManager)
{
#if ENABLE_CLASSIC != 0
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        bluetooth->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        bluetooth->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        bluetoothIndex = 0;
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        bluetoothIndex = bluetooth->getSelectedIndex();
        switch (bluetoothIndex)
        {
        case 0: // if index is 0, show classic scan
        {
            if (viewManager->getView("Bluetooth Classic Scan") == nullptr)
            {
                viewManager->add(&bluetoothClassicScanView);
            }
            viewManager->switchTo("Bluetooth Classic Scan");
            break;
        }
        case 1: // if index is 1, show BLE scan
        {
            if (viewManager->getView("Bluetooth BLE Scan") == nullptr)
            {
                viewManager->add(&bluetoothBLEScanView);
            }
            viewManager->switchTo("Bluetooth BLE Scan");
            break;
        }
        case 2: // if index is 2, show keyboard
        {
            if (viewManager->getView("Bluetooth BLE Keyboard") == nullptr)
            {
                viewManager->add(&bluetoothKeyboardView);
            }
            viewManager->switchTo("Bluetooth BLE Keyboard");
            break;
        }
        case 3: // if index is 3, show mouse
        {
            if (viewManager->getView("Bluetooth BLE Mouse") == nullptr)
            {
                viewManager->add(&bluetoothMouseView);
            }
            viewManager->switchTo("Bluetooth BLE Mouse");
            break;
        }
        default:
            break;
        };
        inputManager->reset(true);
    }
    break;
    default:
        break;
    }
#endif // ENABLE_CLASSIC != 0
}

static void bluetoothStop(ViewManager *viewManager)
{
    if (bluetooth != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            bluetooth->clear();
        delete bluetooth;
        bluetooth = nullptr;
    }
}

const PROGMEM View bluetoothView = View("Bluetooth", bluetoothRun, bluetoothStart, bluetoothStop);