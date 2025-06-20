#pragma once
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/applications/flip_social/utils.hpp"
using namespace Picoware;
static bool flipSocialUserIsRunning = false;
static bool flipSocialUserSaveRequested = false;

static void flipSocialUserStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        viewManager->back();
        return;
    }

    // Reset flags
    flipSocialUserIsRunning = true;
    flipSocialUserSaveRequested = false;

    // Set up save callback that just sets a flag instead of immediately calling back()
    viewManager->getKeyboard()->setSaveCallback([](const String &response)
                                                { flipSocialUserSaveRequested = true; });

    // load the ssid from flash
    viewManager->getKeyboard()->setResponse(flipSocialUtilsLoadUserFromFlash(viewManager));
}

static void flipSocialUserRun(ViewManager *viewManager)
{
    if (!flipSocialUserIsRunning)
    {
        return;
    }

    if (viewManager->getKeyboard() == nullptr)
    {
        flipSocialUserIsRunning = false;
        return;
    }

    // Check if save was requested
    if (flipSocialUserSaveRequested)
    {
        flipSocialUserSaveRequested = false;
        viewManager->back();
        return;
    }

    viewManager->getKeyboard()->run();
}

static void flipSocialUserStop(ViewManager *viewManager)
{
    flipSocialUserIsRunning = false;
    flipSocialUserSaveRequested = false;

    if (viewManager->getKeyboard() != nullptr)
    {
        // save the ssid to flash
        flipSocialUtilsSaveUserToFlash(viewManager, viewManager->getKeyboard()->getResponse());
        viewManager->getKeyboard()->reset();
    }
}

const PROGMEM View flipSocialUserView = View("FlipSocialUser", flipSocialUserRun, flipSocialUserStart, flipSocialUserStop);