#pragma once
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/applications/flip_social/utils.hpp"
#include "../../../../internal/applications/system/system_info.hpp"
using namespace Picoware;
static Alert *flipSocialPostAlert = nullptr;
static bool flipSocialPostIsRunning = false;
static bool flipSocialPostSaveRequested = false;
static void flipSocialPostAlertAndReturn(ViewManager *viewManager, const char *message)
{
    if (flipSocialPostAlert)
    {
        delete flipSocialPostAlert;
        flipSocialPostAlert = nullptr;
    }
    viewManager->getDraw()->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
    flipSocialPostAlert = new Alert(viewManager->getDraw(), message, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    flipSocialPostAlert->draw();
    delay(2000);
    // viewManager->back();
    // just reboot, not sure what's up with back in this view...
    System systemInfo = System();
    systemInfo.reboot();
}
static void flipSocialPostStart(ViewManager *viewManager)
{
    if (viewManager->getKeyboard() == nullptr)
    {
        viewManager->back();
        return;
    }

    // Reset flags
    flipSocialPostIsRunning = true;
    flipSocialPostSaveRequested = false;
    viewManager->getKeyboard()->setSaveCallback([](const String &response)
                                                { flipSocialPostSaveRequested = true; });
}

static void flipSocialPostRun(ViewManager *viewManager)
{
    if (!flipSocialPostIsRunning)
    {
        return;
    }

    if (viewManager->getKeyboard() == nullptr)
    {
        flipSocialPostIsRunning = false;
        return;
    }

    // Check if save was requested
    if (flipSocialPostSaveRequested)
    {
        flipSocialPostSaveRequested = false;
        viewManager->back();
        return;
    }

    viewManager->getKeyboard()->run();
}

static void flipSocialPostStop(ViewManager *viewManager)
{
    flipSocialPostIsRunning = false;
    flipSocialPostSaveRequested = false;

    if (viewManager->getKeyboard() != nullptr)
    {
        // clear the screen and show posting message
        viewManager->getDraw()->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        viewManager->getDraw()->text(Vector(5, 5), "Posting to FlipSocial...", viewManager->getForegroundColor());
        viewManager->getDraw()->swap();

        // get user and response from keyboard
        String user = flipSocialUtilsLoadUserFromFlash(viewManager);
        String content = viewManager->getKeyboard()->getResponse();

        if (user.length() == 0 || content.length() == 0)
        {
            flipSocialPostAlertAndReturn(viewManager, "Username or content cannot be empty.");
            return;
        }

        // setup command
        char command[256];
        snprintf(command, sizeof(command), "{\"username\":\"%s\",\"content\":\"%s\"}", user.c_str(), content.c_str());

        // send post request and wait for response
        String response = flipSocialHttpRequest(viewManager, "POST", "https://www.jblanked.com/flipper/api/feed/post/", command);

        // reset
        viewManager->getKeyboard()->reset();

        // check response (empty or ERROR in response)
        if (response.length() == 0 || response.indexOf("ERROR") != -1)
        {
            // if response is empty or null, show alert and return
            // this may freeze if called but we shouldn't get here anyways from all the checks above and in flip_social.hpp
            // we could just show the message and restart the device until we fix the issue
            flipSocialPostAlertAndReturn(viewManager, "Failed to post. Please try again.");
            return;
        }

        // in the flipper app, we automatically send the user back to the feed
        // but for now we'll just return to the main menu
        // when feed implementation is ready, we can switch using viewManager->switchTo("FlipSocialFeed");
    }

    if (flipSocialPostAlert)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            flipSocialPostAlert->clear();
        delete flipSocialPostAlert;
        flipSocialPostAlert = nullptr;
    }
}

const PROGMEM View flipSocialPostView = View("FlipSocialPost", flipSocialPostRun, flipSocialPostStart, flipSocialPostStop);