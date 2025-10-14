#pragma once
#include "../../../gui/alert.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/games/arkanoid/arkanoid.hpp"
#include "../../../applications/games/doom/doom.hpp"
#include "../../../applications/games/flappybird/flappybird.hpp"
#include "../../../applications/games/flightassault/flightassault.hpp"
// #include "../../../applications/games/flipworld/flipworld.hpp"
// #include "../../../applications/games/freeroam/freeroam.hpp"
#include "../../../applications/games/furiousbirds/furiousbirds.hpp"
#include "../../../applications/games/labyrinth/labyrinth.hpp"
#include "../../../applications/games/pong/pong.hpp"
#include "../../../applications/games/spaceinvaders/spaceinvaders.hpp"
#include "../../../applications/games/tetris/tetris.hpp"
#include "../../../applications/games/trexrunner/trexrunner.hpp"

static Menu *games = nullptr;
static uint8_t gamesIndex = 0; // Index for the games menu
static void gamesSwitchToView(ViewManager *viewManager)
{
    const char *currentItem = games->getCurrentItem();
    if (viewManager->getView(currentItem) == nullptr)
    {
        if (strcmp(currentItem, "Arkanoid") == 0)
        {
            viewManager->add(&arkanoidView);
        }
        else if (strcmp(currentItem, "Doom") == 0)
        {
            viewManager->add(&doomView);
        }
        else if (strcmp(currentItem, "Flappy Bird") == 0)
        {
            viewManager->add(&flappyBirdView);
        }
        else if (strcmp(currentItem, "Flight Assault") == 0)
        {
            viewManager->add(&flightAssaultView);
        }
        // else if (strcmp(currentItem, "FlipWorld") == 0)
        // {
        //     viewManager->add(&flipWorldView);
        // }
        // else if (strcmp(currentItem, "Free Roam") == 0)
        // {
        //     viewManager->add(&freeRoamView);
        // }
        else if (strcmp(currentItem, "Furious Birds") == 0)
        {
            viewManager->add(&furiousBirdsView);
        }
        else if (strcmp(currentItem, "Labyrinth") == 0)
        {
            viewManager->add(&labyrinthView);
        }
        else if (strcmp(currentItem, "Pong") == 0)
        {
            viewManager->add(&pongView);
        }
        else if (strcmp(currentItem, "Space Invaders") == 0)
        {
            viewManager->add(&spaceInvadersView);
        }
        else if (strcmp(currentItem, "Tetris") == 0)
        {
            viewManager->add(&tetrisView);
        }
        else if (strcmp(currentItem, "T-Rex Runner") == 0)
        {
            viewManager->add(&trexRunnerView);
        }
    }
    viewManager->switchTo(currentItem);
}
static bool gamesStart(ViewManager *viewManager)
{
    if (games != nullptr)
    {
        delete games;
        games = nullptr;
    }

    games = new Menu(
        viewManager->getDraw(),            // draw instance
        "Games",                           // title
        0,                                 // y
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    games->addItem("Arkanoid");
    games->addItem("Doom");
    games->addItem("Flappy Bird");
    // games->addItem("Flight Assault");
    //  games->addItem("FlipWorld");
    //  games->addItem("Free Roam");
    // games->addItem("Furious Birds");
    games->addItem("Labyrinth");
    games->addItem("Pong");
    games->addItem("Space Invaders");
    games->addItem("Tetris");
    // games->addItem("T-Rex Runner");
    games->setSelected(gamesIndex);
    games->draw();
    return true;
}

static void gamesRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_UP:
        games->scrollUp();
        inputManager->reset();
        break;
    case BUTTON_DOWN:
        games->scrollDown();
        inputManager->reset();
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        gamesIndex = 0;
        viewManager->back();
        inputManager->reset();
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        gamesIndex = games->getSelectedIndex();
        gamesSwitchToView(viewManager);
        inputManager->reset();
    }
    break;
    default:
        break;
    }
}

static void gamesStop(ViewManager *viewManager)
{
    if (games != nullptr)
    {
        delete games;
        games = nullptr;
    }
}

static const View gamesView = View("Games", gamesRun, gamesStart, gamesStop);