// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/apps_source_code/flipper_pong/flipper_pong.c

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/games/pong/game.hpp"

static GameEngine *pongEngine = nullptr;

static bool pongStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Pong",                         // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_BLACK,                      // Foreground color
        TFT_WHITE,                      // Background color
        CAMERA_FIRST_PERSON,            // Camera perspective
        nullptr,                        // Game start callback
        Pong::game_stop                 // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(320, 240), game);
    game->level_add(level);

    // Add the player entity to the level
    Pong::player_spawn(level, game);

    // Create the game engine (with 60 frames per second target).
    pongEngine = new GameEngine(game, 60);

    return true;
}

static void pongRun(ViewManager *viewManager)
{
    // Run the game engine
    if (pongEngine != nullptr)
    {
        pongEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
        return;
    }
}

static void pongStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (pongEngine != nullptr)
    {
        pongEngine->stop();
        delete pongEngine;
        pongEngine = nullptr;
    }
}

static const View pongView = View("Pong", pongRun, pongStart, pongStop);