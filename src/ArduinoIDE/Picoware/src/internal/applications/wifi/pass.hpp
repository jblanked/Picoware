#pragma once
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/wifi/utils.hpp"
using namespace Picoware;
static bool passwordIsRunning = false;
static bool passwordSaveRequested = false;

static void wifiPasswordStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        viewManager->back();
        return;
    }

    // Reset flags
    passwordIsRunning = true;
    passwordSaveRequested = false;

    // Set up save callback that just sets a flag instead of immediately calling back()
    viewManager->getKeyboard()->setSaveCallback([](const String &response)
                                                { passwordSaveRequested = true; });

    // load the password from flash
    viewManager->getKeyboard()->setResponse(loadWiFiPasswordFromFlash(viewManager));
}

static void wifiPasswordRun(ViewManager *viewManager)
{
    if (!passwordIsRunning)
    {
        return;
    }

    if (viewManager->getKeyboard() == nullptr)
    {
        passwordIsRunning = false;
        return;
    }

    // Check if save was requested
    if (passwordSaveRequested)
    {
        passwordSaveRequested = false;
        viewManager->back();
        return;
    }

    viewManager->getKeyboard()->run();
}

static void wifiPasswordStop(ViewManager *viewManager)
{
    passwordIsRunning = false;
    passwordSaveRequested = false;

    if (viewManager->getKeyboard() != nullptr)
    {
        // save the password to flash
        saveWiFiPasswordToFlash(viewManager->getStorage(), viewManager->getKeyboard()->getResponse());
        viewManager->getKeyboard()->reset();
    }
}

const PROGMEM View wifiPasswordView = View("WiFi Password", wifiPasswordRun, wifiPasswordStart, wifiPasswordStop);