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
#include "../../../internal/applications/games/furiousbirds/furiousbirds.hpp"
#include "../../../internal/applications/games/pong/pong.hpp"
#include "../../../internal/applications/games/tetris/tetris.hpp"
#include "../../../internal/applications/games/trexrunner/trexrunner.hpp"
using namespace Picoware;
static Menu *games = nullptr;
static Alert *gameMemoryAlert = nullptr;
static void gamesStart(ViewManager *viewManager)
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
    games->addItem("Furious Birds");
    games->addItem("Pong");
    games->addItem("Tetris");
    games->addItem("T-Rex Runner");
    games->setSelected(0);
    games->draw();
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
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        switch (games->getSelectedIndex())
        {
        case 0: // if index is 0, show arkanoid
        {
            if (viewManager->getView("Arkanoid") == nullptr)
            {
                viewManager->add(&arkanoidView);
            }
            viewManager->switchTo("Arkanoid");
            break;
        }
        case 1: // if index is 1, show doom
        {
            if (viewManager->getView("Doom") == nullptr)
            {
                viewManager->add(&doomView);
            }
            viewManager->switchTo("Doom");
            break;
        }
        case 2: // if index is 2, show flappy bird
        {
            if (viewManager->getView("Flappy Bird") == nullptr)
            {
                viewManager->add(&flappyBirdView);
            }
            viewManager->switchTo("Flappy Bird");
            break;
        }
        case 3: // if index is 3, show flight assault
        {
            if (viewManager->getView("Flight Assault") == nullptr)
            {
                viewManager->add(&flightAssaultView);
            }
            viewManager->switchTo("Flight Assault");
            break;
        }
        case 4: // if index is 4, show flip world
        {
            if (viewManager->getBoard().boardType != BOARD_TYPE_VGM)
            {
                if (viewManager->getView("FlipWorld") == nullptr)
                {
                    viewManager->add(&flipWorldView);
                }
                viewManager->switchTo("FlipWorld");
            }
            else
            {
                auto draw = viewManager->getDraw();
                draw->clear(Vector(0, 0), draw->getSize(), viewManager->getBackgroundColor());
                gameMemoryAlert = new Alert(draw, "Not enough memory for FlipWorld yet..", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
                gameMemoryAlert->draw();
                delay(2000);
                viewManager->back();
            }
            return;
        }
        case 5: // if index is 5, show furious birds
        {
            if (viewManager->getView("Furious Birds") == nullptr)
            {
                viewManager->add(&furiousBirdsView);
            }
            viewManager->switchTo("Furious Birds");
            break;
        }
        case 6: // if index is 6, show pong
        {
            if (viewManager->getView("Pong") == nullptr)
            {
                viewManager->add(&pongView);
            }
            viewManager->switchTo("Pong");
            break;
        }
        case 7: // if index is 7, show tetris
        {
            if (viewManager->getView("Tetris") == nullptr)
            {
                viewManager->add(&tetrisView);
            }
            viewManager->switchTo("Tetris");
            break;
        }
        case 8: // if index is 8, show t-rex runner
        {
            if (viewManager->getView("T-Rex Runner") == nullptr)
            {
                viewManager->add(&trexRunnerView);
            }
            viewManager->switchTo("T-Rex Runner");
            break;
        }
        default: // none for now
            break;
        };
        inputManager->reset(true);
    default:
        break;
    }
}

static void gamesStop(ViewManager *viewManager)
{

    if (gameMemoryAlert != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            gameMemoryAlert->clear();
        delete gameMemoryAlert;
        gameMemoryAlert = nullptr;
    }
    if (games != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            games->clear();
        delete games;
        games = nullptr;
    }
}

const PROGMEM View gamesView = View("Games", gamesRun, gamesStart, gamesStop);