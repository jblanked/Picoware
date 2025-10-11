#pragma once
#include "../../gui/menu.hpp"
#include "../../gui/textbox.hpp"
#include "../../system/system.hpp"
#include "../../system/view.hpp"
#include "../../system/view_manager.hpp"
#include "../../applications/system/about.hpp"
#include "../../applications/system/system_info.hpp"

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
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );
    // systemApp->addItem("Settings");
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
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_UP:
        systemApp->scrollUp();
        inputManager->reset();
        break;
    case BUTTON_DOWN:
        systemApp->scrollDown();
        inputManager->reset();
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        systemIndex = 0;
        viewManager->back();
        inputManager->reset();
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        const char *currentItem = systemApp->getCurrentItem();
        if (strcmp(currentItem, "About Picoware") == 0)
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
        inputManager->reset();
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
        delete systemApp;
        systemApp = nullptr;
    }
}

static const View systemView = View("System", systemRun, systemStart, systemStop);