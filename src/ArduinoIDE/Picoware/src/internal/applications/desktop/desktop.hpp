#pragma once
#include "../../../internal/boards.hpp"
#include "../../../internal/gui/draw.hpp"
#include "../../../internal/gui/desktop.hpp"
#include "../../../internal/system/buttons.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/desktop/frames.hpp"
#include "../../../internal/applications/library/library.hpp"
#include "../../../internal/applications/system/system_info.hpp"
#include "../../../internal/applications/wifi/utils.hpp"
using namespace Picoware;
static Desktop *desktop = nullptr;
static bool isVGM = false;
static const PROGMEM uint8_t *frame_data(uint8_t index)
{
    return index == 1 ? frame_1 : index == 2 ? frame_2
                              : index == 3   ? frame_3
                                             : frame_4;
}

static bool desktopStart(ViewManager *viewManager)
{
    // Clean up any existing desktop instance
    if (desktop != nullptr)
    {
        delete desktop;
        desktop = nullptr;
    }

    desktop = new Desktop(viewManager->getDraw(), viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    auto board = viewManager->getBoard();
    isVGM = board.boardType == BOARD_TYPE_VGM;

    wifiUtilsConnectToSavedWiFi(viewManager);

    return true;
}

static void desktopRun(ViewManager *viewManager)
{
    static bool systemInfoLoading = false;
    // Handle input
    auto input = viewManager->getInputManager()->getInput();
    switch (input)
    {
    case BUTTON_LEFT:
        if (!systemInfoLoading)
        {
            systemInfoLoading = true;
            viewManager->getInputManager()->reset();
            if (viewManager->getView("System Info") == nullptr)
            {
                viewManager->add(&systemInfoView);
            }
            viewManager->switchTo("System Info");
        }
        return;
    case BUTTON_CENTER:
    case BUTTON_UP:
        viewManager->getInputManager()->reset();
        if (viewManager->getView("Library") == nullptr)
        {
            viewManager->add(&libraryView);
        }
        viewManager->switchTo("Library");
        return;
    default:
        break;
    }

    static uint8_t next_frame = 1;
    static uint8_t max_frame = 4;
    static uint8_t direction = 1;
    static int elapsed = 0;

    if (!isVGM && elapsed > 2500 || elapsed > 250000)
    {
        systemInfoLoading = false;
        elapsed = 0;

        desktop->setTime(viewManager->getTime());
        desktop->draw(frame_data(next_frame), Vector(320, 240));

        // Update frame counter
        next_frame += direction;
        if (next_frame == max_frame)
        {
            direction = -1;
        }
        if (next_frame == 1)
        {
            direction = 1;
        }
    }
    elapsed++;

    desktop->setTextColor(viewManager->getForegroundColor());
    desktop->setBackgroundColor(viewManager->getBackgroundColor());
}

static void desktopStop(ViewManager *viewManager)
{
    // Clean up desktop instance
    if (desktop != nullptr)
    {
        if (isVGM)
            desktop->clear();
        delete desktop;
        desktop = nullptr;
    }
}

const PROGMEM View desktopView = View("Desktop", desktopRun, desktopStart, desktopStop);