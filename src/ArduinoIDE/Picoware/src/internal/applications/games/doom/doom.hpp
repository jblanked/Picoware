// Translated from https://github.com/xMasterX/all-the-plugins/tree/dev/base_pack/doom
// All credits to @xMasterX @Svarich @hedger (original code by @p4nic4ttack)

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/engine/engine.hpp"
#include "../../../../internal/engine/entity.hpp"
#include "../../../../internal/engine/game.hpp"
#include "../../../../internal/engine/level.hpp"
#include "../../../../internal/applications/games/doom/game.hpp"

static GameEngine *doomEngine = nullptr;

static bool doomStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Doom",                            // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        TFT_WHITE,                         // Foreground color
        TFT_BLACK,                         // Background color
        CAMERA_FIRST_PERSON,               // Camera perspective
        nullptr,                           // Game start callback
        Doom::game_stop                    // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    // Add the player entity to the level
    Doom::player_spawn(level, game);

    // Create the game engine (with 120 frames per second target).
    doomEngine = new GameEngine(game, 120);

    return true;
}

static void doomRun(ViewManager *viewManager)
{
    // Run the game engine
    if (doomEngine != nullptr)
    {
        doomEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
        return;
    }
}

static void doomStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (doomEngine != nullptr)
    {
        doomEngine->stop();
        delete doomEngine;
        doomEngine = nullptr;
    }
}

static const PROGMEM View doomView = View("Doom", doomRun, doomStart, doomStop);