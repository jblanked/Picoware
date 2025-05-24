// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/apps_source_code/flipper_pong/flipper_pong.c

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/pong/game.hpp"

static GameEngine *pongEngine = nullptr;

static void pongStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Pong",                            // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        viewManager->getForegroundColor(), // Foreground color
        viewManager->getBackgroundColor(), // Background color
        nullptr,                           // Game start callback
        Pong::game_stop                    // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    // Add the player entity to the level
    Pong::player_spawn(level, game);

    // Create the game engine (with 60 frames per second target).
    pongEngine = new GameEngine(game, 60);
}

static void pongRun(ViewManager *viewManager)
{
    // Run the game engine
    if (pongEngine != nullptr)
    {
        pongEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
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

static const PROGMEM View pongView = View("Pong", pongRun, pongStart, pongStop);