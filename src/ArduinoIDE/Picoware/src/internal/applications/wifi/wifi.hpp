#pragma once
#include "../../../internal/boards.hpp"
#include "../../../internal/gui/draw.hpp"
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/wifi/captive_portal.hpp"
#include "../../../internal/applications/wifi/connect.hpp"
#include "../../../internal/applications/wifi/scan.hpp"
#include "../../../internal/applications/wifi/settings.hpp"
using namespace Picoware;
static Menu *wifi = nullptr;

static void wifiStart(ViewManager *viewManager)
{
    if (wifi != nullptr)
    {
        delete wifi;
        wifi = nullptr;
    }

    wifi = new Menu(
        viewManager->getDraw(),            // draw instance
        "WiFi",                            // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    wifi->addItem("Connect");
    wifi->addItem("Scan");
    wifi->addItem("Captive Portal");
    wifi->addItem("Settings");
    wifi->setSelected(0);
    wifi->draw();
}

static void wifiRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        wifi->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        wifi->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        switch (wifi->getSelectedIndex())
        {
        case 0: // if index is 0, show connect
        {
            if (viewManager->getView("WiFi Connect") == nullptr)
            {
                viewManager->add(&wifiConnectView);
            }
            viewManager->switchTo("WiFi Connect");
            break;
        }
        case 1: // if index is 1, show scan
        {
            if (viewManager->getView("WiFi Scan") == nullptr)
            {
                viewManager->add(&wifiScanView);
            }
            viewManager->switchTo("WiFi Scan");
            break;
        }
        case 2: // captive portal
        {
            if (viewManager->getView("Captive Portal") == nullptr)
            {
                viewManager->add(&captivePortalView);
            }
            viewManager->switchTo("Captive Portal");
            break;
        }
        case 3: // if index is 3, show settings
        {
            if (viewManager->getView("WiFi Settings") == nullptr)
            {
                viewManager->add(&wifiSettingsView);
            }
            viewManager->switchTo("WiFi Settings");
            break;
        }
        default:
            break;
        }
        inputManager->reset(true);
    default:
        break;
    }
}

static void wifiStop(ViewManager *viewManager)
{
    if (wifi != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            wifi->clear();
        delete wifi;
        wifi = nullptr;
    }
}

const PROGMEM View wifiView = View("WiFi", wifiRun, wifiStart, wifiStop);