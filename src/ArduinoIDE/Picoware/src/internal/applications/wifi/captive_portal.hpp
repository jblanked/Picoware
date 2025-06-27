#pragma once
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/system/wifi_ap.hpp"
using namespace Picoware;
static Alert *wifiAPAlert = nullptr;
static WiFiAP *wifiAP = nullptr;
static bool captivePortalStart(ViewManager *viewManager)
{
    if (wifiAP)
    {
        delete wifiAP;
        wifiAP = nullptr;
    }
    if (wifiAPAlert)
    {
        delete wifiAPAlert;
        wifiAPAlert = nullptr;
    }

    auto draw = viewManager->getDraw();

    // if wifi isn't available, return
    if (!viewManager->getBoard().hasWiFi)
    {
        wifiAPAlert = new Alert(draw, "WiFi not available on your board.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        wifiAPAlert->draw();
        delay(2000);
        return false;
    }

    draw->text(Vector(5, 5), "Starting Captive Portal...");
    draw->swap();

    wifiAP = new WiFiAP();
    if (!wifiAP->start("Picoware"))
    {
        wifiAPAlert = new Alert(draw, "Failed to start AP mode.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        wifiAPAlert->draw();
        delay(2000);
        return false;
    }
    viewManager->getLED().on();
    auto size = viewManager->getSize();
    draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
    draw->text(Vector(5, 5), "Captive Portal running... Press BACK to stop.");
    draw->swap();
    return true;
}

static void captivePortalRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
        break;
    }
    wifiAP->runAsync();

    String strInput = wifiAP->getInputs();
    if (strInput.length() != 0)
    {
        auto draw = viewManager->getDraw();
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Captive Portal running... Press BACK to stop.", viewManager->getForegroundColor());
        draw->text(Vector(0, 25), strInput.c_str(), viewManager->getForegroundColor());
        draw->swap();
    }
}

static void captivePortalStop(ViewManager *viewManager)
{
    if (wifiAP)
    {
        wifiAP->stop();
        delete wifiAP;
        wifiAP = nullptr;
    }
    if (wifiAPAlert)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            wifiAPAlert->clear();
        delete wifiAPAlert;
        wifiAPAlert = nullptr;
    }
}

const PROGMEM View captivePortalView = View("Captive Portal", captivePortalRun, captivePortalStart, captivePortalStop);