// Original from https://github.com/jamisonderek/flipper-zero-tutorials/tree/main/vgm/apps/air_labyrinth

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/games/labyrinth/game.hpp"

static GameEngine *labyrinthEngine = nullptr;

static bool labyrinthStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Labyrinth",                    // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_BLACK,                      // Foreground color
        TFT_WHITE,                      // Background color
        CAMERA_FIRST_PERSON,            // Camera perspective
        nullptr,                        // Game start callback
        Labyrinth::game_stop            // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(320, 240), game);
    game->level_add(level);

    Labyrinth::wall_spawn(level);
    Labyrinth::player_spawn(level);

    // Create the game engine (with 30 frames per second target).
    labyrinthEngine = new GameEngine(game, 30);

    return true;
}

static void labyrinthRun(ViewManager *viewManager)
{
    // Run the game engine
    if (labyrinthEngine != nullptr)
    {
        labyrinthEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset();
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

static const View labyrinthView = View("Labyrinth", labyrinthRun, labyrinthStart, labyrinthStop);