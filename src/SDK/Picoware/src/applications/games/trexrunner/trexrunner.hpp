// Original from https://github.com/xMasterX/all-the-plugins/tree/dev/apps_source_code/t-rex-runner

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/games/trexrunner/game.hpp"

static GameEngine *trexRunnerEngine = nullptr;

static bool trexRunnerStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "T-Rex Runner",                 // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_BLACK,                      // Foreground color
        TFT_WHITE,                      // Background color
        CAMERA_FIRST_PERSON,            // Camera perspective
        nullptr,                        // Game start callback
        TrexRunner::game_stop           // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(320, 240), game);
    game->level_add(level);

    // Add the player entity to the level
    TrexRunner::player_spawn(level, game);

    // Create the game engine (with 30 frames per second target).
    trexRunnerEngine = new GameEngine(game, 30);

    return true;
}

static void trexRunnerRun(ViewManager *viewManager)
{
    // Run the game engine
    if (trexRunnerEngine != nullptr)
    {
        trexRunnerEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
        return;
    }
}

static void trexRunnerStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (trexRunnerEngine != nullptr)
    {
        trexRunnerEngine->stop();
        delete trexRunnerEngine;
        trexRunnerEngine = nullptr;
    }
}

static const View trexRunnerView = View("T-Rex Runner", trexRunnerRun, trexRunnerStart, trexRunnerStop);