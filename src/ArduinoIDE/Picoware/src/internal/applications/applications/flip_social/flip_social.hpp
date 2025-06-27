#pragma once
#include "../../../../internal/boards.hpp"
#include "../../../../internal/gui/draw.hpp"
#include "../../../../internal/gui/menu.hpp"
#include "../../../../internal/system/http.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/applications/flip_social/feed.hpp"
#include "../../../../internal/applications/applications/flip_social/post.hpp"
#include "../../../../internal/applications/applications/flip_social/settings.hpp"
#include "../../../../internal/applications/applications/flip_social/utils.hpp"
using namespace Picoware;
static Alert *flipSocialAlert = nullptr;
static Menu *flipSocialMenu = nullptr;
static uint8_t flipSocialIndex = 0; // Index for the FlipSocial menu
static void flipSocialAlertAndReturn(ViewManager *viewManager, const char *message)
{
    if (flipSocialAlert)
    {
        delete flipSocialAlert;
        flipSocialAlert = nullptr;
    }
    flipSocialAlert = new Alert(viewManager->getDraw(), message, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    flipSocialAlert->draw();
    delay(2000);
}
static bool flipSocialStart(ViewManager *viewManager)
{
    if (flipSocialMenu)
    {
        delete flipSocialMenu;
        flipSocialMenu = nullptr;
    }

    auto draw = viewManager->getDraw();

    // if wifi isn't available, return
    if (!viewManager->getBoard().hasWiFi)
    {
        flipSocialAlertAndReturn(viewManager, "WiFi not available on your board.");
        return false;
    }

    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        flipSocialAlertAndReturn(viewManager, "WiFi not connected yet.");
        return false;
    }

    flipSocialMenu = new Menu(
        viewManager->getDraw(),            // draw instance
        "FlipSocial",                      // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    flipSocialMenu->addItem("Feed");
    flipSocialMenu->addItem("Post");
    flipSocialMenu->addItem("Settings");
    flipSocialMenu->setSelected(flipSocialIndex);
    flipSocialMenu->draw();
    return true;
}
static void flipSocialRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        flipSocialMenu->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        flipSocialMenu->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        flipSocialIndex = 0;
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        inputManager->reset(true);
        auto currentItem = flipSocialMenu->getCurrentItem();
        flipSocialIndex = flipSocialMenu->getSelectedIndex();
        if (strcmp(currentItem, "Feed") == 0)
        {
            if (viewManager->getView("FlipSocialFeed") == nullptr)
            {
                viewManager->add(&flipSocialFeedView);
            }
            viewManager->switchTo("FlipSocialFeed");
            return;
        }
        if (strcmp(currentItem, "Post") == 0)
        {
            if (flipSocialUtilsLoadUserFromFlash(viewManager) == "" || flipSocialUtilsLoadPasswordFromFlash(viewManager) == "")
            {
                viewManager->getDraw()->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                flipSocialAlertAndReturn(viewManager, "Please set your username and password in\nFlipSocial settings first.");
                return;
            }
            if (viewManager->getView("FlipSocialPost") == nullptr)
            {
                viewManager->add(&flipSocialPostView);
            }
            viewManager->switchTo("FlipSocialPost");
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
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            flipSocialAlert->clear();
        delete flipSocialAlert;
        flipSocialAlert = nullptr;
    }
    if (flipSocialMenu)
    {
        delete flipSocialMenu;
        flipSocialMenu = nullptr;
    }
}
const PROGMEM View flipSocialView = View("FlipSocial", flipSocialRun, flipSocialStart, flipSocialStop);