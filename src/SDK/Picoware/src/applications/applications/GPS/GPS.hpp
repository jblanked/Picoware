#pragma once
#include "../../../gui/draw.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/http.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"

static Alert *gpsAlert = nullptr;
static HTTP *gpsHttp = nullptr;

static bool requestSent = false;
static bool requestInProgress = false;
static bool displayingResult = false;

static void resetGpsState()
{
    requestSent = false;
    requestInProgress = false;
    displayingResult = false;
}

static std::string parseLocationData(const std::string &response)
{
    std::string city = getJsonValue(response.c_str(), "city");
    std::string region = getJsonValue(response.c_str(), "region");
    std::string country = getJsonValue(response.c_str(), "country");
    std::string lat = getJsonValue(response.c_str(), "latitude");
    std::string lon = getJsonValue(response.c_str(), "longitude");
    std::string ip = getJsonValue(response.c_str(), "ip");

    // Build location display string
    if (!city.empty() || !country.empty())
    {
        std::string locationText = "Your Location:\n\n";

        if (!city.empty())
        {
            locationText += "City: " + city + "\n";
        }
        if (!region.empty())
        {
            locationText += "Region: " + region + "\n";
        }
        if (!country.empty())
        {
            locationText += "Country: " + country + "\n";
        }
        locationText += "\n";

        if (!lat.empty() && !lon.empty())
        {
            locationText += "Coordinates:\n";
            locationText += "Lat: " + lat + "\n";
            locationText += "Lon: " + lon + "\n\n";
        }

        if (!ip.empty())
        {
            locationText += "IP: " + ip + "\n\n";
        }

        locationText += "Press CENTER to refresh\nPress LEFT to go back";

        return locationText;
    }

    return "";
}

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

    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        gpsAlert = new Alert(draw, "WiFi not connected yet.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        gpsAlert->draw();
        delay(2000);
        return false;
    }

    draw->text(Vector(5, 5), "Starting GPS lookup...");
    draw->swap();
    gpsHttp = new HTTP();

    // Reset GPS state for fresh start
    resetGpsState();

    return true;
}

static void gpsRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    auto draw = viewManager->getDraw();

    switch (input)
    {
    case BUTTON_LEFT:
    case BUTTON_BACK:
        requestSent = false;
        requestInProgress = false;
        displayingResult = false;
        viewManager->back();
        inputManager->reset();
        return;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        requestSent = false;
        requestInProgress = false;
        displayingResult = false;
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Starting GPS lookup...");
        draw->swap();
        inputManager->reset();
        break;
    default:
        break;
    }

    if (displayingResult)
    {
        return;
    }

    if (!requestSent && !requestInProgress)
    {
        requestSent = true;
        requestInProgress = true;

        // Start async request for location data
        if (!gpsHttp->getAsync("https://ipwhois.app/json/"))
        {
            std::string errorMsg = "Failed to start location request.";
            gpsAlert = new Alert(draw, errorMsg.c_str(), viewManager->getForegroundColor(), viewManager->getBackgroundColor());
            gpsAlert->draw();
            delay(2000);
            requestSent = false;
            requestInProgress = false;
            return;
        }

        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Getting your location...");
        draw->swap();
    }

    // Check if async request is complete
    if (requestInProgress)
    {
        // Process async requests
        gpsHttp->update();

        // Check if request completed (either success or failure)
        if (gpsHttp->isRequestComplete())
        {
            requestInProgress = false;

            std::string gpsResponse = gpsHttp->getAsyncResponse();

            if (!gpsResponse.empty())
            {
                // Parse the location data
                std::string locationInfo = parseLocationData(gpsResponse);

                if (!locationInfo.empty())
                {
                    draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                    draw->text(Vector(0, 5), locationInfo.c_str(), viewManager->getForegroundColor());
                    draw->swap();
                    displayingResult = true;
                    return;
                }
                else
                {
                    draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                    std::string errorMsg = "Unable to parse location data.\n\nRaw response:\n" + gpsResponse.substr(0, 200) + "\n\nPress LEFT to go back";
                    draw->text(Vector(0, 5), errorMsg.c_str(), viewManager->getForegroundColor());
                    draw->swap();
                    displayingResult = true;
                    return;
                }
            }
            else
            {
                draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                std::string errorMsg = "Failed to get location data.";
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
        else
        {
            // Show loading indicator while request is in progress
            static unsigned long lastUpdate = 0;
            static int dotCount = 0;

            if (millis() - lastUpdate > 500)
            {
                lastUpdate = millis();
                dotCount = (dotCount + 1) % 4;

                std::string loadingText = "Getting your location";
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
}
static void gpsStop(ViewManager *viewManager)
{
    resetGpsState();

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
}

static const View gpsView = View("GPS", gpsRun, gpsStart, gpsStop);