#pragma once
#include "../../../gui/draw.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
// #include "../../../applications/wifi/captive_portal.hpp"
#include "../../../applications/wifi/connect.hpp"
#include "../../../applications/wifi/scan.hpp"
#include "../../../applications/wifi/settings.hpp"

static Menu *wifi = nullptr;
static uint8_t wifiIndex = 0; // Index for the WiFi menu
static bool wifiStart(ViewManager *viewManager)
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
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    wifi->addItem("Connect");
    wifi->addItem("Scan");
    // wifi->addItem("Captive Portal");
    wifi->addItem("Settings");
    wifi->setSelected(wifiIndex);
    wifi->draw();

    return true;
}

static void wifiRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_UP:
        wifi->scrollUp();
        inputManager->reset();
        break;
    case BUTTON_DOWN:
        wifi->scrollDown();
        inputManager->reset();
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        viewManager->back();
        wifiIndex = 0;
        inputManager->reset();
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        wifiIndex = wifi->getSelectedIndex();
        switch (wifiIndex)
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
        // case 2: // captive portal
        // {
        //     if (viewManager->getView("Captive Portal") == nullptr)
        //     {
        //         viewManager->add(&captivePortalView);
        //     }
        //     viewManager->switchTo("Captive Portal");
        //     break;
        // }
        case 2: // if index is 3, show settings
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
        inputManager->reset();
    }
    break;
    default:
        break;
    }
}

static void wifiStop(ViewManager *viewManager)
{
    if (wifi != nullptr)
    {
        delete wifi;
        wifi = nullptr;
    }
}

static const View wifiView = View("WiFi", wifiRun, wifiStart, wifiStop);