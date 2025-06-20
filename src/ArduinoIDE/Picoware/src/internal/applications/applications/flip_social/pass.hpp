#pragma once
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/applications/flip_social/utils.hpp"
using namespace Picoware;
static bool flipSocialPassIsRunning = false;
static bool flipSocialPassSaveRequested = false;

static void flipSocialPassStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        viewManager->back();
        return;
    }

    // Reset flags
    flipSocialPassIsRunning = true;
    flipSocialPassSaveRequested = false;

    // Set up save callback that just sets a flag instead of immediately calling back()
    viewManager->getKeyboard()->setSaveCallback([](const String &response)
                                                { flipSocialPassSaveRequested = true; });

    // load the ssid from flash
    viewManager->getKeyboard()->setResponse(flipSocialUtilsLoadPasswordFromFlash(viewManager));
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

const PROGMEM View flipSocialPasswordView = View("FlipSocialPassword", flipSocialPassRun, flipSocialPassStart, flipSocialPassStop);