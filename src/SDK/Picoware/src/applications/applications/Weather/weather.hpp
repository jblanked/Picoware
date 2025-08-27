#pragma once
#include "../../../gui/draw.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/http.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"

static Alert *weatherAlert = nullptr;
static HTTP *weatherHttp = nullptr;

static bool locationRequestSent = false;
static bool locationRequestInProgress = false;
static bool weatherRequestSent = false;
static bool weatherRequestInProgress = false;
static bool displayingResultW = false;
static std::string ipAddress = "";

static void resetWeatherState()
{
    locationRequestSent = false;
    locationRequestInProgress = false;
    weatherRequestSent = false;
    weatherRequestInProgress = false;
    displayingResultW = false;
    ipAddress = "";
}

static void weatherAlertAndReturn(ViewManager *viewManager, const char *message)
{
    if (weatherAlert)
    {
        delete weatherAlert;
        weatherAlert = nullptr;
    }
    weatherAlert = new Alert(viewManager->getDraw(), message, viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    weatherAlert->draw();
    delay(2000);
    viewManager->back();
}
static bool weatherStart(ViewManager *viewManager)
{
    if (weatherAlert)
    {
        delete weatherAlert;
        weatherAlert = nullptr;
    }
    if (weatherHttp)
    {
        delete weatherHttp;
        weatherHttp = nullptr;
    }

    auto draw = viewManager->getDraw();

    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        weatherAlertAndReturn(viewManager, "WiFi not connected yet.");
        return false;
    }

    draw->text(Vector(5, 5), "Fetching location data...");
    draw->swap();
    weatherHttp = new HTTP();

    // Reset weather state for fresh start
    resetWeatherState();

    return true;
}
static void weatherRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    auto draw = viewManager->getDraw();

    switch (input)
    {
    case BUTTON_LEFT:
    case BUTTON_BACK:
        resetWeatherState();
        viewManager->back();
        inputManager->reset(true);
        return;
    case BUTTON_RIGHT:
    case BUTTON_CENTER:
        resetWeatherState();
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Fetching location data...");
        draw->swap();
        inputManager->reset(true);
        break;
    default:
        break;
    }

    if (displayingResultW)
    {
        return;
    }

    // Step 1: Get location data if not already requested
    if (!locationRequestSent && !locationRequestInProgress)
    {
        locationRequestSent = true;
        locationRequestInProgress = true;

        weatherHttp->getAsync("https://ipwhois.app/json/");

        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Getting your location...");
        draw->swap();
    }

    // Process async location request
    if (locationRequestInProgress)
    {
        weatherHttp->update();

        if (weatherHttp->isRequestComplete())
        {
            locationRequestInProgress = false;

            std::string locationResponse = weatherHttp->getAsyncResponse();

            if (!locationResponse.empty())
            {
                ipAddress = getJsonValue(locationResponse.c_str(), "ip");

                if (!ipAddress.empty())
                {
                    // Clear the first request before starting the second one
                    weatherHttp->clearAsyncResponse();

                    draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                    draw->text(Vector(5, 5), "Fetching Weather data...");
                    draw->swap();
                    return;
                }
                else
                {
                    weatherAlertAndReturn(viewManager, "Failed to get location coordinates.");
                    return;
                }
            }
            else
            {
                weatherAlertAndReturn(viewManager, "Failed to fetch location data.");
                return;
            }
        }
        else
        {
            // Show loading indicator for location
            static unsigned long lastLocationUpdate = 0;
            static int locationDotCount = 0;

            if (millis() - lastLocationUpdate > 500)
            {
                lastLocationUpdate = millis();
                locationDotCount = (locationDotCount + 1) % 4;

                std::string loadingText = "Getting your location";
                for (int i = 0; i < locationDotCount; i++)
                {
                    loadingText += ".";
                }

                draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                draw->text(Vector(5, 5), loadingText.c_str(), viewManager->getForegroundColor());
                draw->swap();
            }
        }
        return;
    }

    // Step 2: Get weather data if we have coordinates but haven't requested weather yet
    if (!ipAddress.empty() && !weatherRequestSent && !weatherRequestInProgress)
    {
        weatherRequestSent = true;
        weatherRequestInProgress = true;

        std::string weatherUrl = "https://wttr.in/@" + ipAddress + "?format=%f,%t,%h";
        weatherHttp->getAsync(weatherUrl);
        draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
        draw->text(Vector(5, 5), "Getting weather data...");
        draw->swap();
    }

    // Process async weather request
    if (weatherRequestInProgress)
    {
        weatherHttp->update();

        if (weatherHttp->isRequestComplete())
        {
            weatherRequestInProgress = false;

            std::string weatherResponse = weatherHttp->getAsyncResponse();
            if (!weatherResponse.empty())
            {
                // wttr.in has each value separated by a comma
                std::vector<std::string> values;
                std::string item;

                // comma splitting
                size_t pos = 0;
                std::string response = weatherResponse;
                while ((pos = response.find(',')) != std::string::npos)
                {
                    values.push_back(response.substr(0, pos));
                    response.erase(0, pos + 1);
                }
                // Add the last part (after the final comma)
                if (!response.empty())
                {
                    values.push_back(response);
                }

                // Extract individual values (temperature, feels_like, humidity)
                std::string temperature = values.size() > 0 ? values[0] : "N/A";
                std::string feelsLike = values.size() > 1 ? values[1] : "N/A";
                std::string humidity = values.size() > 2 ? values[2] : "N/A";

                std::string total_data = std::string("Current Weather:\n") +
                                         "Temperature: " + temperature + "\n" +
                                         "Feels Like: " + feelsLike + "\n" +
                                         "Humidity: " + humidity + "\n" +
                                         "Press CENTER to refresh\nPress LEFT to go back";

                draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
                draw->text(Vector(0, 5), total_data.c_str(), viewManager->getForegroundColor());
                draw->swap();
                displayingResultW = true;
                return;
            }
            else
            {
                weatherAlertAndReturn(viewManager, "Failed to fetch weather data.");
                return;
            }
        }
        else
        {
            // Show loading indicator for weather
            static unsigned long lastWeatherUpdate = 0;
            static int weatherDotCount = 0;

            if (millis() - lastWeatherUpdate > 500)
            {
                lastWeatherUpdate = millis();
                weatherDotCount = (weatherDotCount + 1) % 4;

                std::string loadingText = "Getting weather data";
                for (int i = 0; i < weatherDotCount; i++)
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

static void weatherStop(ViewManager *viewManager)
{
    resetWeatherState();

    if (weatherAlert)
    {
        delete weatherAlert;
        weatherAlert = nullptr;
    }
    if (weatherHttp)
    {
        delete weatherHttp;
        weatherHttp = nullptr;
    }
}

static const View weatherView = View("Weather", weatherRun, weatherStart, weatherStop);