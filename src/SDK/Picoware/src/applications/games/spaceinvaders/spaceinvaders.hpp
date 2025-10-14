// Original Space Invaders - Classic arcade space shooter
// Implementation for Picoware gaming system

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/games/spaceinvaders/game.hpp"

static GameEngine *spaceInvadersEngine = nullptr;

static bool spaceInvadersStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Space Invaders",               // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_WHITE,                      // Foreground color
        TFT_BLACK,                      // Background color
        CAMERA_FIRST_PERSON,            // Camera perspective
        nullptr,                        // Game start callback
        SpaceInvaders::game_stop        // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Space Battle", Vector(320, 240), game);
    game->level_add(level);

    // Add the player entity to the level
    SpaceInvaders::player_spawn(level, game);

    // Create the game engine (with 30 frames per second for stable performance).
    spaceInvadersEngine = new GameEngine(game, 30);

    return true;
}

static void spaceInvadersRun(ViewManager *viewManager)
{
    // Run the game engine
    if (spaceInvadersEngine != nullptr)
    {
        spaceInvadersEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
        return;
    }
}

static void spaceInvadersStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (spaceInvadersEngine != nullptr)
    {
        spaceInvadersEngine->stop();
        delete spaceInvadersEngine;
        spaceInvadersEngine = nullptr;
    }
}

static const View spaceInvadersView = View("Space Invaders", spaceInvadersRun, spaceInvadersStart, spaceInvadersStop);