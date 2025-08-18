// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/tetris_game

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/games/tetris/game.hpp"

static GameEngine *tetrisEngine = nullptr;

static bool tetrisStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Tetris",                       // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_BLACK,                      // Foreground color
        TFT_WHITE,                      // Background color
        CAMERA_FIRST_PERSON,            // Camera perspective
        nullptr,                        // Game start callback
        Tetris::game_stop               // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(320, 240), game);
    game->level_add(level);

    // Add the player entity to the level
    Tetris::player_spawn(level, game);

    // Create the game engine (with 15 frames per second target).
    tetrisEngine = new GameEngine(game, 15);

    return true;
}

static void tetrisRun(ViewManager *viewManager)
{
    // Run the game engine
    if (tetrisEngine != nullptr)
    {
        tetrisEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
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

static const View tetrisView = View("Tetris", tetrisRun, tetrisStart, tetrisStop);