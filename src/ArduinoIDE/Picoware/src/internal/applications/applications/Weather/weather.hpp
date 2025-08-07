#pragma once
#include "../../../../internal/boards.hpp"
#include "../../../../internal/gui/draw.hpp"
#include "../../../../internal/gui/menu.hpp"
#include "../../../../internal/system/http.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
using namespace Picoware;
static Alert *weatherAlert = nullptr;
static HTTP *weatherHttp = nullptr;
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

    // if wifi isn't available, return
    if (!viewManager->getBoard().hasWiFi)
    {
        weatherAlertAndReturn(viewManager, "WiFi not available on your board.");
        return false;
    }

    // if wifi isn't connected, return
    if (!viewManager->getWiFi().isConnected())
    {
        weatherAlertAndReturn(viewManager, "WiFi not connected yet.");
        return false;
    }

    draw->text(Vector(5, 5), "Fetching location data...");
    draw->swap();
    weatherHttp = new HTTP();
    return true;
}
static void weatherRun(ViewManager *viewManager)
{
    static bool sendWeatherRequest = false;
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getInput();
    switch (input)
    {
    case BUTTON_LEFT:
    case BUTTON_BACK:
        viewManager->back();
        inputManager->reset(true);
        return;
    default:
        break;
    }

    if (!sendWeatherRequest)
    {
        sendWeatherRequest = true;
        auto draw = viewManager->getDraw();
        auto LED = viewManager->getLED();
        LED.on();
        String locationResponse = weatherHttp->request("GET", "https://ipwhois.app/json/");
        LED.off();
        if (locationResponse.length() != 0)
        {
            draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
            JsonDocument doc;
            DeserializationError error = deserializeJson(doc, locationResponse);
            if (error)
            {
                weatherAlert = new Alert(draw, "Failed to parse GPS data.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
                weatherAlert->draw();
                delay(2000);
                viewManager->back();
                return;
            }
            String latitude = String(doc["latitude"].as<double>(), 6);
            String longitude = String(doc["longitude"].as<double>(), 6);

            draw->text(Vector(5, 5), "Fetching Weather data...");
            draw->swap();

            String url = "https://api.open-meteo.com/v1/forecast?latitude=" + latitude + "&longitude=" + longitude +
                         "&current=temperature_2m,precipitation,rain,showers,snowfall&temperature_unit=celsius&wind_speed_unit=mph&precipitation_unit=inch&forecast_days=1";
            String weatherResponse = weatherHttp->request("GET", url);
            if (weatherResponse.length() == 0)
            {
                weatherAlert = new Alert(draw, "Failed to fetch Weather data.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
                weatherAlertAndReturn(viewManager, "Failed to fetch Weather data.");
                return;
            }
            JsonDocument weatherDoc;
            error = deserializeJson(weatherDoc, weatherResponse);
            if (error)
            {
                weatherAlertAndReturn(viewManager, "Failed to parse Weather data.");
                return;
            }

            draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
            String temperature = String(weatherDoc["current"]["temperature_2m"].as<double>(), 1);
            String precipitation = String(weatherDoc["current"]["precipitation"].as<double>(), 1);
            String rain = String(weatherDoc["current"]["rain"].as<double>(), 1);
            String showers = String(weatherDoc["current"]["showers"].as<double>(), 1);
            String snowfall = String(weatherDoc["current"]["snowfall"].as<double>(), 1);
            String time_str = weatherDoc["current"]["time"].as<String>();
            time_str.replace("T", " ");
            String total_data = String("Current Weather:\n") +
                                "Temperature: " + temperature + " C\n" +
                                "Precipitation: " + precipitation + "mm\n" +
                                "Rain: " + rain + "mm\n" +
                                "Showers: " + showers + "mm\n" +
                                "Snowfall: " + snowfall + "mm\n" +
                                "Time: " + time_str;
            draw->text(Vector(0, 5), total_data.c_str(), viewManager->getForegroundColor());
            draw->swap();
            return;
        }
        else
        {
            draw->clear(Vector(0, 0), viewManager->getSize(), viewManager->getBackgroundColor());
            weatherAlertAndReturn(viewManager, "Failed to fetch Weather data.");
            return;
        }
    }
}
static void weatherStop(ViewManager *viewManager)
{
    if (weatherAlert)
    {
        if (viewManager->getBoard().boardType == BOARD_TYPE_VGM)
            weatherAlert->clear();
        delete weatherAlert;
        weatherAlert = nullptr;
    }
    if (weatherHttp)
    {
        delete weatherHttp;
        weatherHttp = nullptr;
    }
}
const PROGMEM View weatherView = View("Weather", weatherRun, weatherStart, weatherStop);