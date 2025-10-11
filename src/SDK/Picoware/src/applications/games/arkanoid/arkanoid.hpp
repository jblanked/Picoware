// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/arkanoid/arkanoid_game.c

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../engine/engine.hpp"
#include "../../../engine/entity.hpp"
#include "../../../engine/game.hpp"
#include "../../../engine/level.hpp"
#include "../../../applications/games/arkanoid/game.hpp"

static GameEngine *arkanoidEngine = nullptr;

static bool arkanoidStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Arkanoid",                     // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_BLACK,                      // Foreground color
        TFT_WHITE                       // Background color
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(320, 240), game);
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
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset();
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

static const View arkanoidView = View("Arkanoid", arkanoidRun, arkanoidStart, arkanoidStop);