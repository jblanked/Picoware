// Original from https://github.com/bmstr-ru/furious-birds/blob/main/furious_birds.c

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../engine/engine.hpp"
#include "../../../engine/entity.hpp"
#include "../../../engine/game.hpp"
#include "../../../engine/level.hpp"
#include "../../../applications/games/furiousbirds/game.hpp"

static GameEngine *furiousBirdsEngine = nullptr;

static bool furiousBirdsStart(ViewManager *viewManager)
{
    // Create the game instance with its name, start/stop callbacks, and colors.
    Game *game = new Game(
        "Furious Birds",                // Game name
        Vector(320, 240),               // Game size
        viewManager->getDraw(),         // Draw object
        viewManager->getInputManager(), // Input manager
        TFT_BLACK,                      // Foreground color
        TFT_WHITE,                      // Background color
        CAMERA_FIRST_PERSON,            // Camera perspective
        nullptr,                        // Game start callback
        FuriousBirds::game_stop         // Game stop callback
    );

    // Create and add a level to the game.
    Level *level = new Level("Level 1", Vector(320, 240), game);
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
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset();
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

static const View furiousBirdsView = View("Furious Birds", furiousBirdsRun, furiousBirdsStart, furiousBirdsStop);