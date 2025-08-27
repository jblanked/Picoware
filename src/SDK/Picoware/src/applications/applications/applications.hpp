#pragma once
#include "../../../gui/alert.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../applications/applications/flip_social/flip_social.hpp"
// #include "../../../applications/applications/file_browser/file_browser.hpp"
#include "../../../applications/applications/GPS/GPS.hpp"
#include "../../../applications/applications/Weather/weather.hpp"

static Menu *applications = nullptr;
static uint8_t applicationsIndex = 0; // Index for the applications menu
static bool applicationsStart(ViewManager *viewManager)
{
    if (applications != nullptr)
    {
        delete applications;
        applications = nullptr;
    }

    applications = new Menu(
        viewManager->getDraw(),            // draw instance
        "Applications",                    // title
        0,                                 // y
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

// applications->addItem("File Browser");
#ifdef CYW43_WL_GPIO_LED_PIN
    applications->addItem("FlipSocial");
    applications->addItem("GPS");
    applications->addItem("Weather");
#endif
    applications->setSelected(applicationsIndex);
    applications->draw();
    return true;
}

static void applicationsRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_UP:
        applications->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        applications->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        applicationsIndex = 0;
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
    {
        const char *currentItem = applications->getCurrentItem();
        applicationsIndex = applications->getSelectedIndex();
// if (strcmp(currentItem, "File Browser") == 0)
// {
//     if (viewManager->getView("File Browser") == nullptr)
//     {
//         viewManager->add(&fileBrowserView);
//     }
//     viewManager->switchTo("File Browser");
//     return;
// }
#ifdef CYW43_WL_GPIO_LED_PIN
        if (strcmp(currentItem, "FlipSocial") == 0)
        {
            if (viewManager->getView("FlipSocial") == nullptr)
            {
                viewManager->add(&flipSocialView);
            }
            viewManager->switchTo("FlipSocial");
            return;
        }
        if (strcmp(currentItem, "GPS") == 0)
        {
            if (viewManager->getView("GPS") == nullptr)
            {
                viewManager->add(&gpsView);
            }
            viewManager->switchTo("GPS");
            return;
        }
        if (strcmp(currentItem, "Weather") == 0)
        {
            if (viewManager->getView("Weather") == nullptr)
            {
                viewManager->add(&weatherView);
            }
            viewManager->switchTo("Weather");
            return;
        }
#endif
        inputManager->reset(true);
        break;
    }
    default:
        break;
    }
}
static void applicationsStop(ViewManager *viewManager)
{
    if (applications != nullptr)
    {
        delete applications;
        applications = nullptr;
    }
}
static const View applicationsView = View("Applications", applicationsRun, applicationsStart, applicationsStop);