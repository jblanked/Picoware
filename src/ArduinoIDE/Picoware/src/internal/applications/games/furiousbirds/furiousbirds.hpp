// Original from https://github.com/bmstr-ru/furious-birds/blob/main/furious_birds.c

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/engine/engine.hpp"
#include "../../../../internal/engine/entity.hpp"
#include "../../../../internal/engine/game.hpp"
#include "../../../../internal/engine/level.hpp"
#include "../../../../internal/applications/games/furiousbirds/game.hpp"

static GameEngine *furiousBirdsEngine = nullptr;

static bool furiousBirdsStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Furious Birds",                   // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        TFT_BLACK,                         // Foreground color
        TFT_WHITE,                         // Background color
        CAMERA_FIRST_PERSON,               // Camera perspective
        nullptr,                           // Game start callback
        FuriousBirds::game_stop            // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    // Add the player entity to the level
    FuriousBirds::player_spawn(level, game);

    // Create the game engine (with 240 frames per second target).
    furiousBirdsEngine = new GameEngine(game, 240);

    return true;
}

static void furiousBirdsRun(ViewManager *viewManager)
{
    // Run the game engine
    if (furiousBirdsEngine != nullptr)
    {
        furiousBirdsEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
        return;
    }
}

static void furiousBirdsStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (furiousBirdsEngine != nullptr)
    {
        furiousBirdsEngine->stop();
        delete furiousBirdsEngine;
        furiousBirdsEngine = nullptr;
    }
}

static const PROGMEM View furiousBirdsView = View("Furious Birds", furiousBirdsRun, furiousBirdsStart, furiousBirdsStop);