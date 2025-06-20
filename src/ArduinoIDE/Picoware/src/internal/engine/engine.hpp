#pragma once
#include "Arduino.h"
#include "../../internal/engine/game.hpp"
namespace Picoware
{
    class GameEngine
    {
    private:
        float fps;  // The frames per second of the game engine.
        Game *game; // The game to run.
    public:
        GameEngine(Game *game, float fps)
            : fps(fps), game(game)
        {
        }

        inline void run()
        {
            // Initialize the game if not already active.
            if (!game->is_active)
            {
                game->start();
            }

            while (game->is_active)
            {
                // Update the game
                game->update();

                // Render the game
                game->render();

                delay(1000 / fps);
            }

            this->stop();
        }

        inline void runAsync(bool shouldDelay = true)
        {
            // Initialize the game if not already active.
            if (!game->is_active)
            {
                game->start();
            }

            // Update the game
            game->update();

            // Render the game
            game->render();

            if (shouldDelay)
            {
                // Delay to control the frame rate
                delay(1000 / fps);
            }
        }

        inline void stop()
        {
            // Stop the game
            game->stop();

            // clear the screen
            game->draw->clear(Vector(0, 0), game->size, game->bg_color);

            game->draw->swap();

            delete game;
            game = nullptr;
        }

        inline Game *getGame() const { return game; }
    };

}