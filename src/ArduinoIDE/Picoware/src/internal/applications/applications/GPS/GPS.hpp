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
static bool gpsStart(ViewManager *viewManager)
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
        return false;
    }

    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        gpsAlert = new Alert(draw, "WiFi not connected yet.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        gpsAlert->draw();
        delay(2000);
        return false;
    }

    draw->text(Vector(5, 5), "Fetching GPS...");
    draw->swap();
    gpsHttp = new HTTP();
    return true;
}
static void gpsRun(ViewManager *viewManager)
{
    static bool requestSent = false;
    static bool requestInProgress = false;
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    auto draw = viewManager->getDraw();
    auto LED = viewManager->getLED();

    switch (input)
    {
    case BUTTON_LEFT:
        viewManager->back();
        return;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        // Reset for new request
        requestSent = false;
        requestInProgress = false;
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Fetching GPS...");
        draw->swap();
        break;
    default:
        break;
    }

    // Start async request if not already sent
    if (!requestSent && !requestInProgress)
    {
        requestSent = true;
        requestInProgress = true;
        LED.on();

        // Start async request - AsyncHTTPRequest_RP2040W doesn't support HTTPS
        bool success = gpsHttp->requestAsync("GET", "http://ipwhois.app/json/");
        if (!success)
        {
            LED.off();
            // Check if it's an async library issue or network issue
            String errorMsg = "Failed to start GPS request.";
            gpsAlert = new Alert(draw, errorMsg.c_str(), viewManager->getForegroundColor(), viewManager->getBackgroundColor());
            gpsAlert->draw();
            delay(2000);
            viewManager->back();
            return;
        }

        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Requesting GPS data...");
        draw->swap();
    }

    // Check if async request is complete
    if (requestInProgress)
    {
        // Process async requests
        gpsHttp->processAsync();

        // Check if request completed (either success or failure)
        if (gpsHttp->isAsyncComplete())
        {
            requestInProgress = false;
            LED.off();

            String gpsResponse = gpsHttp->getAsyncResponse();

            if (gpsResponse.length() != 0)
            {
                draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                JsonDocument doc;
                DeserializationError error = deserializeJson(doc, gpsResponse);
                if (error)
                {
                    gpsAlert = new Alert(draw, "Failed to parse GPS data.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
                    gpsAlert->draw();
                    delay(2000);
                    viewManager->back();
                    return;
                }
                String city = doc["city"] | "Unknown";
                String region = doc["region"] | "Unknown";
                String country = doc["country"] | "Unknown";
                String latitude = String(doc["latitude"].as<double>(), 6);
                String longitude = String(doc["longitude"].as<double>(), 6);
                String total_data = "You are in:\n" + city + ", " + region + ", " + country + ".\nLatitude: " + latitude + ", Longitude: " + longitude + "\n\nPress CENTER to refresh\nPress LEFT to go back";
                draw->text(Vector(0, 5), total_data.c_str(), viewManager->getForegroundColor());
                draw->swap();
            }
            else
            {
                draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                String errorMsg = "Failed to fetch GPS data.";
                if (gpsHttp->getState() == ISSUE)
                {
                    errorMsg = "Network error or timeout.";
                }
                gpsAlert = new Alert(draw, errorMsg.c_str(), viewManager->getForegroundColor(), viewManager->getBackgroundColor());
                gpsAlert->draw();
                delay(2000);
                viewManager->back();
                return;
            }
        }
    }

    // Show loading indicator while request is in progress
    if (requestInProgress)
    {
        static unsigned long lastUpdate = 0;
        static int dotCount = 0;

        if (millis() - lastUpdate > 500) // Update every 500ms
        {
            lastUpdate = millis();
            dotCount = (dotCount + 1) % 4;

            String loadingText = "Requesting GPS data";
            for (int i = 0; i < dotCount; i++)
            {
                loadingText += ".";
            }

            draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
            draw->text(Vector(5, 5), loadingText.c_str(), viewManager->getForegroundColor());
            draw->swap();
        }
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
}

const PROGMEM View gpsView = View("GPS", gpsRun, gpsStart, gpsStop);