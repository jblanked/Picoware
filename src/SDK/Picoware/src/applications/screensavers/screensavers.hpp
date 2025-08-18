#pragma once
#include "../../gui/menu.hpp"
#include "../../system/view.hpp"
#include "../../system/view_manager.hpp"
#include "../../applications/screensavers/cube/cube.hpp"
#include "../../applications/screensavers/spiro/spiro.hpp"
#include "../../applications/screensavers/starfield/starfield.hpp"

static Menu *screensavers = nullptr;
static uint8_t screensaversIndex = 0; // Index for the screensavers menu
static bool screensaversStart(ViewManager *viewManager)
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
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    screensavers->addItem("Cube");
    screensavers->addItem("Spiro");
    screensavers->addItem("Starfield");
    screensavers->setSelected(screensaversIndex);
    screensavers->draw();

    return true;
}

static void screensaversRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
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
    case BUTTON_BACK:
        screensaversIndex = 0;
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        inputManager->reset(true);
        auto currentItem = screensavers->getCurrentItem();
        screensaversIndex = screensavers->getSelectedIndex();
        if (strcmp(currentItem, "Cube") == 0)
        {
            if (viewManager->getView("Cube") == nullptr)
            {
                viewManager->add(&cubeView);
            }
            viewManager->switchTo("Cube");
            return;
        }
        if (strcmp(currentItem, "Spiro") == 0)
        {
            if (viewManager->getView("Spiro") == nullptr)
            {
                viewManager->add(&spiroView);
            }
            viewManager->switchTo("Spiro");
            return;
        }
        if (strcmp(currentItem, "Starfield") == 0)
        {
            if (viewManager->getView("Starfield") == nullptr)
            {
                viewManager->add(&starfieldView);
            }
            viewManager->switchTo("Starfield");
            return;
        }
        break;
    }
    default:
        break;
    }
}

static void screensaversStop(ViewManager *viewManager)
{
    if (screensavers != nullptr)
    {
        delete screensavers;
        screensavers = nullptr;
    }
}

static const View screensaversView = View("Screensavers", screensaversRun, screensaversStart, screensaversStop);