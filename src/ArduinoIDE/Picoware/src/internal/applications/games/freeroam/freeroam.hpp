#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/freeroam/game.hpp"
std::unique_ptr<FreeRoamGame> game;
static Alert *freeRoamAlert = nullptr;
static void freeRoamAlertAndReturn(ViewManager *viewManager, const char *message)
{
    if (freeRoamAlert)
    {
        delete freeRoamAlert;
        freeRoamAlert = nullptr;
    }
    freeRoamAlert = new Alert(viewManager->getDraw(), message, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    freeRoamAlert->draw();
    delay(2000);
}
static bool freeRoamStart(ViewManager *viewManager)
{
    // if wifi isn't available, return
    if (!viewManager->getBoard().hasWiFi)
    {
        freeRoamAlertAndReturn(viewManager, "WiFi not available on your board.");
        return false;
    }

    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        freeRoamAlertAndReturn(viewManager, "WiFi not connected yet.");
        return false;
    }

    game = std::make_unique<FreeRoamGame>(viewManager);
    return true;
}

static void freeRoamRun(ViewManager *viewManager)
{
    auto input = viewManager->getInputManager()->getInput();

    game->updateInput(input);
    game->updateDraw();

    if (!game->isActive())
    {
        // If the game is not active, return to the main menu
        viewManager->back();
        return;
    }
}

static void freeRoamStop(ViewManager *viewManager)
{
    game.reset();
    if (freeRoamAlert)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            freeRoamAlert->clear();
        delete freeRoamAlert;
        freeRoamAlert = nullptr;
    }
}

static const PROGMEM View freeRoamView("Free Roam", freeRoamRun, freeRoamStart, freeRoamStop);