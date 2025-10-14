#pragma once
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/wifi/utils.hpp"

static bool passwordIsRunning = false;
static bool passwordSaveRequested = false;

static bool wifiPasswordStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        return false;
    }

    // Reset flags
    passwordIsRunning = true;
    passwordSaveRequested = false;

    // Set up save callback that just sets a flag instead of immediately calling back()
    viewManager->getKeyboard()->setSaveCallback([](const std::string &response)
                                                { passwordSaveRequested = true; });

    // load the password from flash
    viewManager->getKeyboard()->setResponse(wifiUtilsLoadWiFiPasswordFromFlash(viewManager));
    return true;
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

    auto input = viewManager->getInputManager();

    // Check if save was requested
    if (passwordSaveRequested || input->getLastButton() == BUTTON_BACK)
    {
        passwordSaveRequested = false;
        input->reset();
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
        wifiUtilsSaveWiFiPasswordToFlash(viewManager->getStorage(), viewManager->getKeyboard()->getResponse());
        viewManager->getKeyboard()->reset();
    }
}

static const View wifiPasswordView = View("WiFi Password", wifiPasswordRun, wifiPasswordStart, wifiPasswordStop);