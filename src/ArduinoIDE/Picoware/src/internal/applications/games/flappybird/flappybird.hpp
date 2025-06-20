// Original from https://github.com/xMasterX/all-the-plugins/blob/dev/base_pack/flappy_bird

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/flappybird/game.hpp"

static GameEngine *flappyBirdEngine = nullptr;

static void flappyBirdStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Flappy Bird",                     // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        viewManager->getForegroundColor(), // Foreground color
        viewManager->getBackgroundColor(), // Background color
        CAMERA_FIRST_PERSON,               // Camera perspective
        nullptr,                           // Game start callback
        FlappyBird::game_stop              // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    // Add the player entity to the level
    FlappyBird::player_spawn(level, game);

    // Create the game engine (with 60 frames per second target).
    flappyBirdEngine = new GameEngine(game, 60);
}

static void flappyBirdRun(ViewManager *viewManager)
{
    // Run the game engine
    if (flappyBirdEngine != nullptr)
    {
        flappyBirdEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
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

static const PROGMEM View flappyBirdView = View("Flappy Bird", flappyBirdRun, flappyBirdStart, flappyBirdStop);