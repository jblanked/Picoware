#pragma once
#include "../../../internal/gui/alert.hpp"
#include "../../../internal/gui/menu.hpp"
#include "../../../internal/system/view.hpp"
#include "../../../internal/system/view_manager.hpp"
#include "../../../internal/system/wifi_utils.hpp"
using namespace Picoware;
static Menu *wifiScan = nullptr;
static Alert *wifiScanAlert = nullptr;

static bool wifiScanStart(ViewManager *viewManager)
{
    if (wifiScan != nullptr)
    {
        delete wifiScan;
        wifiScan = nullptr;
    }
    if (wifiScanAlert != nullptr)
    {
        delete wifiScanAlert;
        wifiScanAlert = nullptr;
    }

    auto draw = viewManager->getDraw();

    // if wifi isn't available, return
    if (!viewManager->getBoard().hasWiFi)
    {
        wifiScanAlert = new Alert(draw, "WiFi not available on your board.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        wifiScanAlert->draw();
        delay(2000);
        return false;
    }

    auto LED = viewManager->getLED();

    draw->text(Vector(5, 5), "Scanning...");
    draw->swap();

    LED.on();
    auto networks = viewManager->getWiFi().scan();
    LED.off();

    if (wifiScanCount == 0)
    {
        wifiScanAlert = new Alert(draw, "No networks found", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        wifiScanAlert->draw();
        draw->swap();
        delay(2000);
        return false;
    }

    wifiScan = new Menu(
        viewManager->getDraw(),            // draw instance
        "WiFi Scan",                       // title
        0,                                 // y
        viewManager->getBoard().height,    // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    for (int i = 0; i < wifiScanCount; i++)
    {
        String ssid = wifiScanResults[i].ssid;
        if (ssid.length() == 0 || ssid == " ")
            continue;
        wifiScan->addItem(wifiScanResults[i].ssid.c_str());
    }
    wifiScan->setSelected(0);
    wifiScan->draw();

    return true;
}

static void wifiScanRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_UP:
        wifiScan->scrollUp();
        inputManager->reset(true);
        break;
    case BUTTON_DOWN:
        wifiScan->scrollDown();
        inputManager->reset(true);
        break;
    case BUTTON_LEFT:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
        switch (wifiScan->getSelectedIndex())
        {
            // maybe we can connect to the selected wifi?
            // send to the loading view, then connect
        }
        inputManager->reset(true);
    default:
        break;
    }
}

static void wifiScanStop(ViewManager *viewManager)
{
    if (wifiScan != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            wifiScan->clear();
        delete wifiScan;
        wifiScan = nullptr;
    }
    if (wifiScanAlert != nullptr)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            wifiScanAlert->clear();
        delete wifiScanAlert;
        wifiScanAlert = nullptr;
    }
}

const PROGMEM View wifiScanView = View("WiFi Scan", wifiScanRun, wifiScanStart, wifiScanStop);