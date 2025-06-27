#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "../../../internal/system/view_manager.hpp"

#define WIFI_SETTINGS_PATH "/wifi_settings.json"
#define WIFI_SSID_PATH "/ssid.json"
#define WIFI_PASSWORD_PATH "/password.json"
using namespace Picoware;
String wifiUtilsLoadWiFiSSIDFromFlash(ViewManager *viewManager)
{
    JsonDocument doc;
    auto storage = viewManager->getStorage();
    if (!storage.deserialize(doc, WIFI_SSID_PATH))
    {
        return "";
    }
    if (!doc["ssid"])
    {
        return "";
    }
    return doc["ssid"].as<String>();
}
String wifiUtilsLoadWiFiPasswordFromFlash(ViewManager *viewManager)
{
    JsonDocument doc;
    auto storage = viewManager->getStorage();
    if (!storage.deserialize(doc, WIFI_PASSWORD_PATH))
    {
        return "";
    }
    if (!doc["password"])
    {
        return "";
    }
    return doc["password"].as<String>();
}
bool wifiUtilsConnectToSavedWiFi(ViewManager *viewManager)
{
    auto wifi = viewManager->getWiFi();
    auto board = viewManager->getBoard();
    if (board.hasWiFi && !wifi.isConnected())
    {
        // start WiFi connection
        String ssid = wifiUtilsLoadWiFiSSIDFromFlash(viewManager);
        String password = wifiUtilsLoadWiFiPasswordFromFlash(viewManager);
        if (ssid.length() > 0 && password.length() > 0)
        {
            return wifi.connectAsync(ssid.c_str(), password.c_str());
        }
    }
    return false;
}
String wifiUtilsLoadWiFiFromFlash(ViewManager *viewManager)
{
    JsonDocument doc;
    auto storage = viewManager->getStorage();
    if (!storage.deserialize(doc, WIFI_SETTINGS_PATH))
    {
        return "";
    }
    if (!doc["ssid"] || !doc["password"])
    {
        return "";
    }
    String ssid = doc["ssid"].as<String>();
    String password = doc["password"].as<String>();
    return "{\"ssid\":\"" + ssid + "\",\"password\":\"" + password + "\"}";
}
bool wifiUtilsSaveWiFiSSIDToFlash(Storage storage, const String ssid)
{
    JsonDocument doc;
    doc["ssid"] = ssid;
    return storage.serialize(doc, WIFI_SSID_PATH);
}
bool wifiUtilsSaveWiFiPasswordToFlash(Storage storage, const String password)
{
    JsonDocument doc;
    doc["password"] = password;
    return storage.serialize(doc, WIFI_PASSWORD_PATH);
}
bool wifiUtilsSaveWiFiToFlash(Storage storage, const String ssid, const String password)
{
    JsonDocument settingsDoc;
    if (storage.deserialize(settingsDoc, WIFI_SETTINGS_PATH))
    {
        settingsDoc.clear();
    }
    settingsDoc["ssid"] = ssid;
    settingsDoc["password"] = password;
    return storage.serialize(settingsDoc, WIFI_SETTINGS_PATH);
}