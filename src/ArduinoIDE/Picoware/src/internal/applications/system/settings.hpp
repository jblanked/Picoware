#pragma once
#include <ArduinoJson.h>
#include "../../../internal/gui/toggle.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
// #define GMT_OFFSET_LOCATION "/gmt_offset.json"
using namespace Picoware;
Toggle *darkModeToggle = nullptr;
uint8_t selectedToggleIndex = 0; // Index for the toggle in settings
static bool settingsStart(ViewManager *viewManager)
{
    if (darkModeToggle != nullptr)
    {
        delete darkModeToggle;
        darkModeToggle = nullptr;
    }
    darkModeToggle = new Toggle(
        viewManager->getDraw(),                    // draw instance
        Vector(10, 10),                            // position
        Vector(viewManager->getSize().x - 20, 30), // size
        "Dark Mode",                               // text
        false,                                     // initial state
        viewManager->getForegroundColor(),         // foreground color
        viewManager->getBackgroundColor(),         // background color
        TFT_BLUE,                                  // on color
        viewManager->getForegroundColor(),         // border color
        2                                          // border width
    );
    JsonDocument doc;
    auto storage = viewManager->getStorage();
    if (storage.deserialize(doc, DARK_MODE_LOCATION))
    {
        darkModeToggle->setState(doc["dark_mode"]);
    }
    return true;
}

static void settingsRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto index = inputManager->getInput();
    switch (index)
    {
    case BUTTON_CENTER:
    {
        if (darkModeToggle)
        {
            darkModeToggle->toggle();

            // Save the state to flash
            JsonDocument doc;
            doc["dark_mode"] = darkModeToggle->getState();
            auto storage = viewManager->getStorage();
            storage.serialize(doc, DARK_MODE_LOCATION);

            // Update the background color based on the toggle state
            // we should probably move this to the ViewManager..
            if (darkModeToggle->getState())
            {
                viewManager->setBackgroundColor(TFT_BLACK);
                viewManager->setForegroundColor(TFT_WHITE);
            }
            else
            {
                viewManager->setBackgroundColor(TFT_WHITE);
                viewManager->setForegroundColor(TFT_BLACK);
            }
        }
        inputManager->reset(true);
        break;
    }
    case BUTTON_UP:
        // up to the previous toggle
        if (selectedToggleIndex > 0)
        {
            selectedToggleIndex--;
        }
        break;
    case BUTTON_DOWN:
        // down to the next toggle
        if (selectedToggleIndex < 1)
        {
            selectedToggleIndex++;
        }
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
    {
        viewManager->back();
        inputManager->reset(true);
        return;
    }
    default:
        break;
    }

    if (darkModeToggle != nullptr)
    {
        darkModeToggle->draw();
    }
}

static void settingsStop(ViewManager *viewManager)
{
    if (darkModeToggle != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            darkModeToggle->clear();
        delete darkModeToggle;
        darkModeToggle = nullptr;
    }
}

const PROGMEM View settingsView = View("Settings", settingsRun, settingsStart, settingsStop);