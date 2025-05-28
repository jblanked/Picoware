#pragma once
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/applications/screensavers/cube/cube.hpp"
#include "../../../internal/applications/screensavers/spiro/spiro.hpp"
#include "../../../internal/applications/screensavers/starfield/starfield.hpp"
using namespace Picoware;
static Menu *screensavers = nullptr;

static void screensaversStart(ViewManager *viewManager)
{
    if (screensavers != nullptr)
    {
        delete screensavers;
        screensavers = nullptr;
    }

    screensavers = new Menu(
        viewManager->getDraw(),            // draw instance
        "Screensavers",                    // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    screensavers->addItem("Cube");
    screensavers->addItem("Spiro");

    // put at the bottom of the list for correct indexing
    if (viewManager->getBoard().boardType != BOARD_TYPE_VGM)
        screensavers->addItem("Starfield");

    screensavers->setSelected(0);
    screensavers->draw();
}

static void screensaversRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        screensavers->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        screensavers->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        switch (screensavers->getSelectedIndex())
        {
        case 0: // if index is 0, show cube
        {
            if (viewManager->getView("Cube") == nullptr)
            {
                viewManager->add(&cubeView);
            }
            viewManager->switchTo("Cube");
            break;
        }
        case 1: // if index is 1, show spiro
        {
            if (viewManager->getView("Spiro") == nullptr)
            {
                viewManager->add(&spiroView);
            }
            viewManager->switchTo("Spiro");
            break;
        }
        case 2: // if index is 2, show starfield
        {
            if (viewManager->getView("Starfield") == nullptr)
            {
                viewManager->add(&starfieldView);
            }
            viewManager->switchTo("Starfield");
            break;
        }
        default:
            break;
        };
        inputManager->reset(true);
    default:
        break;
    }
}

static void screensaversStop(ViewManager *viewManager)
{
    if (screensavers != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            screensavers->clear();
        delete screensavers;
        screensavers = nullptr;
    }
}

const PROGMEM View screensaversView = View("Screensavers", screensaversRun, screensaversStart, screensaversStop);