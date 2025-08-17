#pragma once
#include "../../gui/menu.hpp"
#include "../../system/view.hpp"
#include "../../system/view_manager.hpp"
// #include "../../applications/applications/applications.hpp"
// #include "../../applications/bluetooth/bluetooth.hpp"
#include "../../applications/games/games.hpp"
#include "../../applications/screensavers/screensavers.hpp"
#include "../../applications/system/system.hpp"
#include "../../applications/wifi/wifi.hpp"

static Menu *library = nullptr;
static uint8_t libraryIndex = 0; // Index for the library menu
static bool libraryStart(ViewManager *viewManager)
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
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    // library->addItem("Applications");
    library->addItem("System");
#ifdef CYW43_WL_GPIO_LED_PIN
    library->addItem("WiFi");
#endif
    // if (viewManager->getBoard().hasBluetooth)
    // {
    //     library->addItem("Bluetooth");
    // }
    library->addItem("Games");
    library->addItem("Screensavers");
    library->setSelected(libraryIndex);
    library->draw();

    return true;
}

static void libraryRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
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
    case BUTTON_BACK:
        libraryIndex = 0;
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        inputManager->reset(true);
        auto currentItem = library->getCurrentItem();
        libraryIndex = library->getSelectedIndex();
        // if (strcmp(currentItem, "Applications") == 0)
        // {
        //     if (viewManager->getView("Applications") == nullptr)
        //     {
        //         viewManager->add(&applicationsView);
        //     }
        //     viewManager->switchTo("Applications");
        //     return;
        // }
        if (strcmp(currentItem, "System") == 0)
        {
            if (viewManager->getView("System") == nullptr)
            {
                viewManager->add(&systemView);
            }
            viewManager->switchTo("System");
            return;
        }
#ifdef CYW43_WL_GPIO_LED_PIN
        if (strcmp(currentItem, "WiFi") == 0)
        {
            if (viewManager->getView("WiFi") == nullptr)
            {
                viewManager->add(&wifiView);
            }
            viewManager->switchTo("WiFi");
            return;
        }
#endif
        // if (strcmp(currentItem, "Bluetooth") == 0)
        // {
        //     if (viewManager->getView("Bluetooth") == nullptr)
        //     {
        //         viewManager->add(&bluetoothView);
        //     }
        //     viewManager->switchTo("Bluetooth");
        //     return;
        // }
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
        delete library;
        library = nullptr;
    }
}

static const View libraryView = View("Library", libraryRun, libraryStart, libraryStop);