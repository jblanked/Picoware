#pragma once
#include "../../../gui/alert.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../system/wifi.hpp"

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
#ifndef CYW43_WL_GPIO_LED_PIN
    wifiScanAlert = new Alert(draw, "WiFi not available on your board.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    wifiScanAlert->draw();
    delay(2000);
    return false;
#else

    draw->text(Vector(5, 5), "Scanning...");
    draw->swap();

    auto networks = viewManager->getWiFi().scan();

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
        320,                               // height
        viewManager->getForegroundColor(), // text color
        viewManager->getBackgroundColor(), // background color
        viewManager->getSelectedColor(),   // selected color
        viewManager->getForegroundColor(), // border/separator color
        2                                  // border/separator width
    );

    for (int i = 0; i < wifiScanCount; i++)
    {
        if (wifiScanResults[i].ssid.length() == 0 || wifiScanResults[i].ssid == " ")
            continue;
        wifiScan->addItem(wifiScanResults[i].ssid.c_str());
    }
    wifiScan->setSelected(0);
    wifiScan->draw();

    return true;
#endif
}

static void wifiScanRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
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
    case BUTTON_BACK:
        viewManager->back();
        inputManager->reset(true);
        break;
    case BUTTON_RIGHT:
        switch (wifiScan->getSelectedIndex())
        {
            // maybe we can connect to the selected wifi?
            // send to the loading view, then connect
        };
        inputManager->reset(true);
    default:
        break;
    };
}

static void wifiScanStop(ViewManager *viewManager)
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
}

static const View wifiScanView = View("WiFi Scan", wifiScanRun, wifiScanStart, wifiScanStop);