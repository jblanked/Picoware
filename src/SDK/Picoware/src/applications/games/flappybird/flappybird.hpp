// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/flappy_bird

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/games/flappybird/game.hpp"

static GameEngine *flappyBirdEngine = nullptr;

static bool flappyBirdStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Flappy Bird",                  // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_BLACK,                      // Foreground color
        TFT_WHITE,                      // Background color
        CAMERA_FIRST_PERSON,            // Camera perspective
        nullptr,                        // Game start callback
        FlappyBird::game_stop           // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(320, 240), game);
    game->level_add(level);

    // Add the player entity to the level
    FlappyBird::player_spawn(level, game);

    // Create the game engine (with 60 frames per second target).
    flappyBirdEngine = new GameEngine(game, 60);

    return true;
}

static void flappyBirdRun(ViewManager *viewManager)
{
    // Run the game engine
    if (flappyBirdEngine != nullptr)
    {
        flappyBirdEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset();
        return;
    }
}

static void flappyBirdStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (flappyBirdEngine != nullptr)
    {
        flappyBirdEngine->stop();
        delete flappyBirdEngine;
        flappyBirdEngine = nullptr;
    }
}

static const View flappyBirdView = View("Flappy Bird", flappyBirdRun, flappyBirdStart, flappyBirdStop);