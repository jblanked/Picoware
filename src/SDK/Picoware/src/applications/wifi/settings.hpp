#pragma once
#include "../../../gui/draw.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../system/wifi.hpp"
#include "../../../applications/wifi/pass.hpp"
#include "../../../applications/wifi/ssid.hpp"

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
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    displayBox = new TextBox(viewManager->getDraw(), 0, 320, viewManager->getForegroundColor(), viewManager->getBackgroundColor());

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
    auto input = inputManager->getLastButton();
    static bool textBoxVisible = false;
    switch (input)
    {
    case BUTTON_UP:
        wifiSettings->scrollUp();
        inputManager->reset();
        break;
    case BUTTON_DOWN:
        wifiSettings->scrollDown();
        inputManager->reset();
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
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
        inputManager->reset();
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        inputManager->reset();
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
        delete wifiSettings;
        wifiSettings = nullptr;
    }
    if (displayBox != nullptr)
    {
        delete displayBox;
        displayBox = nullptr;
    }
}

static const View wifiSettingsView = View("WiFi Settings", wifiSettingsRun, wifiSettingsStart, wifiSettingsStop);