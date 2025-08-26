#pragma once
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/applications/flip_social/utils.hpp"

static bool flipSocialPassIsRunning = false;
static bool flipSocialPassSaveRequested = false;

static bool flipSocialPassStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        return false;
    }

    // Reset flags
    flipSocialPassIsRunning = true;
    flipSocialPassSaveRequested = false;

    // Set up save callback that just sets a flag instead of immediately calling back()
    viewManager->getKeyboard()->setSaveCallback([](const String &response)
                                                { flipSocialPassSaveRequested = true; });

    // load the ssid from flash
    viewManager->getKeyboard()->setResponse(flipSocialUtilsLoadPasswordFromFlash(viewManager));
    return true;
}

static void flipSocialPassRun(ViewManager *viewManager)
{
    if (!flipSocialPassIsRunning)
    {
        return;
    }

    if (viewManager->getKeyboard() == nullptr)
    {
        flipSocialPassIsRunning = false;
        return;
    }

    // Check if save was requested
    if (flipSocialPassSaveRequested)
    {
        flipSocialPassSaveRequested = false;
        viewManager->back();
        return;
    }

    viewManager->getKeyboard()->run();
}

static void flipSocialPassStop(ViewManager *viewManager)
{
    flipSocialPassIsRunning = false;
    flipSocialPassSaveRequested = false;

    if (viewManager->getKeyboard() != nullptr)
    {
        // save the ssid to flash
        flipSocialUtilsSavePasswordToFlash(viewManager, viewManager->getKeyboard()->getResponse());
        viewManager->getKeyboard()->reset();
    }
}

static const View flipSocialPasswordView = View("FlipSocialPassword", flipSocialPassRun, flipSocialPassStart, flipSocialPassStop);