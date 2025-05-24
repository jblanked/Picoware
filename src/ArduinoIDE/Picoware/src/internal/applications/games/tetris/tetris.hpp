// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/tetris_game

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/tetris/game.hpp"

static GameEngine *tetrisEngine = nullptr;

static void tetrisStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Tetris",                          // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        viewManager->getForegroundColor(), // Foreground color
        viewManager->getBackgroundColor(), // Background color
        nullptr,                           // Game start callback
        Tetris::game_stop                  // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    // Add the player entity to the level
    Tetris::player_spawn(level, game);

    // Create the game engine (with 15 frames per second target).
    tetrisEngine = new GameEngine(game, 15);
}

static void tetrisRun(ViewManager *viewManager)
{
    // Run the game engine
    if (tetrisEngine != nullptr)
    {
        tetrisEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        return;
    }
}

static void tetrisStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (tetrisEngine != nullptr)
    {
        tetrisEngine->stop();
        delete tetrisEngine;
        tetrisEngine = nullptr;
    }
}

static const PROGMEM View tetrisView = View("Tetris", tetrisRun, tetrisStart, tetrisStop);