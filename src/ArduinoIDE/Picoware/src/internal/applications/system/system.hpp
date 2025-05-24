#pragma once
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/gui/textbox.hpp"
#include "../../../internal/system/system.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/system/about.hpp"
#include "../../../internal/applications/system/system_info.hpp"
using namespace Picoware;
static Menu *systemApp = nullptr;

static void systemStart(ViewManager *viewManager)
{
    if (systemApp != nullptr)
    {
        delete systemApp;
        systemApp = nullptr;
    }

    systemApp = new Menu(
        viewManager->getDraw(),            // draw instance
        "System",                          // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );
    systemApp->addItem("About Picoware");
    systemApp->addItem("System Info");
    systemApp->addItem("Bootloader Mode");
    systemApp->addItem("Restart Device");
    systemApp->setSelected(0);
    systemApp->draw();
}

static void systemRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        systemApp->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        systemApp->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        switch (systemApp->getSelectedIndex())
        {
        case 0: // if index is 0, show about
        {
            if (viewManager->getView("About") == nullptr)
            {
                viewManager->add(&aboutView);
            }
            viewManager->switchTo("About");
            return;
        }
        case 1: // if index is 1, show system info
        {
            if (viewManager->getView("System Info") == nullptr)
            {
                viewManager->add(&systemInfoView);
            }
            viewManager->switchTo("System Info");
            return;
        }
        case 2: // if index is 2, reboot into bootloader
        {
            System systemInfo = System();
            systemInfo.bootloaderMode();
            break;
        }
        case 3: // if index is 3, restart device
        {
            System systemInfo = System();
            systemInfo.reboot();
            break;
        }
        };
        inputManager->reset(true);
        break;
    default:
        break;
    }
}

static void systemStop(ViewManager *viewManager)
{
    if (systemApp != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            systemApp->clear();
        delete systemApp;
        systemApp = nullptr;
    }
}

const PROGMEM View systemView = View("System", systemRun, systemStart, systemStop);