#pragma once
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/gui/textbox.hpp"
#include "../../../internal/system/system.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/system/about.hpp"
#include "../../../internal/applications/system/settings.hpp"
#include "../../../internal/applications/system/system_info.hpp"
using namespace Picoware;
static Menu *systemApp = nullptr;
static uint8_t systemIndex = 0; // Index for the system menu
static bool systemStart(ViewManager *viewManager)
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
    systemApp->addItem("Settings");
    systemApp->addItem("About Picoware");
    systemApp->addItem("System Info");
    systemApp->addItem("Bootloader Mode");
    systemApp->addItem("Restart Device");
    systemApp->setSelected(systemIndex);
    systemApp->draw();
    return true;
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
    case BUTTON_BACK:
        systemIndex = 0;
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        const char *currentItem = systemApp->getCurrentItem();
        if (strcmp(currentItem, "Settings") == 0)
        {
            if (viewManager->getView("Settings") == nullptr)
            {
                viewManager->add(&settingsView);
            }
            viewManager->switchTo("Settings");
        }
        else if (strcmp(currentItem, "About") == 0)
        {
            if (viewManager->getView("About") == nullptr)
            {
                viewManager->add(&aboutView);
            }
            viewManager->switchTo("About");
        }
        else if (strcmp(currentItem, "System Info") == 0)
        {
            if (viewManager->getView("System Info") == nullptr)
            {
                viewManager->add(&systemInfoView);
            }
            viewManager->switchTo("System Info");
        }
        else if (strcmp(currentItem, "Bootloader Mode") == 0)
        {
            System systemInfo = System();
            systemInfo.bootloaderMode();
        }
        else if (strcmp(currentItem, "Restart Device") == 0)
        {
            System systemInfo = System();
            systemInfo.reboot();
        }
        inputManager->reset(true);
        break;
    }
    default:
        break;
    };
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