#pragma once
#include "../../../gui/alert.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
// #include "../../../applications/applications/flip_social/flip_social.hpp"
// #include "../../../applications/applications/file_browser/file_browser.hpp"
#include "../../../applications/applications/GPS/GPS.hpp"
#include "../../../applications/applications/Weather/weather.hpp"

// Add includes
#include "../../../system/binary_app.hpp"
#include "../../../system/app_loader.hpp"

static Menu *applications = nullptr;
static uint8_t applicationsIndex = 0; // Index for the applications menu

// Dynamic Apps View - declare before use
static AppLoader *appLoader = nullptr;
static Menu *dynamicAppsMenu = nullptr;
static uint8_t dynamicAppsIndex = 0;
static bool appIsRunning = false;

static bool dynamicAppStart(ViewManager *viewManager)
{
    if (appLoader == nullptr)
    {
        appLoader = new AppLoader(viewManager);
    }

    // Scan for apps and create menu
    appLoader->scanForApps();

    if (dynamicAppsMenu != nullptr)
    {
        delete dynamicAppsMenu;
        dynamicAppsMenu = nullptr;
    }

    dynamicAppsMenu = new Menu(
        viewManager->getDraw(),            // draw instance
        "UF2 Native Apps",                 // title
        0,                                 // y
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        9                                  // max visible items
    );

    const auto &apps = appLoader->getAvailableApps();
    if (apps.empty())
    {
        dynamicAppsMenu->addItem("No UF2 apps found");
        dynamicAppsMenu->addItem("Place .uf2 files in test_apps/");
    }
    else
    {
        for (const auto &app : apps)
        {
            // Add indicator for UF2 apps
            const char *extension = strrchr(app.entryPoint, '.');
            if (extension && strcmp(extension, ".uf2") == 0)
            {
                char displayName[80];
                snprintf(displayName, sizeof(displayName), "🚀 %s", app.name);
                dynamicAppsMenu->addItem(displayName);
            }
            else
            {
                dynamicAppsMenu->addItem(app.name);
            }
        }
    }

    dynamicAppsMenu->setSelected(dynamicAppsIndex);
    dynamicAppsMenu->draw();
    return true;
}

static void dynamicAppRun(ViewManager *viewManager)
{
    if (dynamicAppsMenu == nullptr)
        return;

    // If an app is running, handle it differently
    if (appIsRunning && appLoader != nullptr && appLoader->hasLoadedApp())
    {
        auto inputManager = viewManager->getInputManager();
        auto input = inputManager->getLastButton();

        // Check for back button to exit the running app
        if (input == BUTTON_BACK || input == BUTTON_LEFT)
        {
            appLoader->unloadCurrentApp();
            appIsRunning = false;
            inputManager->reset(true);
            // Redraw the menu
            dynamicAppsMenu->draw();
            return;
        }

        // Run the current app
        DynamicApp *currentApp = appLoader->getCurrentApp();
        if (currentApp != nullptr)
        {
            currentApp->run(viewManager);
        }
        return;
    }

    // Handle menu navigation when no app is running
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    switch (input)
    {
    case BUTTON_UP:
        dynamicAppsMenu->scrollUp();
        dynamicAppsIndex = dynamicAppsMenu->getSelectedIndex();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        dynamicAppsMenu->scrollDown();
        dynamicAppsIndex = dynamicAppsMenu->getSelectedIndex();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
    case BUTTON_BACK:
        viewManager->back();
        inputManager->reset(true);
        return;
    case BUTTON_CENTER:
    case BUTTON_RIGHT:
        if (appLoader != nullptr)
        {
            const auto &apps = appLoader->getAvailableApps();
            if (!apps.empty() && dynamicAppsIndex < apps.size())
            {
                // Launch the selected app
                if (appLoader->launchApp(dynamicAppsIndex))
                {
                    // App launched successfully, switch to running state
                    appIsRunning = true;
                    inputManager->reset(true);
                    return;
                }
            }
        }
        inputManager->reset(true);
        return;
    default:
        break;
    }

    // Redraw menu only when not running an app
    if (!appIsRunning)
    {
        dynamicAppsMenu->draw();
    }
}

static void dynamicAppStop(ViewManager *viewManager)
{
    if (appLoader != nullptr)
    {
        appLoader->unloadCurrentApp();
    }
    if (dynamicAppsMenu != nullptr)
    {
        delete dynamicAppsMenu;
        dynamicAppsMenu = nullptr;
    }
    appIsRunning = false;
}

static const View dynamicAppView = View("Dynamic Apps", dynamicAppRun, dynamicAppStart, dynamicAppStop);

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

    // Add menu item (in applicationsStart function)
    applications->addItem("UF2 Apps");

    // applications->addItem("File Browser");
    // applications->addItem("FlipSocial");
    // if wifi isn't available, return
#ifdef CYW43_WL_GPIO_LED_PIN
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
        // Add handler (in applicationsRun function)
        if (strcmp(currentItem, "UF2 Apps") == 0)
        {
            if (viewManager->getView("Dynamic Apps") == nullptr)
            {
                viewManager->add(&dynamicAppView);
            }
            viewManager->switchTo("Dynamic Apps");
            return;
        }

        // if (strcmp(currentItem, "File Browser") == 0)
        // {
        //     if (viewManager->getView("File Browser") == nullptr)
        //     {
        //         viewManager->add(&fileBrowserView);
        //     }
        //     viewManager->switchTo("File Browser");
        //     return;
        // }
        // if (strcmp(currentItem, "FlipSocial") == 0)
        // {
        //     if (viewManager->getView("FlipSocial") == nullptr)
        //     {
        //         viewManager->add(&flipSocialView);
        //     }
        //     viewManager->switchTo("FlipSocial");
        //     return;
        // }
        // if wifi isn't available, return
#ifdef CYW43_WL_GPIO_LED_PIN
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