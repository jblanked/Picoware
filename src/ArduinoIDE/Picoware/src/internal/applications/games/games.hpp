#pragma once
#include "../../../internal/gui/alert.hpp"
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/games/arkanoid/arkanoid.hpp"
#include "../../../internal/applications/games/doom/doom.hpp"
#include "../../../internal/applications/games/flappybird/flappybird.hpp"
#include "../../../internal/applications/games/flightassault/flightassault.hpp"
#include "../../../internal/applications/games/flipworld/flipworld.hpp"
#include "../../../internal/applications/games/freeroam/freeroam.hpp"
#include "../../../internal/applications/games/furiousbirds/furiousbirds.hpp"
#include "../../../internal/applications/games/labyrinth/labyrinth.hpp"
#include "../../../internal/applications/games/pong/pong.hpp"
#include "../../../internal/applications/games/tetris/tetris.hpp"
#include "../../../internal/applications/games/trexrunner/trexrunner.hpp"
using namespace Picoware;
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
        else if (strcmp(currentItem, "FlipWorld") == 0)
        {
            viewManager->add(&flipWorldView);
        }
        else if (strcmp(currentItem, "Free Roam") == 0)
        {
            viewManager->add(&freeRoamView);
        }
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
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    games->addItem("Arkanoid");
    games->addItem("Doom");
    games->addItem("Flappy Bird");
    games->addItem("Flight Assault");
    games->addItem("FlipWorld");
    games->addItem("Free Roam");
    games->addItem("Furious Birds");
    games->addItem("Labyrinth");
    games->addItem("Pong");
    games->addItem("Tetris");
    games->addItem("T-Rex Runner");
    games->setSelected(gamesIndex);
    games->draw();
    return true;
}

static void gamesRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        games->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        games->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        gamesIndex = 0;
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        gamesIndex = games->getSelectedIndex();
        gamesSwitchToView(viewManager);
        inputManager->reset(true);
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
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            games->clear();
        delete games;
        games = nullptr;
    }
}

const PROGMEM View gamesView = View("Games", gamesRun, gamesStart, gamesStop);