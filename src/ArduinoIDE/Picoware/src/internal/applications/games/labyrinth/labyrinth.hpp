// Original from https://github.com/jamisonderek/flipper-zero-tutorials/tree/main/vgm/apps/air_labyrinth

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/labyrinth/game.hpp"

static GameEngine *labyrinthEngine = nullptr;

static void labyrinthStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Labyrinth",                       // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        viewManager->getForegroundColor(), // Foreground color
        viewManager->getBackgroundColor(), // Background color
        CAMERA_FIRST_PERSON,               // Camera perspective
        nullptr,                           // Game start callback
        Labyrinth::game_stop               // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    Labyrinth::wall_spawn(level);
    Labyrinth::player_spawn(level);

    // Create the game engine (with 30 frames per second target).
    labyrinthEngine = new GameEngine(game, 30);
}

static void labyrinthRun(ViewManager *viewManager)
{
    // Run the game engine
    if (labyrinthEngine != nullptr)
    {
        labyrinthEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        return;
    }
}

static void labyrinthStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (labyrinthEngine != nullptr)
    {
        labyrinthEngine->stop();
        delete labyrinthEngine;
        labyrinthEngine = nullptr;
    }
}

static const PROGMEM View labyrinthView = View("Labyrinth", labyrinthRun, labyrinthStart, labyrinthStop);