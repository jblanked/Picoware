#pragma once
#include "../../../internal/boards.hpp"
#include "../../../internal/gui/draw.hpp"
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/system/wifi_utils.hpp"
#include "../../../internal/applications/wifi/pass.hpp"
#include "../../../internal/applications/wifi/ssid.hpp"
using namespace Picoware;
static Menu *wifiSettings = nullptr;
static TextBox *displayBox = nullptr;

static bool wifiSettingsStart(ViewManager *viewManager)
{
    if (wifiSettings != nullptr)
    {
        delete wifiSettings;
        wifiSettings = nullptr;
    }
    if (displayBox != nullptr)
    {
        delete displayBox;
        displayBox = nullptr;
    }

    wifiSettings = new Menu(
        viewManager->getDraw(),            // draw instance
        "WiFi Settings",                   // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    displayBox = new TextBox(viewManager->getDraw(), 0, viewManager->getBoard().height, viewManager->getForegroundColor(), viewManager->getBackgroundColor());

    wifiSettings->addItem("Network Info");
    wifiSettings->addItem("Change SSID");
    wifiSettings->addItem("Change Password");
    wifiSettings->setSelected(0);
    wifiSettings->draw();

    return true;
}

static void wifiSettingsRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    static bool textBoxVisible = false;
    switch (input)
    {
    case BUTTON_UP:
        wifiSettings->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        wifiSettings->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        if (!textBoxVisible)
        {
            viewManager->back();
        }
        else
        {
            displayBox->clear();
            textBoxVisible = false;
            wifiSettings->draw();
        }
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        inputManager->reset(true);
        switch (wifiSettings->getSelectedIndex())
        {
        case 0: // Network Info
        {
            String ssid = wifiUtilsLoadWiFiSSIDFromFlash(viewManager);
            String password = wifiUtilsLoadWiFiPasswordFromFlash(viewManager);
            char buffer[128];
            snprintf(buffer, sizeof(buffer), "Network Info\n\nSSID: %s\nPassword: %s", ssid.c_str(), password.c_str());
            displayBox->setText(buffer);
            textBoxVisible = true;
            break;
        }
        case 1: // Change SSID
            if (viewManager->getView("WiFi SSID") == nullptr)
            {
                viewManager->add(&wifiSSIDView);
            }
            viewManager->switchTo("WiFi SSID");
            break;
        case 2: // Change Password
            if (viewManager->getView("WiFi Password") == nullptr)
            {
                viewManager->add(&wifiPasswordView);
            }
            viewManager->switchTo("WiFi Password");
            break;
        default:
            break;
        }
    default:
        break;
    }
}

static void wifiSettingsStop(ViewManager *viewManager)
{
    if (wifiSettings != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            wifiSettings->clear();
        delete wifiSettings;
        wifiSettings = nullptr;
    }
    if (displayBox != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            displayBox->clear();
        delete displayBox;
        displayBox = nullptr;
    }
}

const PROGMEM View wifiSettingsView = View("WiFi Settings", wifiSettingsRun, wifiSettingsStart, wifiSettingsStop);