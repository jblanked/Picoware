#pragma once
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/bluetooth/bluetooth.hpp"
#include "../../../internal/applications/games/games.hpp"
#include "../../../internal/applications/screensavers/screensavers.hpp"
#include "../../../internal/applications/system/system.hpp"
#include "../../../internal/applications/wifi/wifi.hpp"
using namespace Picoware;
static Menu *library = nullptr;

static void libraryStart(ViewManager *viewManager)
{
    if (library != nullptr)
    {
        delete library;
        library = nullptr;
    }

    library = new Menu(
        viewManager->getDraw(),            // draw instance
        "Library",                         // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    library->addItem("System");
    if (viewManager->getBoard().hasWiFi)
    {
        library->addItem("WiFi");
    }
    if (viewManager->getBoard().hasBluetooth)
    {
        library->addItem("Bluetooth");
    }
    library->addItem("Games");
    library->addItem("Screensavers");
    library->setSelected(0);
    library->draw();
}

static void libraryRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        library->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        library->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        inputManager->reset(true);
        auto currentItem = library->getCurrentItem();
        if (strcmp(currentItem, "System") == 0)
        {
            if (viewManager->getView("System") == nullptr)
            {
                viewManager->add(&systemView);
            }
            viewManager->switchTo("System");
            return;
        }
        if (strcmp(currentItem, "WiFi") == 0)
        {
            if (viewManager->getView("WiFi") == nullptr)
            {
                viewManager->add(&wifiView);
            }
            viewManager->switchTo("WiFi");
            return;
        }
        if (strcmp(currentItem, "Bluetooth") == 0)
        {
            if (viewManager->getView("Bluetooth") == nullptr)
            {
                viewManager->add(&bluetoothView);
            }
            viewManager->switchTo("Bluetooth");
            return;
        }
        if (strcmp(currentItem, "Games") == 0)
        {
            if (viewManager->getView("Games") == nullptr)
            {
                viewManager->add(&gamesView);
            }
            viewManager->switchTo("Games");
            return;
        }
        if (strcmp(currentItem, "Screensavers") == 0)
        {
            if (viewManager->getView("Screensavers") == nullptr)
            {
                viewManager->add(&screensaversView);
            }
            viewManager->switchTo("Screensavers");
            return;
        }
        break;
    }
    default:
        break;
    }
}

static void libraryStop(ViewManager *viewManager)
{
    if (library != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            library->clear();
        delete library;
        library = nullptr;
    }
}

const PROGMEM View libraryView = View("Library", libraryRun, libraryStart, libraryStop);