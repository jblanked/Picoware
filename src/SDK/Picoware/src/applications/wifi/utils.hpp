#pragma once
#include "../../../system/drivers/jsmn/jsmn.h"
#include "../../../system/view_manager.hpp"

#define WIFI_SETTINGS_PATH "picoware/wifi/settings.json"
#define WIFI_SSID_PATH "picoware/wifi/ssid.json"
#define WIFI_PASSWORD_PATH "picoware/wifi/password.json"

inline std::string wifiUtilsLoadWiFiSSIDFromFlash(ViewManager *viewManager)
{
    auto storage = viewManager->getStorage();
    char buffer[64] = {0};
    size_t bytes_read = 0;
    if (!storage.read(WIFI_SSID_PATH, buffer, sizeof(buffer) - 1, &bytes_read))
    {
        printf("Failed to load WiFi SSID from flash\n");
        return "";
    }
    buffer[bytes_read] = '\0'; // Ensure null termination at actual read length
    return getJsonValue(buffer, "ssid");
}

inline std::string wifiUtilsLoadWiFiPasswordFromFlash(ViewManager *viewManager)
{
    auto storage = viewManager->getStorage();
    char buffer[64] = {0};
    size_t bytes_read = 0;
    if (!storage.read(WIFI_PASSWORD_PATH, buffer, sizeof(buffer) - 1, &bytes_read))
    {
        printf("Failed to load WiFi password from flash\n");
        return "";
    }
    buffer[bytes_read] = '\0'; // Ensure null termination at actual read length
    return getJsonValue(buffer, "password");
}

inline bool wifiUtilsConnectToSavedWiFi(ViewManager *viewManager)
{
    auto &wifi = viewManager->getWiFi();
    if (!wifi.isConnected())
    {
        // start WiFi connection
        std::string ssid = wifiUtilsLoadWiFiSSIDFromFlash(viewManager);
        std::string password = wifiUtilsLoadWiFiPasswordFromFlash(viewManager);
        if (ssid.length() > 0 && password.length() > 0)
        {
            return wifi.connectAsync(ssid.c_str(), password.c_str());
        }
        return false;
    }
    return true;
}

inline std::string wifiUtilsLoadWiFiFromFlash(ViewManager *viewManager)
{
    auto storage = viewManager->getStorage();
    char buffer[128] = {0};
    size_t bytes_read = 0;
    if (!storage.read(WIFI_SETTINGS_PATH, buffer, sizeof(buffer) - 1, &bytes_read))
    {
        printf("Failed to load WiFi settings from flash\n");
        return "";
    }
    buffer[bytes_read] = '\0'; // Ensure null termination at actual read length
    std::string ssid = getJsonValue(buffer, "ssid");
    std::string password = getJsonValue(buffer, "password");
    return "{\"ssid\":\"" + ssid + "\",\"password\":\"" + password + "\"}";
}

inline bool wifiUtilsSaveWiFiSSIDToFlash(Storage storage, const std::string ssid)
{
    std::string json = "{\"ssid\":\"" + ssid + "\"}";
    if (!storage.write(WIFI_SSID_PATH, json.c_str(), json.size()))
    {
        printf("Failed to save SSID to flash\n");
        return false;
    }
    return true;
}

inline bool wifiUtilsSaveWiFiPasswordToFlash(Storage storage, const std::string password)
{
    std::string json = "{\"password\":\"" + password + "\"}";
    if (!storage.write(WIFI_PASSWORD_PATH, json.c_str(), json.size()))
    {
        printf("Failed to save password to flash\n");
        return false;
    }
    return true;
}

inline bool wifiUtilsSaveWiFiToFlash(Storage storage, const std::string ssid, const std::string password)
{
    std::string json = "{\"ssid\":\"" + ssid + "\",\"password\":\"" + password + "\"}";
    if (!storage.write(WIFI_SETTINGS_PATH, json.c_str(), json.size()))
    {
        printf("Failed to save WiFi settings to flash\n");
        return false;
    }
    return true;
}