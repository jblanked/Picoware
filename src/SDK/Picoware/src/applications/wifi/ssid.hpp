#pragma once
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/wifi/utils.hpp"

static bool ssidIsRunning = false;
static bool ssidSaveRequested = false;

static bool wifiSSIDStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        return false;
    }

    // Reset flags
    ssidIsRunning = true;
    ssidSaveRequested = false;

    // Set up save callback that just sets a flag instead of immediately calling back()
    viewManager->getKeyboard()->setSaveCallback([](const std::string &response)
                                                { ssidSaveRequested = true; });

    // load the ssid from flash
    viewManager->getKeyboard()->setResponse(wifiUtilsLoadWiFiSSIDFromFlash(viewManager));

    return true;
}

static void wifiSSIDRun(ViewManager *viewManager)
{
    if (!ssidIsRunning)
    {
        return;
    }

    if (viewManager->getKeyboard() == nullptr)
    {
        ssidIsRunning = false;
        return;
    }

    // Check if save was requested
    if (ssidSaveRequested)
    {
        ssidSaveRequested = false;
        viewManager->back();
        return;
    }

    viewManager->getKeyboard()->run();
}

static void wifiSSIDStop(ViewManager *viewManager)
{
    ssidIsRunning = false;
    ssidSaveRequested = false;

    if (viewManager->getKeyboard() != nullptr)
    {
        // save the ssid to flash
        wifiUtilsSaveWiFiSSIDToFlash(viewManager->getStorage(), viewManager->getKeyboard()->getResponse());
        viewManager->getKeyboard()->reset();
    }
}

static const View wifiSSIDView = View("WiFi SSID", wifiSSIDRun, wifiSSIDStart, wifiSSIDStop);