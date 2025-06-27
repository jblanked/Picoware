// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/arkanoid/arkanoid_game.c

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/engine/engine.hpp"
#include "../../../../internal/engine/entity.hpp"
#include "../../../../internal/engine/game.hpp"
#include "../../../../internal/engine/level.hpp"
#include "../../../../internal/applications/games/arkanoid/game.hpp"

static GameEngine *arkanoidEngine = nullptr;

static bool arkanoidStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Arkanoid",                        // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        viewManager->getForegroundColor(), // Foreground color
        viewManager->getBackgroundColor()  // Background color
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    // Add the player entity to the level
    Arkanoid::player_spawn(level, game);

    // Create the game engine (with 240 frames per second target).
    arkanoidEngine = new GameEngine(game, 240);

    return true;
}

static void arkanoidRun(ViewManager *viewManager)
{
    // Run the game engine
    if (arkanoidEngine != nullptr)
    {
        arkanoidEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        return;
    }
}

static void arkanoidStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (arkanoidEngine != nullptr)
    {
        arkanoidEngine->stop();
        delete arkanoidEngine;
        arkanoidEngine = nullptr;
    }
}

static const PROGMEM View arkanoidView = View("Arkanoid", arkanoidRun, arkanoidStart, arkanoidStop);