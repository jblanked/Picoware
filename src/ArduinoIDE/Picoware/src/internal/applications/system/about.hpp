#pragma once
#include "../../../internal/gui/textbox.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
using namespace Picoware;
static TextBox *aboutBox = nullptr;
static const String aboutText()
{
    String text;
    text += "Picoware\n\n";
    text += "A custom firmware for the PicoCalc, Video Game Module, and other Raspberry Pi Pico devices, originally created by JBlanked on 2025-05-13.\n\n";
    text += "This firmware was made with Arduino IDE/C++ and is open source on GitHub. Developers are welcome\nto contribute.\n\n";
    text += "Picoware is a work in progress and is not yet complete. Some features may not work as\nexpected. Picoware is not affiliated with ClockworkPI, the Raspberry Pi Foundation, or any other organization.\n\n";
    text += "Discord: https://discord.gg/5aN9qwkEc6\n";
    text += "GitHub: https://www.github.com/jblanked/Picoware\n";
    text += "Instagram: @jblanked";
    return text;
}
static bool aboutStart(ViewManager *viewManager)
{
    if (aboutBox != nullptr)
    {
        delete aboutBox;
        aboutBox = nullptr;
    }
    aboutBox = new TextBox(viewManager->getDraw(), 0, viewManager->getBoard().height, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    aboutBox->setText(aboutText().c_str());
    return true;
}
static void aboutRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto index = inputManager->getInput();
    switch (index)
    {
    case BUTTON_LEFT:
    {
        viewManager->back();
        inputManager->reset();
        return;
    }
    case BUTTON_DOWN:
    {
        aboutBox->scrollDown();
        inputManager->reset(true);
        break;
    }
    case BUTTON_UP:
    {
        aboutBox->scrollUp();
        inputManager->reset(true);
        break;
    }
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        aboutBox->setText(aboutText().c_str());
        inputManager->reset(true);
        break;
    }
    default:
        break;
    }
}
static void aboutStop(ViewManager *viewManager)
{
    if (aboutBox != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            aboutBox->clear();
        delete aboutBox;
        aboutBox = nullptr;
    }
}

const PROGMEM View aboutView = View("About", aboutRun, aboutStart, aboutStop);