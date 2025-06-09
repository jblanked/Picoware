#pragma once
#include "../../../../internal/boards.hpp"
#include "../../../../internal/gui/draw.hpp"
#include "../../../../internal/gui/menu.hpp"
#include "../../../../internal/system/http.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
using namespace Picoware;
static Alert *gpsAlert = nullptr;
static HTTP *gpsHttp = nullptr;
static String gpsResponse = "";
static void gpsStart(ViewManager *viewManager)
{
    if (gpsAlert)
    {
        delete gpsAlert;
        gpsAlert = nullptr;
    }
    if (gpsHttp)
    {
        delete gpsHttp;
        gpsHttp = nullptr;
    }

    auto draw = viewManager->getDraw();

    // if wifi isn't available, return
    if (!viewManager->getBoard().hasWiFi)
    {
        gpsAlert = new Alert(draw, "WiFi not available on your board.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        gpsAlert->draw();
        delay(2000);
        viewManager->back();
        return;
    }
    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        gpsAlert = new Alert(draw, "WiFi not connected yet.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        gpsAlert->draw();
        delay(2000);
        viewManager->back();
        return;
    }

    draw->text(Vector(5, 5), "Fetching GPS...");
    draw->swap();

    // send the request
    gpsHttp = new HTTP();
    gpsResponse = gpsHttp->request("GET", "https://ipwhois.app/json/");
}
static void gpsRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_LEFT:
        viewManager->back();
        return;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        // maybe refresh the request?
        break;
    default:
        break;
    }

    auto draw = viewManager->getDraw();
    if (gpsResponse.length() != 0)
    {
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, gpsResponse);
        if (error)
        {
            Serial.print("deserializeJson() failed: ");
            Serial.println(error.c_str());
            gpsAlert = new Alert(draw, "Failed to parse GPS data.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
            gpsAlert->draw();
            delay(2000);
            viewManager->back();
            return;
        }
        String city = doc["city"] | "Unknown";
        String region = doc["region"] | "Unknown";
        String country = doc["country"] | "Unknown";
        String latitude = doc["latitude"] | "Unknown";
        String longitude = doc["longitude"] | "Unknown";
        String total_data = "You are in:\n" + city + ", " + region + ", " + country + ".\nLatitude: " + latitude + ", Longitude: " + longitude;
        draw->text(Vector(0, 5), total_data.c_str(), viewManager->getForegroundColor());
        draw->swap();
    }
    else
    {
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        gpsAlert = new Alert(draw, "Failed to fetch GPS data.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        gpsAlert->draw();
        delay(2000);
        viewManager->back();
        return;
    }
}
static void gpsStop(ViewManager *viewManager)
{
    if (gpsAlert)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            gpsAlert->clear();
        delete gpsAlert;
        gpsAlert = nullptr;
    }
    if (gpsHttp)
    {
        delete gpsHttp;
        gpsHttp = nullptr;
    }

    gpsResponse = "";
}

const PROGMEM View gpsView = View("GPS", gpsRun, gpsStart, gpsStop);