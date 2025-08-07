// Original from https://github.com/evillero/flight_assault/tree/main

#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/flightassault/game.hpp"

static GameEngine *flightAssaultEngine = nullptr;

static bool flightAssaultStart(ViewManager *viewManager)
{
    auto board = viewManager->getBoard();

    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Flight Assault",                  // Game name
        Vector(board.width, board.height), // Game size
        viewManager->getDraw(),            // Draw object
        viewManager->getInputManager(),    // Input manager
        TFT_BLACK,                         // Foreground color
        TFT_WHITE,                         // Background color
        CAMERA_FIRST_PERSON,               // Camera perspective
        nullptr,                           // Game start callback
        FlightAssault::game_stop           // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(board.width, board.height), game);
    game->level_add(level);

    // Add the player entity to the level
    FlightAssault::player_spawn(level, game);

    // Create the game engine (with 60 frames per second target).
    flightAssaultEngine = new GameEngine(game, 60);

    return true;
}

static void flightAssaultRun(ViewManager *viewManager)
{
    // Run the game engine
    if (flightAssaultEngine != nullptr)
    {
        flightAssaultEngine->runAsync(false);
    }
    auto input = viewManager->getInputManager()->getInput();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
        return;
    }
}

static void flightAssaultStop(ViewManager *viewManager)
{
    // Stop the game engine
    if (flightAssaultEngine != nullptr)
    {
        flightAssaultEngine->stop();
        delete flightAssaultEngine;
        flightAssaultEngine = nullptr;
    }
}

static const PROGMEM View flightAssaultView = View("Flight Assault", flightAssaultRun, flightAssaultStart, flightAssaultStop);