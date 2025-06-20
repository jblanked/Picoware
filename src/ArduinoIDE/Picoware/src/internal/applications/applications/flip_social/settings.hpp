#pragma once
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/applications/flip_social/pass.hpp"
#include "../../../../internal/applications/applications/flip_social/user.hpp"
using namespace Picoware;
static Menu *flipSocialSettings = nullptr;
static TextBox *flipSocialSettingsTextBox = nullptr;

static void flipSocialSettingsStart(ViewManager *viewManager)
{
    if (flipSocialSettings != nullptr)
    {
        delete flipSocialSettings;
        flipSocialSettings = nullptr;
    }
    if (flipSocialSettingsTextBox != nullptr)
    {
        delete flipSocialSettingsTextBox;
        flipSocialSettingsTextBox = nullptr;
    }

    flipSocialSettings = new Menu(
        viewManager->getDraw(),            // draw instance
        "Settings",                        // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    flipSocialSettingsTextBox = new TextBox(viewManager->getDraw(), 0, viewManager->getBoard().height, viewManager->getForegroundColor(), viewManager->getBackgroundColor());

    flipSocialSettings->addItem("Change User");
    flipSocialSettings->addItem("Change Password");
    flipSocialSettings->setSelected(0);
    flipSocialSettings->draw();
}
static void flipSocialSettingsRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    static bool textBoxVisible = false;
    switch (input)
    {
    case BUTTON_UP:
        flipSocialSettings->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        flipSocialSettings->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        if (!textBoxVisible)
        {
            viewManager->back();
            inputManager->reset(true);
        }
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        inputManager->reset(true);
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
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            flipSocialSettings->clear();
        delete flipSocialSettings;
        flipSocialSettings = nullptr;
    }
    if (flipSocialSettingsTextBox != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            flipSocialSettingsTextBox->clear();
        delete flipSocialSettingsTextBox;
        flipSocialSettingsTextBox = nullptr;
    }
}

const PROGMEM View flipSocialSettingsView = View("FlipSocialSettings", flipSocialSettingsRun, flipSocialSettingsStart, flipSocialSettingsStop);