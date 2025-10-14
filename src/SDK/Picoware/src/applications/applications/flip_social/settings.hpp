#pragma once
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../gui/menu.hpp"
#include "../../../gui/textbox.hpp"
#include "../../../applications/applications/flip_social/pass.hpp"
#include "../../../applications/applications/flip_social/user.hpp"

static Menu *flipSocialSettings = nullptr;

static bool flipSocialSettingsStart(ViewManager *viewManager)
{
    if (flipSocialSettings != nullptr)
    {
        delete flipSocialSettings;
        flipSocialSettings = nullptr;
    }

    flipSocialSettings = new Menu(
        viewManager->getDraw(),            // draw instance
        "Settings",                        // title
        0,                                 // y
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    flipSocialSettings->addItem("Change User");
    flipSocialSettings->addItem("Change Password");
    flipSocialSettings->setSelected(0);
    flipSocialSettings->draw();
    return true;
}
static void flipSocialSettingsRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_UP:
        flipSocialSettings->scrollUp();
        inputManager->reset();
        break;
    case BUTTON_DOWN:
        flipSocialSettings->scrollDown();
        inputManager->reset();
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        viewManager->back();
        inputManager->reset();
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        inputManager->reset();
        switch (flipSocialSettings->getSelectedIndex())
        {
        case 0: // Change User
            if (viewManager->getView("FlipSocialUser") == nullptr)
            {
                viewManager->add(&flipSocialUserView);
            }
            viewManager->switchTo("FlipSocialUser");
            break;
        case 1: // Change Password
            if (viewManager->getView("FlipSocialPassword") == nullptr)
            {
                viewManager->add(&flipSocialPasswordView);
            }
            viewManager->switchTo("FlipSocialPassword");
            break;
        default:
            break;
        }
        break;
    default:
        break;
    }
}
static void flipSocialSettingsStop(ViewManager *viewManager)
{
    if (flipSocialSettings != nullptr)
    {
        delete flipSocialSettings;
        flipSocialSettings = nullptr;
    }
}

static const View flipSocialSettingsView = View("FlipSocialSettings", flipSocialSettingsRun, flipSocialSettingsStart, flipSocialSettingsStop);