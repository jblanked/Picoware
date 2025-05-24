#pragma once
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/wifi/utils.hpp"
using namespace Picoware;
static bool ssidIsRunning = false;
static bool ssidSaveRequested = false;

static void wifiSSIDStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        viewManager->back();
        return;
    }

    // Reset flags
    ssidIsRunning = true;
    ssidSaveRequested = false;

    // Set up save callback that just sets a flag instead of immediately calling back()
    viewManager->getKeyboard()->setSaveCallback([](const String &response)
                                                { ssidSaveRequested = true; });

    // load the ssid from flash
    viewManager->getKeyboard()->setResponse(loadWiFiSSIDFromFlash(viewManager));
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
        saveWiFiSSIDToFlash(viewManager->getStorage(), viewManager->getKeyboard()->getResponse());
        viewManager->getKeyboard()->reset();
    }
}

const PROGMEM View wifiSSIDView = View("WiFi SSID", wifiSSIDRun, wifiSSIDStart, wifiSSIDStop);