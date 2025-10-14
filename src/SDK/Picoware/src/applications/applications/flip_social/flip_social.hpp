#pragma once
#include "../../../gui/draw.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/http.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/applications/flip_social/run.hpp"
#include "../../../applications/applications/flip_social/settings.hpp"
#include "../../../applications/applications/flip_social/utils.hpp"

static Alert *flipSocialAlert = nullptr;
static Menu *flipSocialMenu = nullptr;
static uint8_t flipSocialIndex = 0; // Index for the FlipSocial menu
static void flipSocialAlertAndReturn(ViewManager *viewManager, const char *message, bool back = true)
{
    if (flipSocialAlert)
    {
        delete flipSocialAlert;
        flipSocialAlert = nullptr;
    }
    flipSocialAlert = new Alert(viewManager->getDraw(), message, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    flipSocialAlert->draw();
    delay(2000);
    if (back)
        viewManager->back();
}
static bool flipSocialStart(ViewManager *viewManager)
{
    if (flipSocialMenu)
    {
        delete flipSocialMenu;
        flipSocialMenu = nullptr;
    }

    viewManager->getStorage().createDirectory(FLIP_SOCIAL_DIRECTORY);

    auto draw = viewManager->getDraw();

    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        flipSocialAlertAndReturn(viewManager, "WiFi not connected yet.", false);
        return false;
    }

    flipSocialMenu = new Menu(
        viewManager->getDraw(),            // draw instance
        "FlipSocial",                      // title
        0,                                 // y
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    flipSocialMenu->addItem("Run");
    flipSocialMenu->addItem("Settings");
    flipSocialMenu->setSelected(flipSocialIndex);
    flipSocialMenu->draw();
    return true;
}
static void flipSocialRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_UP:
        flipSocialMenu->scrollUp();
        inputManager->reset();
        break;
    case BUTTON_DOWN:
        flipSocialMenu->scrollDown();
        inputManager->reset();
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        flipSocialIndex = 0;
        viewManager->back();
        inputManager->reset();
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        inputManager->reset();
        auto currentItem = flipSocialMenu->getCurrentItem();
        flipSocialIndex = flipSocialMenu->getSelectedIndex();
        if (strcmp(currentItem, "Run") == 0)
        {
            if (flipSocialUtilsLoadUserFromFlash(viewManager) == "" || flipSocialUtilsLoadPasswordFromFlash(viewManager) == "")
            {
                viewManager->getDraw()->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                flipSocialAlertAndReturn(viewManager, "Please set your username and password in\nFlipSocial settings first.");
                return;
            }
            if (viewManager->getView("FlipSocialRun") == nullptr)
            {
                viewManager->add(&flipSocialRunView);
            }
            viewManager->switchTo("FlipSocialRun");
            return;
        }
        if (strcmp(currentItem, "Settings") == 0)
        {
            if (viewManager->getView("FlipSocialSettings") == nullptr)
            {
                viewManager->add(&flipSocialSettingsView);
            }
            viewManager->switchTo("FlipSocialSettings");
            return;
        }
        break;
    }
    default:
        break;
    }
}
static void flipSocialStop(ViewManager *viewManager)
{
    if (flipSocialAlert)
    {
        delete flipSocialAlert;
        flipSocialAlert = nullptr;
    }
    if (flipSocialMenu)
    {
        delete flipSocialMenu;
        flipSocialMenu = nullptr;
    }
}
static const View flipSocialView = View("FlipSocial", flipSocialRun, flipSocialStart, flipSocialStop);