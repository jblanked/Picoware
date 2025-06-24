// Original from https://github.com/jblanked/FlipWorld

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/flipworld/assets.hpp"
#include "../../../../internal/applications/games/flipworld/game.hpp"
#include "../../../../internal/applications/games/flipworld/icon.hpp"

static GameEngine *flipWorldEngine = nullptr;

static bool flipWorldStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "FlipWorld",                       // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        viewManager->getForegroundColor(), // Foreground color
        viewManager->getBackgroundColor(), // Background color
        CAMERA_FIRST_PERSON,               // Camera perspective
        nullptr,                           // Game start callback
        FlipWorld::game_stop               // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(768, 384), game, NULL, NULL);
    game->level_add(level);

    // set game position to center of player
    game->pos = Vector(384, 192);
    game->old_pos = game->pos;

    // spawn icons from json
    FlipWorld::icon_spawn_json(level, shadow_woods_v4);

    // spawn enemys from json
    FlipWorld::enemy_spawn_json(level, shadow_woods_v4);

    // Add the player entity to the level
    FlipWorld::player_spawn(level, "sword", Vector(384, 192));

    // Create the game engine (with 60 frames per second target).
    flipWorldEngine = new GameEngine(game, 60);

    return true;
}

static void flipWorldRun(ViewManager *viewManager)
{
    // Run the game engine
    if (flipWorldEngine != nullptr)
    {
        flipWorldEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_BACK)
    {
        viewManager->back();
        return;
    }
}

static void flipWorldStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (flipWorldEngine != nullptr)
    {
        flipWorldEngine->stop();
        delete flipWorldEngine;
        flipWorldEngine = nullptr;
    }
}

static const PROGMEM View flipWorldView = View("FlipWorld", flipWorldRun, flipWorldStart, flipWorldStop);